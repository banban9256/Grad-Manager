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