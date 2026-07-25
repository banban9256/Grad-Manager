# app/schemas.py
from pydantic import BaseModel, model_validator
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

class ProfileUpdateRequest(BaseModel):
    name: str
    studentId: str
    department: str
    mileage: Optional[int] = None
    current_semester: Optional[int] = None
    major_tracks: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_tracks(self) -> "ProfileUpdateRequest":
        if self.major_tracks:
            convergence_majors = {
                "인공지능소프트웨어융합전공",
                "디지털문화콘텐츠융합전공",
                "스마트경영융합전공",
                "공공서비스융합전공",
            }
            specialized_tracks = {
                "인지 감성 특화 트랙",
                "데이터 사이언스 트랙",
                "지능형 IoT 소프트웨어 트랙",
                "풀스택 웹/모바일 소프트웨어 트랙",
                "인지 감성 특화",
                "데이터 사이언스",
                "지능형 IoT 소프트웨어",
                "풀스택 웹/모바일 소프트웨어",
            }
            
            has_conv = any(track in convergence_majors for track in self.major_tracks)
            has_spec = any(track in specialized_tracks for track in self.major_tracks)
            
            if has_conv and has_spec:
                raise ValueError("융합전공과 특성화트랙은 동시에 선택할 수 없습니다.")
        return self