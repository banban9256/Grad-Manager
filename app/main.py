# app/main.py
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app import models, schemas
from app.routers import auth, graduation, timetable, notices, chatbot

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

@app.get("/")
def read_root():
    return {"message": "GradManager 백엔드 서버가 정상 작동 중입니다!"}

# [실제 DB 연동 API] 개설 과목 목록 조회 (검색 및 페이징 지원)
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