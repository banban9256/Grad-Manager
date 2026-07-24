from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

from backend.core.data.students import get_student, STUDENTS
from backend.core.data.csv_loader import load_courses
from backend.core.data.courses import get_required_remaining
from backend.core.scheduler import generate_timetable
from backend.core.notifications import get_upcoming_alerts, search_notices

router = APIRouter()

class UpdateCoursesRequest(BaseModel):
    studentId: str
    completedCourses: List[str]
    targetSemester: Optional[str] = None

def get_student_from_token(authorization: Optional[str]) -> dict:
    # Authorization header 파싱하여 학번 추출
    if not authorization:
        # 헤더가 없으면 기본 데모 계정 반환
        student = get_student("20210001")
        if not student:
            raise HTTPException(status_code=404, detail="기본 데모 학생을 찾을 수 없습니다.")
        return student
        
    try:
        token = authorization.split(" ")[1]
        student_id = token.replace("mock-jwt-token-", "")
        student = get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
        return student
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

def map_user_info(student: dict) -> dict:
    completed = student.get("completed_credits", 0)
    required = student.get("required_credits", 130)
    
    completed_details = {}
    try:
        courses_db = load_courses()
        for code in student.get("completed_courses", []):
            course = courses_db.get(code)
            if course:
                completed_details[code] = course.get("name", code)
            else:
                completed_details[code] = code
    except Exception:
        pass

    return {
        "name": student.get("name", ""),
        "university": "한신대학교",
        "department": student.get("department", "AISW"),
        "track": ", ".join(student.get("major_tracks", ["AISW 본전공"])),
        "studentId": student.get("student_id", ""),
        "semester": f"{student.get('current_semester', 1)}학기",
        "mileage": student.get("mileage", 0),
        "overallProgress": int((completed / required) * 100) if required > 0 else 0,
        "remainingCredits": max(0, required - completed),
        "totalRequired": required,
        "earnedCredits": completed,
        "completedCourses": student.get("completed_courses", []),
        "completedCoursesDetail": completed_details
    }

def get_course_category(code: str, courses_db: dict) -> str:
    from backend.core.data.csv_loader import _infer_type_from_code, _normalize_completion_type
    course = courses_db.get(code)
    if course:
        cat = course.get("category", "일반선택")
        return _normalize_completion_type(cat)
    else:
        inferred = _infer_type_from_code(code)
        return _normalize_completion_type(inferred)


@router.get("/summary", summary="종합 졸업학점 진단 결과 API")
def get_graduation_summary(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    student = get_student_from_token(authorization)
    student_id = student["student_id"]
    
    courses_db = load_courses()
    
    # SQLite StudentCourseHistory 기반의 최신 실시간 이수현황 집계
    from app import models
    histories = db.query(models.StudentCourseHistory).filter(
        models.StudentCourseHistory.student_id == int(student_id)
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
            "semester_taken": h.semester_taken,
            "earned_credit": h.earned_credit,
            "grade": h.grade,
            "is_retake": h.is_retake,
            "course_type": getattr(h, 'course_type', None)
        })

    # 재수강 포기(Forfeited) 계산: 동일 과목코드 또는 동일 과목명 그룹화 (Union-Find)
    from collections import defaultdict
    import re

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

    # creditCategories 계산
    # 카테고리별 기본 목표치 설정
    category_goals = {
        "전공필수": 18,
        "전공선택": 45,
        "교양필수": 14,
        "교양선택": 20,
        "계열공통": 12,
    }
    
    category_earned = {cat: 0.0 for cat in category_goals.keys()}
    category_earned["일반선택"] = 0.0
    
    completed_courses_list = []
    completed_details = {}

    for hd in history_details:
        if hd["history_id"] in forfeited_ids:
            continue
        if hd["grade"] == "F":
            continue
            
        code = hd["course_code"]
        completed_courses_list.append(code)
        completed_details[code] = hd["course_name"]
        
        # 이수구분 판별: 실물 DB에 course_type이 이미 저장되어 있으면 그것을 최우선으로 쓰고, 없으면 추론
        cat = hd.get("course_type")
        if not cat or cat.strip() == "":
            cat = get_course_category(code, courses_db)
        credits = float(hd["earned_credit"])
        
        if cat in category_earned:
            category_earned[cat] += credits
        else:
            category_earned["일반선택"] += credits

    completed = sum(category_earned.values())
    
    # 대시보드 리턴 데이터에 활용할 학생 딕셔너리 정보 오버라이드
    student["completed_credits"] = completed
    student["completed_courses"] = completed_courses_list

    category_keys = {
        "전공필수": "major_req",
        "전공선택": "major_sel",
        "교양필수": "liberal_req",
        "교양선택": "liberal_sel",
        "계열공통": "core_common",
        "일반선택": "general_sel"
    }

    category_tones = {
        "전공필수": "chart-1",
        "전공선택": "chart-2",
        "교양필수": "chart-3",
        "교양선택": "chart-1",
        "계열공통": "chart-2",
        "일반선택": "chart-3"
    }

    credit_categories = []
    for cat, req_credits in category_goals.items():
        credit_categories.append({
            "key": category_keys.get(cat, "etc"),
            "label": cat,
            "current": float(category_earned[cat]),
            "required": req_credits,
            "tone": category_tones.get(cat, "chart-1")
        })
    # 일반선택 추가
    credit_categories.append({
        "key": "general_sel",
        "label": "일반선택",
        "current": float(category_earned["일반선택"]),
        "required": 21,
        "tone": "chart-3"
    })

    # 2. 시간표 추천 데이터 (첫 번째 시간표를 scheduleBlocks 형태로 파싱)
    schedules = generate_timetable(student, max_schedules=1)
    schedule_blocks = []
    schedule_reasons = []
    
    if schedules:
        sched = schedules[0]
        # Pastel Color mapping
        pastel_palette = [
            {"bg": "bg-[#e8f3ff]", "text": "text-[#1b64da]", "bar": "bg-[#3182f6]"},
            {"bg": "bg-[#daf2ee]", "text": "text-[#008f80]", "bar": "bg-[#00b5a3]"},
            {"bg": "bg-[#fff3f5]", "text": "text-[#d6284a]", "bar": "bg-[#f04452]"},
            {"bg": "bg-[#f4edff]", "text": "text-[#6b31f6]", "bar": "bg-[#8f5cf0]"},
            {"bg": "bg-[#fffae8]", "text": "text-[#b08b00]", "bar": "bg-[#ffc900]"}
        ]
        
        day_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4}
        
        for idx, c in enumerate(sched["courses"]):
            color = pastel_palette[idx % len(pastel_palette)]
            for d, start, end in c.get("time_slots", []):
                if d in day_map:
                    # '09:00' -> 9.0
                    try:
                        sh, sm = map(int, start.split(":"))
                        eh, em = map(int, end.split(":"))
                        start_h = sh + sm / 60
                        end_h = eh + em / 60
                        
                        schedule_blocks.append({
                          "id": f"block-{c['code']}-{d}",
                          "name": c["name"],
                          "professor": c["professor"],
                          "day": day_map[d],
                          "start": start_h,
                          "end": end_h,
                          "color": color["bg"],
                          "textColor": color["text"]
                        })
                    except Exception:
                        pass
        
        schedule_reasons = [
            {"icon": "GraduationCap", "text": "졸업 필수 과목 배치 완료"},
            {"icon": "CalendarOff", "text": "선호하시는 요일 최적 배정"},
            {"icon": "BrainCircuit", "text": "여유로운 점심 시간대 보장"}
        ]
    else:
        schedule_reasons = [{"icon": "AlertTriangle", "text": "조건에 맞는 추천 시간표가 없습니다."}]

    # 3. 공지 알림 데이터
    notice_alerts = get_upcoming_alerts(30)
    academic_cal = []
    for a in notice_alerts:
        academic_cal.append({
            "id": a.get("id", 1),
            "title": a.get("alert_message", ""),
            "date": a.get("start_date", "2026-08-01"),
            "category": "일반",
            "isNew": True
        })
    if not academic_cal:
        academic_cal = [
            {"id": 1, "title": "2026학년도 2학기 수강신청 안내", "date": "2026-08-10", "category": "학사", "isNew": True},
            {"id": 2, "title": "졸업앨범 촬영 일정 안내", "date": "2026-09-15", "category": "학사", "isNew": False}
        ]

    # 디지털 트윈용 전공/교양 과목 개수 계산 (DB course_type 및 forfeited_ids 반영)
    major_courses_count = 0
    liberal_courses_count = 0
    for hd in history_details:
        if hd["history_id"] in forfeited_ids:
            continue
        if hd["grade"] == "F":
            continue
        
        c_type = hd.get("course_type")
        if not c_type or c_type.strip() == "":
            c_type = get_course_category(hd["course_code"], courses_db)
            
        if c_type in ("전공필수", "전공선택"):
            major_courses_count += 1
        elif c_type in ("교양필수", "교양선택"):
            liberal_courses_count += 1

    # 4. 디지털 트윈 상태
    remaining_req = get_required_remaining(student)
    digital_twin = {
        "name": student["name"],
        "progress": int((student["completed_credits"] / student["required_credits"]) * 100) if student["required_credits"] > 0 else 0,
        "remainingCredits": max(0, student["required_credits"] - student["completed_credits"]),
        "aiProbability": 94 if len(remaining_req) == 0 else max(40, 94 - len(remaining_req) * 15),
        "expectedGraduation": "2027년 2월 (정기)",
        "completedCourses": len(completed_courses_list),
        "majorCourses": major_courses_count,
        "liberalCourses": liberal_courses_count,
        "scenarioCount": 3,
        "scenarioStatus": "안정" if len(remaining_req) == 0 else "주의"
    }

    def get_course_schedules(course_info: dict) -> list:
        schedules = []
        offs = course_info.get("offerings", [])
        if offs:
            # 2026-1학기 분반 우선
            primary = None
            for o in offs:
                if o.get("semester") == "1학기" and o.get("academic_year") == "2026":
                    primary = o
                    break
            if not primary:
                primary = offs[0]
            
            # primary 분반의 시간표를 프론트엔드 스키마로 변환
            # (day_of_week -> day, start_time, end_time, classroom -> classroom)
            for idx, slot in enumerate(primary.get("time_slots", [])):
                day, start_time, end_time = slot
                classroom = primary.get("classrooms")[idx] if idx < len(primary.get("classrooms", [])) else "미정"
                schedules.append({
                    "day": day,
                    "start_time": start_time,
                    "end_time": end_time,
                    "classroom": classroom,
                    "section": primary.get("section", "01"),
                    "professor": primary.get("professor", "미정")
                })
        return schedules

    # 5. AI 수강 추천 과목
    ai_courses = []
    colors = ["violet", "pink", "teal"]
    # 미이수 필수 과목과 수강 가능 추천 과목 조립
    for idx, r in enumerate(remaining_req[:5]):
        prof = r.get("professor", "미정")
        schedules = get_course_schedules(r)
        time_str = " / ".join(f"{s['day']} {s['start_time']}~{s['end_time']}" for s in schedules) if schedules else ""
        ai_courses.append({
            "id": f"ai-course-{r['code']}",
            "code": r["code"],
            "name": r["name"],
            "credit": r["credits"],
            "match": 98,
            "tags": ["전공필수", prof],
            "reason": "미이수한 전공필수 과목입니다.",
            "color": colors[idx % len(colors)],
            "professor": prof,
            "category": "전공필수",
            "time": time_str,
            "schedules": schedules
        })
    # 전공선택 추가
    if len(ai_courses) < 6:
        for code, info in list(courses_db.items()):
            if code not in student.get("completed_courses", []) and info["category"] == "전공선택":
                idx = len(ai_courses)
                prof = info.get("professor", "이교수")
                schedules = get_course_schedules(info)
                time_str = " / ".join(f"{s['day']} {s['start_time']}~{s['end_time']}" for s in schedules) if schedules else ""
                ai_courses.append({
                    "id": f"ai-course-{code}",
                    "code": code,
                    "name": info["name"],
                    "credit": info["credits"],
                    "match": 85,
                    "tags": ["전공선택", prof],
                    "reason": "추천 전공 트랙 관심 과목입니다.",
                    "color": colors[idx % len(colors)],
                    "professor": prof,
                    "category": "전공선택",
                    "time": time_str,
                    "schedules": schedules
                })
                if len(ai_courses) >= 6:
                    break

    user_info_mapped = map_user_info(student)
    user_info_mapped["completedCoursesDetail"] = completed_details

    return {
        "user": {
            "userInfo": user_info_mapped,
            "creditCategories": credit_categories,
            "quickMenus": [
                {"key": "diagnostic", "label": "졸업요건 진단", "icon": "GraduationCap", "title": "졸업요건 진단", "description": "나의 부족 학점 확인"},
                {"key": "recommend", "label": "AI 과목 추천", "icon": "Sparkles", "title": "AI 과목 추천", "description": "인공지능 시간표 추천"},
                {"key": "timetable", "label": "모의 시간표", "icon": "CalendarRange", "title": "모의 시간표", "description": "나만의 예비 시간표"}
            ]
        },
        "schedule": {
            "scheduleDays": ["월", "화", "수", "목", "금"],
            "scheduleHours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "scheduleBlocks": schedule_blocks,
            "scheduleReasons": schedule_reasons,
            "pastelPalette": [
                {"bg": "bg-[#e8f3ff]", "text": "text-[#1b64da]", "bar": "bg-[#3182f6]"},
                {"bg": "bg-[#daf2ee]", "text": "text-[#008f80]", "bar": "bg-[#00b5a3]"},
                {"bg": "bg-[#fff3f5]", "text": "text-[#d6284a]", "bar": "bg-[#f04452]"}
            ]
        },
        "notice": {
            "interestKeywords": [
                {"id": idx, "text": kw, "active": True}
                for idx, kw in enumerate(student.get("keyword_preferences", []))
            ],
            "urgentNotice": {
                "id": 100,
                "title": "[중요] 2026학년도 전기(2월) 예비졸업사정 대상자 조회 안내",
                "date": "2026-07-20",
                "isNew": True
            },
            "academicCalendar": academic_cal
        },
        "chat": {
            "recommendedCourses": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "professor": c["professor"],
                    "credit": c["credit"],
                    "time": "월 10:30 ~ 12:00",
                    "match": c["match"],
                    "tags": [c["category"], "추천"],
                    "retake": False
                }
                for c in ai_courses[:4]
            ],
            "chatSimSummary": {
                "avgMatch": 94,
                "freeDay": "금요일",
                "totalCredits": sum(c["credit"] for c in ai_courses[:4]),
                "courseCount": len(ai_courses[:4]),
                "reasons": [
                    {"icon": "GraduationCap", "text": "필수과목 모두 배치 완료"},
                    {"icon": "CalendarOff", "text": "금요일 공강 보장"}
                ]
            }
        },
        "digitalTwin": digital_twin,
        "aiRecommendation": {
            "aiFilters": [
                {"key": "all", "label": "전체"},
                {"key": "major", "label": "전공필수/선택"},
                {"key": "liberal", "label": "교양"},
                {"key": "settings", "label": "설정", "addOnly": True}
            ],
            "aiCourses": ai_courses
        }
    }

@router.put("/courses", summary="기수강 과목 목록 갱신 API")
def update_completed_courses(
    req: UpdateCoursesRequest,
    db: Session = Depends(get_db)
):
    student = get_student(req.studentId)
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
        
    # 빈 요청 방지 가드 완화 (None일 때만 방지)
    if req.completedCourses is None:
        return {
            "success": True, 
            "completed_credits": student.get("completed_credits", 0),
            "completed_courses_count": len(student.get("completed_courses", []))
        }

    courses_db = load_courses()
    
    # 기수강 과목 목록 업데이트
    student["completed_courses"] = req.completedCourses
    
    # 이수한 과목들의 총 학점 합산 및 completed_credits 업데이트
    total_credits = 0
    for code in req.completedCourses:
        course = courses_db.get(code)
        if course:
            total_credits += course.get("credits", 3)
        else:
            total_credits += 3 # 매칭 코드가 없으면 기본 3학점 취급
            
    student["completed_credits"] = total_credits
    
    # 변경 사항을 STUDENTS에 저장
    STUDENTS[req.studentId] = student
    
    # --- [실제 SQLite DB 동기화 - 보존형 리팩토링] ---
    try:
        student_id_int = int(req.studentId)
        
        # 1. 기존 DB에 있던 수강 기록들을 리스트로 백업해둡니다. (학기와 성적 보존 목적, 중복 수강 보존)
        from collections import defaultdict
        existing_histories = db.query(models.StudentCourseHistory).filter(
            models.StudentCourseHistory.student_id == student_id_int
        ).all()
        
        history_backup = defaultdict(list)
        for h in existing_histories:
            history_backup[h.course_id].append({
                "semester_taken": h.semester_taken,
                "grade": h.grade,
                "earned_credit": h.earned_credit,
                "completion_status": h.completion_status,
                "is_retake": h.is_retake
            })
            
        # 기존 히스토리 중 가장 최근 학기 구하기 (기본값용)
        latest_sem = "2026-1학기"
        if existing_histories:
            sems = [h.semester_taken for h in existing_histories if h.semester_taken]
            if sems:
                latest_sem = sorted(sems, reverse=True)[0]
 
        # 2. 기존 수강기록 전체 삭제
        db.query(models.StudentCourseHistory).filter(
            models.StudentCourseHistory.student_id == student_id_int
        ).delete()
        
        # 3. 새로운 수강기록 bulk 추가 (백업된 값 보존)
        for code in req.completedCourses:
            c_record = db.query(models.Course).filter(models.Course.course_code == code).first()
            if not c_record:
                # CSV 로더 캐시에서 정보 조회하여 SQLite DB에 Course 레코드 즉시 동기화 생성
                from backend.core.data.csv_loader import load_courses
                courses_db = load_courses()
                c_info = courses_db.get(code)
                if c_info:
                    credit_val_temp = float(c_info.get("credits", 3.0))
                    new_c = models.Course(
                        course_code=code,
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

            c_id = c_record.course_id if c_record else None
            credit_val = 3.0
            if c_record:
                if getattr(c_record, 'credit', None) is not None:
                    credit_val = float(c_record.credit)
            if not c_id:
                import re
                nums = re.findall(r'\d+', code)
                fallback_id = int(nums[0]) if nums else 1001
                if fallback_id == 1 or fallback_id == 0:
                    fallback_id = 9999
                c_id = fallback_id
                
            backups = history_backup.get(c_id)
            if backups and len(backups) > 0:
                backup = backups.pop(0)
                sem = backup["semester_taken"]
                grade = backup["grade"]
                credit = backup["earned_credit"]
                status = backup["completion_status"]
                is_ret = backup.get("is_retake", False)
            else:
                sem = req.targetSemester or latest_sem
                grade = "A+"
                credit = credit_val
                status = "이수"
                is_ret = False
                
            new_hist = models.StudentCourseHistory(
                student_id=student_id_int,
                course_id=c_id,
                semester_taken=sem,
                grade=grade,
                earned_credit=credit,
                completion_status=status,
                is_retake=is_ret
            )
            db.add(new_hist)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Bulk Sync SQLite Error: {e}")
    # -----------------------------
    
    return {
        "success": True, 
        "completed_credits": total_credits,
        "completed_courses_count": len(req.completedCourses)
    }