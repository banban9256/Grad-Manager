from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional
from backend.core.data.students import get_student, STUDENTS
from backend.core.data.csv_loader import load_courses

router = APIRouter()

class LoginRequest(BaseModel):
    studentId: str
    password: str

class RegisterRequest(BaseModel):
    studentId: str
    password: str
    name: str
    department: str

def map_user_info(student: dict) -> dict:
    completed = student.get("completed_credits", 0)
    required = student.get("required_credits", 130)
    
    completed_details = {}
    try:
        courses_db = load_courses()
        for code in student.get("completed_courses", []):
            course = courses_db.get(code)
            if course:
                completed_details[code] = course.get("name", "")
            else:
                completed_details[code] = "기수강 과목"
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

@router.post("/login", summary="실제 로그인 API")
def login(req: LoginRequest):
    student = get_student(req.studentId)
    if not student:
        raise HTTPException(status_code=400, detail="존재하지 않는 학번입니다.")
    
    # 가상 검증: 비밀번호는 학번과 동일하거나 임의 통과 처리
    # 실제 프로덕션 대응을 위해 간단 비밀번호 규칙 추가 (기본값은 '1234' 또는 학번 등)
    if req.password != "1234" and req.password != req.studentId:
        raise HTTPException(status_code=400, detail="비밀번호가 일치하지 않습니다. (기본 비밀번호: 1234 또는 학번)")
        
    return {
        "token": f"mock-jwt-token-{req.studentId}",
        "user": map_user_info(student)
    }

@router.post("/register", summary="실제 회원가입 API")
def register(req: RegisterRequest):
    if req.studentId in STUDENTS:
        raise HTTPException(status_code=400, detail="이미 등록된 학번입니다.")
        
    # STUDENTS 가상 데이터베이스에 추가
    STUDENTS[req.studentId] = {
        "name": req.name,
        "student_id": req.studentId,
        "department": req.department,
        "major_tracks": ["AISW 본전공"],
        "enrolled_year": int(req.studentId[:4]) if len(req.studentId) >= 4 else 2026,
        "current_semester": 1,
        "completed_credits": 0,
        "required_credits": 130,
        "completed_courses": [],
        "in_progress_courses": [],
        "gpa": 0.0,
        "mileage": 0,
        "keyword_preferences": [],
        "preferred_days": ["월", "화", "수", "목", "금"],
        "preferred_times": [],
        "avoid_times": [],
    }
    
    return {"message": "회원가입이 완료되었습니다."}

class ProfileUpdateRequest(BaseModel):
    name: str
    studentId: str
    department: str
    mileage: Optional[int] = None

@router.put("/profile", summary="실제 프로필 정보 수정 API")
def update_profile(req: ProfileUpdateRequest):
    student = get_student(req.studentId)
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
    student["name"] = req.name
    student["department"] = req.department
    if req.mileage is not None:
        student["mileage"] = req.mileage
    STUDENTS[req.studentId] = student
    return {"success": True}