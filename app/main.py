# app/main.py
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app import models, schemas
from app.routers import auth, graduation, timetable, notices, chatbot, transcript

app = FastAPI(title="GradManager API")

# 프론트엔드 통신 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(graduation.router, prefix="/api/v1/graduation", tags=["graduation"])
app.include_router(timetable.router, prefix="/api/v1/timetable", tags=["timetable"])
app.include_router(notices.router, prefix="/api/v1/notices", tags=["notices"])
app.include_router(chatbot.router, prefix="/api/v1/chatbot", tags=["chatbot"])
app.include_router(transcript.router, prefix="/api/v1/transcript", tags=["transcript"])

# 자동 DDL 마이그레이션 실행
def run_db_migrations():
    from app.database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(student_course_history)")).fetchall()
            columns = [row[1] for row in result]
            if "course_type" not in columns:
                conn.execute(text("ALTER TABLE student_course_history ADD COLUMN course_type VARCHAR(50) DEFAULT '일반선택'"))
                conn.commit()
                print("DDL Migration: course_type 컬럼이 student_course_history 테이블에 추가되었습니다.")
    except Exception as e:
        print(f"Migration Error: {e}")

run_db_migrations()

# SQLite 내용 기반 STUDENTS 전역 메모리 캐시 강제 동기화 헬퍼
def sync_student_cache(student_id: int, db: Session):
    from backend.core.data.students import STUDENTS
    from backend.core.data.csv_loader import load_courses
    from app.routers.graduation import get_course_category
    import re
    from collections import defaultdict

    student_id_str = str(student_id)
    if student_id_str not in STUDENTS:
        return

    student = STUDENTS[student_id_str]
    courses_db = load_courses()

    # SQLite로부터 최신 수강 기록 로드
    histories = db.query(models.StudentCourseHistory).filter(
        models.StudentCourseHistory.student_id == student_id
    ).all()

    # history_id 별로 course_code 및 attributes를 매칭하기 위해 Course 테이블 조인 조회
    history_details = []
    for h in histories:
        c_record = db.query(models.Course).filter(models.Course.course_id == h.course_id).first()
        course_code = c_record.course_code if c_record else f"UNKNOWN-{h.course_id}"
        course_name = c_record.course_name if c_record else "과목명 미정"
        history_details.append({
            "history_id": h.history_id,
            "course_code": course_code,
            "course_name": course_name,
            "earned_credit": h.earned_credit,
            "grade": h.grade,
            "is_retake": h.is_retake,
            "course_type": getattr(h, 'course_type', None),
            "semester_taken": h.semester_taken
        })

    # 재수강 포기(Forfeited) 계산: 동일 과목코드 또는 동일 과목명 그룹화 (Union-Find)
    n_hist = len(history_details)
    parent = list(range(n_hist))

    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    for i in range(n_hist):
        for j in range(i + 1, n_hist):
            code_i = history_details[i].get("course_code")
            code_j = history_details[j].get("course_code")
            name_i = history_details[i].get("course_name")
            name_j = history_details[j].get("course_name")
            
            cond_code = (code_i and code_j and code_i == code_j)
            cond_name = (name_i and name_j and name_i == name_j)
            if cond_code or cond_name:
                union(i, j)

    groups = defaultdict(list)
    for i in range(n_hist):
        root = find(i)
        groups[root].append(history_details[i])

    forfeited_ids = set()
    for root_idx, instances in groups.items():
        has_retake = any(inst.get("is_retake") for inst in instances)
        if has_retake and len(instances) > 1:
            def get_sem_score(sem: str):
                if not sem: return 0
                m = re.match(r'(\d+)-(\d)학기', sem)
                if not m: return 0
                return int(m.group(1)) * 10 + int(m.group(2))
            
            sorted_instances = sorted(instances, key=lambda x: get_sem_score(x.get("semester_taken")))
            # 최신 학기만 살리고 나머지는 포기
            for inst in sorted_instances[:-1]:
                if inst.get("history_id") is not None:
                    forfeited_ids.add(inst["history_id"])

    completed_courses_list = []
    total_completed = 0.0

    for hd in history_details:
        if hd["history_id"] in forfeited_ids:
            continue
        if hd["grade"] and str(hd["grade"]).upper() == "F":
            continue

        completed_courses_list.append(hd["course_code"])
        total_completed += float(hd["earned_credit"])

    # STUDENTS 캐시 딕셔너리 데이터 강제 덮어쓰기 동기화
    student["completed_courses"] = completed_courses_list
    student["completed_credits"] = total_completed
    STUDENTS[student_id_str] = student
    print(f"Cache Sync: 학생 {student_id} 캐시가 실시간 강제 동기화되었습니다 (학점: {total_completed}, 과목수: {len(completed_courses_list)}).")

@app.get("/")
def read_root():
    return {"message": "GradManager 백엔드 서버가 정상 작동 중입니다!"}

# [실제 DB 연동 API] 개설 과목 목록 조회
@app.get("/api/v1/offerings", response_model=schemas.CourseOfferingListResponse)
def get_course_offerings(
    professor: Optional[str] = Query(None, description="교수명 검색"),
    semester: Optional[str] = Query(None, description="학기 필터 (예: 1학기)"),
    skip: int = Query(0, description="건너뛸 데이터 수"),
    limit: int = Query(20, description="가져올 데이터 수"),
    db: Session = Depends(get_db)
):
    query = db.query(models.CourseOffering)

    # 조건별 필터링
    if professor:
        query = query.filter(models.CourseOffering.professor_name.like(f"%{professor}%"))
    if semester:
        query = query.filter(models.CourseOffering.semester == semester)

    total_count = query.count()
    offerings = query.offset(skip).limit(limit).all()

    return {
        "status": "success",
        "count": len(offerings),
        "data": offerings
    }
    # app/main.py 맨 아래에 추가

# [API 1] 웹에서 학생의 수강 이력 받아서 DB에 저장하기 (POST)
@app.post("/api/v1/students/history")
def add_student_course_history(
    history_data: schemas.CourseHistoryCreate,
    db: Session = Depends(get_db)
):
    import traceback
    try:
        import time
        import random
        from backend.core.data.csv_loader import load_courses
        from backend.core.data.students import STUDENTS

        if not history_data.student_id:
            raise HTTPException(status_code=400, detail="학번(student_id)은 필수 항목입니다.")

        c_id = history_data.course_id
        credit_val = 3.0
        new_course_code = None

        if history_data.custom_course_name:
            course_type = history_data.course_type or "일반선택"
            random_suffix = random.randint(1000, 9999)
            new_course_code = f"CUSTOM-{course_type}-{int(time.time())}-{random_suffix}"
            
            try:
                credit_val = float(history_data.credits) if history_data.credits is not None else 3.0
            except (ValueError, TypeError):
                credit_val = 3.0

            new_course = models.Course(
                course_code=new_course_code,
                course_name=history_data.custom_course_name,
                credit=credit_val,
                source_url="custom",
                theory_hours=0.0,
                practice_hours=0.0,
                course_description="직접 입력한 완료 과목"
            )
            db.add(new_course)
            db.commit()
            db.refresh(new_course)
            
            c_id = new_course.course_id
            load_courses.cache_clear()
            
        elif isinstance(c_id, str):
            c_record = db.query(models.Course).filter(models.Course.course_code == c_id).first()
            if not c_record:
                # CSV 로더 캐시에서 정보 조회하여 SQLite DB에 Course 레코드 즉시 동기화 생성
                from backend.core.data.csv_loader import load_courses
                courses_db = load_courses()
                c_info = courses_db.get(c_id)
                if c_info:
                    credit_val_temp = float(c_info.get("credits", 3.0))
                    new_c = models.Course(
                        course_code=c_id,
                        course_name=c_info.get("name", "과목명 미정"),
                        credit=credit_val_temp,
                        source_url="csv_sync",
                        theory_hours=0.0,
                        practice_hours=0.0,
                        course_description="CSV에서 자동 동기화된 과목"
                    )
                    db.add(new_c)
                    db.commit()
                    db.refresh(new_c)
                    c_record = new_c

            if c_record:
                c_id = c_record.course_id
                if history_data.credits is not None:
                    credit_val = float(history_data.credits)
                elif getattr(c_record, 'credit', None) is not None:
                    credit_val = float(c_record.credit)
                new_course_code = c_record.course_code
            else:
                import re
                nums = re.findall(r'\d+', c_id)
                fallback_id = int(nums[0]) if nums else 1001
                if fallback_id == 1 or fallback_id == 0:
                    fallback_id = 9999
                c_id = fallback_id
                new_course_code = str(c_id)
        else:
            if c_id is None:
                raise HTTPException(status_code=400, detail="course_id 또는 custom_course_name 중 하나는 필수입니다.")
            
            c_record = db.query(models.Course).filter(models.Course.course_id == c_id).first()
            if c_record:
                if history_data.credits is not None:
                    credit_val = float(history_data.credits)
                elif getattr(c_record, 'credit', None) is not None:
                    credit_val = float(c_record.credit)
                new_course_code = c_record.course_code
            else:
                new_course_code = str(c_id)

        if c_id is None:
            raise HTTPException(status_code=400, detail="유효한 course_id를 생성하거나 조회하는 데 실패했습니다.")

        comp_status = "이수"
        if history_data.grade and history_data.grade.upper() == "F":
            comp_status = "미이수"

        # 이수 구분(course_type) 처리
        c_type = history_data.course_type
        if not c_type and new_course_code:
            from backend.core.data.csv_loader import load_courses
            from app.routers.graduation import get_course_category
            c_type = get_course_category(new_course_code, load_courses())
        if not c_type:
            c_type = "일반선택"

        new_history = models.StudentCourseHistory(
            student_id=history_data.student_id,
            course_id=c_id,
            semester_taken=history_data.semester_taken,
            grade=history_data.grade,
            earned_credit=credit_val,
            completion_status=comp_status,
            is_retake=history_data.is_retake if history_data.is_retake is not None else False,
            course_type=c_type
        )
        db.add(new_history)
        db.commit()
        db.refresh(new_history)

        # SQLite 저장 완료 직후 전역 캐시 즉시 리팩토링 동기화
        sync_student_cache(history_data.student_id, db)

        return {
            "status": "success",
            "message": "수강 이력이 성공적으로 저장되었습니다.",
            "history_id": new_history.history_id,
            "course_id": c_id,
            "course_code": new_course_code
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print("add_student_course_history Exception:")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Bad Request: {str(e)}")

# [API 2] 수강 이력 기반 부족한 학점 계산해서 보여주기 (GET)
@app.get("/api/v1/students/{student_id}/graduation-summary", response_model=schemas.GraduationSummaryResponse)
def get_graduation_summary(
    student_id: int,
    db: Session = Depends(get_db)
):
    total_completed = 0
    major_completed = 0
    general_completed = 0
    required_total = 130

    try:
        # 수강 이력 조회
        histories = db.query(models.StudentCourseHistory).filter(
            models.StudentCourseHistory.student_id == student_id
        ).all()

        # 재수강 포기(Forfeited) 계산
        from collections import defaultdict
        import re
        
        history_details = []
        for h in histories:
            c_record = db.query(models.Course).filter(models.Course.course_id == h.course_id).first()
            course_code = c_record.course_code if c_record else f"UNKNOWN-{h.course_id}"
            course_name = c_record.course_name if c_record else "과목명 미정"
            history_details.append({
                "history_id": h.history_id,
                "course_code": course_code,
                "course_name": course_name,
                "earned_credit": h.earned_credit,
                "grade": h.grade,
                "is_retake": h.is_retake,
                "course_type": getattr(h, 'course_type', None),
                "semester_taken": h.semester_taken
            })

        # 재수강 포기(Forfeited) 계산: 동일 과목코드 또는 동일 과목명 그룹화 (Union-Find)
        n_hist = len(history_details)
        parent = list(range(n_hist))

        def find(i):
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        for i in range(n_hist):
            for j in range(i + 1, n_hist):
                code_i = history_details[i].get("course_code")
                code_j = history_details[j].get("course_code")
                name_i = history_details[i].get("course_name")
                name_j = history_details[j].get("course_name")
                
                cond_code = (code_i and code_j and code_i == code_j)
                cond_name = (name_i and name_j and name_i == name_j)
                if cond_code or cond_name:
                    union(i, j)

        groups = defaultdict(list)
        for i in range(n_hist):
            root = find(i)
            groups[root].append(history_details[i])

        forfeited_ids = set()
        for root_idx, instances in groups.items():
            has_retake = any(inst.get("is_retake") for inst in instances)
            if has_retake and len(instances) > 1:
                def get_sem_score(sem: str):
                    if not sem: return 0
                    m = re.match(r'(\d+)-(\d)학기', sem)
                    if not m: return 0
                    return int(m.group(1)) * 10 + int(m.group(2))
                
                sorted_instances = sorted(instances, key=lambda x: get_sem_score(x.get("semester_taken")))
                # 최신 학기만 살리고 나머지는 포기
                for inst in sorted_instances[:-1]:
                    if inst.get("history_id") is not None:
                        forfeited_ids.add(inst["history_id"])

        for hd in history_details:
            if hd["history_id"] in forfeited_ids:
                continue
            if hd["grade"] and str(hd["grade"]).upper() == "F":
                continue

            credit_val = float(hd["earned_credit"])
            c_type = hd.get("course_type")
            if not c_type or c_type.strip() == "":
                from backend.core.data.csv_loader import load_courses
                from app.routers.graduation import get_course_category
                c_type = get_course_category(hd["course_code"], load_courses())

            total_completed += credit_val

            if c_type and "전공" in c_type:
                major_completed += credit_val
            else:
                general_completed += credit_val

    except Exception as e:
        print(f"Calculations Error: {e}")

    remaining_total = max(0, required_total - total_completed)

    return {
        "status": "success",
        "student_id": student_id,
        "total_required_credits": required_total,
        "total_completed_credits": total_completed,
        "total_remaining_credits": remaining_total,
        "major_completed_credits": major_completed,
        "general_completed_credits": general_completed
    }

@app.get("/api/v1/students/{student_id}/history")
def get_student_course_history(
    student_id: int,
    db: Session = Depends(get_db)
):
    histories = db.query(models.StudentCourseHistory).filter(
        models.StudentCourseHistory.student_id == student_id
    ).all()
    result = []
    for h in histories:
        course = db.query(models.Course).filter(models.Course.course_id == h.course_id).first()
        course_name = course.course_name if course else "Unknown Course"
        course_code = course.course_code if course else f"UNKNOWN-{h.course_id}"
        db_course_type = getattr(h, 'course_type', None)
        if not db_course_type:
            from backend.core.data.csv_loader import load_courses
            from app.routers.graduation import get_course_category
            courses_db = load_courses()
            db_course_type = get_course_category(course_code, courses_db)

        # semester_taken 파싱 (예: "2024-1학기" -> year="2024", semester="1학기")
        year = ""
        semester = ""
        if h.semester_taken and "-" in h.semester_taken:
            parts = h.semester_taken.split("-", 1)
            year = parts[0]
            semester = parts[1]

        result.append({
            "history_id": h.history_id,
            "student_id": h.student_id,
            "course_id": h.course_id,
            "course_name": course_name,
            "course_code": course_code,
            "semester_taken": h.semester_taken,
            "grade": h.grade,
            "earned_credit": h.earned_credit,
            "is_retake": h.is_retake,
            "course_type": db_course_type,
            "year": year,
            "semester": semester
        })
    return {
        "status": "success",
        "data": result
    }

@app.put("/api/v1/students/history/{history_id}")
def update_student_course_history(
    history_id: int,
    history_data: schemas.CourseHistoryUpdate,
    db: Session = Depends(get_db)
):
    history = db.query(models.StudentCourseHistory).filter(
        models.StudentCourseHistory.history_id == history_id
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="Course history record not found.")
    
    if history_data.semester_taken is not None:
        history.semester_taken = history_data.semester_taken
    if history_data.grade is not None:
        history.grade = history_data.grade
        if str(history_data.grade).upper() == "F":
            history.completion_status = "미이수"
        else:
            history.completion_status = "이수"
    if history_data.course_id is not None:
        c_id = history_data.course_id
        credit_val = 3.0
        if isinstance(c_id, str):
            c_record = db.query(models.Course).filter(models.Course.course_code == c_id).first()
            if c_record:
                c_id = c_record.course_id
                if getattr(c_record, 'credit', None) is not None:
                    credit_val = float(c_record.credit)
            else:
                import re
                nums = re.findall(r'\d+', c_id)
                c_id = int(nums[0]) if nums else 1001
        else:
            c_record = db.query(models.Course).filter(models.Course.course_id == c_id).first()
            if c_record and getattr(c_record, 'credit', None) is not None:
                credit_val = float(c_record.credit)
        history.course_id = c_id
        history.earned_credit = credit_val

    # 과목명 및 학점 인라인 수정 지원
    course_rec = db.query(models.Course).filter(models.Course.course_id == history.course_id).first()
    if history_data.course_name is not None:
        if course_rec:
            course_rec.course_name = history_data.course_name
            
    if history_data.earned_credit is not None:
        history.earned_credit = history_data.earned_credit
        if course_rec:
            course_rec.credit = history_data.earned_credit
        
    # 이수구분(이수 구분) 수정 지원
    if history_data.course_type is not None:
        history.course_type = history_data.course_type
        
    # 재수강 여부 수정 지원
    if history_data.is_retake is not None:
        history.is_retake = history_data.is_retake
        
    db.commit()
    db.refresh(history)

    # SQLite 수정 커밋 완료 직후 전역 캐시 즉시 리팩토링 동기화
    sync_student_cache(history.student_id, db)

    return {
        "status": "success",
        "message": "Course history updated successfully.",
        "data": {
            "history_id": history.history_id,
            "semester_taken": history.semester_taken,
            "grade": history.grade,
            "earned_credit": history.earned_credit,
            "is_retake": history.is_retake,
            "course_type": history.course_type
        }
    }

@app.delete("/api/v1/students/history/{history_id}")
def delete_student_course_history(
    history_id: int,
    db: Session = Depends(get_db)
):
    history = db.query(models.StudentCourseHistory).filter(
        models.StudentCourseHistory.history_id == history_id
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="Course history record not found.")
    
    student_id = history.student_id
    db.delete(history)
    db.commit()

    # SQLite 삭제 커밋 완료 직후 전역 캐시 즉시 리팩토링 동기화
    sync_student_cache(student_id, db)

    return {
        "status": "success",
        "message": "Course history deleted successfully."
    }

    # =====================================================================
# [학생 디지털 트윈 전체 동기화 API]
# 프론트엔드에서 학생 정보 + 수강 내역 목록 배열을 한 번에 넘겨줄 때 처리하는 API
# =====================================================================
@app.post("/api/v1/student/sync")
def sync_student_full_data(
    payload: schemas.StudentSyncRequest,
    db: Session = Depends(get_db)
):
    try:
        # 1. 학생 정보 (Student) DB 확인 및 저장/갱신
        student = db.query(models.Student).filter(models.Student.student_number == payload.student_number).first()
        
        if not student:
            student = models.Student(
                user_id=payload.user_id,
                student_number=payload.student_number,
                admission_year=payload.admission_year,
                current_grade=payload.current_grade
            )
            db.add(student)
            db.flush()  # student_id 획득
        else:
            student.admission_year = payload.admission_year
            student.current_grade = payload.current_grade

        # 2. 기존 학생의 수강 내역 지우기 (초기화 후 재등록)
        db.query(models.StudentCourseHistory).filter(
            models.StudentCourseHistory.student_id == student.student_id
        ).delete()

        # 3. 프론트에서 받은 수강 내역 일괄 등록
        for item in payload.course_history:
            new_history = models.StudentCourseHistory(
                student_id=student.student_id,
                course_id=item.course_id,
                semester_taken=item.semester_taken,
                grade=item.grade,
                earned_credit=item.earned_credit,
                completion_status=item.completion_status,
                is_retake=item.is_retake,
                course_type=item.course_type
            )
            db.add(new_history)

        db.commit()

        # 4. 캐시 강제 동기화 (기존 main.py 내 헬퍼 함수 호출)
        sync_student_cache(student.student_id, db)

        return {
            "status": "success",
            "message": "학생 정보 및 수강 내역 전체 동기화 완료",
            "student_id": student.student_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Sync Error: {str(e)}")