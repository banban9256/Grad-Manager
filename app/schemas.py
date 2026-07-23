# app/schemas.py
from pydantic import BaseModel
from typing import Optional, List

# 개설 과목 응답 스키마
class CourseOfferingResponse(BaseModel):
    offering_id: int
    course_id: int
    academic_year: int
    semester: str
    section: Optional[str] = None
    professor_name: Optional[str] = None
    syllabus_url: Optional[str] = None

    class Config:
        from_attributes = True

# API 전체 응답 포맷 스키마
class CourseOfferingListResponse(BaseModel):
    status: str
    count: int
    data: List[CourseOfferingResponse]
    # app/schemas.py 맨 아래에 추가

# 1. 수강 이력 입력 요청 스키마
class CourseHistoryCreate(BaseModel):
    student_id: int
    course_id: int
    semester_taken: str = "2025-1학기"
    grade: str = "A+"

# 2. 부족 학점 요건 계산 응답 스키마
class GraduationSummaryResponse(BaseModel):
    status: str
    student_id: int
    total_required_credits: int      # 총 필요 학점 (예: 130)
    total_completed_credits: int     # 총 이수 학점
    total_remaining_credits: int     # 부족한 학점
    major_completed_credits: int     # 전공 이수 학점
    general_completed_credits: int   # 교양 이수 학점