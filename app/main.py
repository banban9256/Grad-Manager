# app/main.py
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app import models, schemas

app = FastAPI(title="GradManager API")

# 프론트엔드 통신 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    new_history = models.StudentCourseHistory(
        student_id=history_data.student_id,
        course_id=history_data.course_id,
        semester_taken=history_data.semester_taken,
        grade=history_data.grade
    )
    db.add(new_history)
    db.commit()
    db.refresh(new_history)

    return {
        "status": "success",
        "message": "수강 이력이 성공적으로 저장되었습니다.",
        "history_id": new_history.history_id
    }

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

        for h in histories:
            # F학점 제외
            if getattr(h, 'grade', '') and str(h.grade).upper() == "F":
                continue

            # 기본 3학점 부여 (과목 DB 조회 실패 대비)
            credit_val = 3
            course_type = ""

            try:
                course = db.query(models.Course).filter(models.Course.course_id == h.course_id).first()
                if course:
                    if hasattr(course, 'credits') and course.credits:
                        credit_val = int(course.credits)
                    if hasattr(course, 'course_type') and course.course_type:
                        course_type = str(course.course_type)
            except Exception:
                pass

            total_completed += credit_val

            if "전공" in course_type:
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