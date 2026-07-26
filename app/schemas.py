# app/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Union

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
    course_id: Optional[Union[int, str]] = None
    semester_taken: str = "2025-1학기"
    grade: str = "A+"
    custom_course_name: Optional[str] = None
    credits: Optional[float] = None
    course_type: Optional[str] = None
    is_retake: Optional[bool] = False

# 2. 부족 학점 요건 계산 응답 스키마
class GraduationSummaryResponse(BaseModel):
    status: str
    student_id: int
    total_required_credits: float      # 총 필요 학점 (예: 130)
    total_completed_credits: float     # 총 이수 학점
    total_remaining_credits: float     # 부족한 학점
    major_completed_credits: float     # 전공 이수 학점
    general_completed_credits: float   # 교양 이수 학점

class CourseHistoryUpdate(BaseModel):
    semester_taken: Optional[str] = None
    grade: Optional[str] = None
    course_id: Optional[Union[int, str]] = None
    course_name: Optional[str] = None
    earned_credit: Optional[float] = None
    is_retake: Optional[bool] = None
    course_type: Optional[str] = None

    # app/schemas.py
from pydantic import BaseModel
from typing import List, Optional

# 프론트엔드에서 수강 내역 배열 항목으로 들어올 개별 과목 데이터
class CourseHistoryInput(BaseModel):
    course_id: int
    semester_taken: Optional[str] = "2025-1"
    grade: Optional[str] = "A+"
    earned_credit: float = 3.0
    completion_status: str = "이수"
    is_retake: bool = False
    course_type: Optional[str] = "일반선택"  # 예: 전공필수, 전공선택, 교양 등

# 프론트엔드에서 보낼 학생 기본 정보 + 수강 내역 전체 요청 데이터
class StudentSyncRequest(BaseModel):
    user_id: int
    student_number: str       # 학번 (예: "20231234")
    admission_year: int       # 입학연도 (예: 2023)
    current_grade: int        # 학년 (예: 3)
    course_history: List[CourseHistoryInput]  # 수강 과목 목록