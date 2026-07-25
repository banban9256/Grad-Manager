from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Student
from app import schemas
from backend.core.data.students import get_student, STUDENTS
from backend.core.data.csv_loader import load_courses
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

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
def login(req: LoginRequest, db: Session = Depends(get_db)):
    student = get_student(req.studentId)
    if not student:
        raise HTTPException(status_code=400, detail="존재하지 않는 학번입니다.")
    
    # SQLite DB에 사용자가 없는 경우 최초 생성 (동기화)
    db_student = db.query(Student).filter(Student.student_number == req.studentId).first()
    if not db_student:
        default_pwd = student.get("password") or "1234"
        max_user_id = db.query(func.max(User.user_id)).scalar() or 0
        next_user_id = max_user_id + 1

        new_user = User(
            user_id=next_user_id,
            login_id=req.studentId,
            password_hash=hash_password(default_pwd),
            role="STUDENT"
        )
        db.add(new_user)
        db.commit()

        max_student_id = db.query(func.max(Student.student_id)).scalar() or 0
        next_student_id = max_student_id + 1

        db_student = Student(
            student_id=next_student_id,
            user_id=next_user_id,
            student_number=req.studentId,
            admission_year=int(req.studentId[:4]) if len(req.studentId) >= 4 else 2026,
            current_grade=4
        )
        db.add(db_student)
        db.commit()

    db_user = db.query(User).filter(User.login_id == req.studentId).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="사용자 정보를 찾을 수 없습니다.")

    hashed_input = hash_password(req.password)
    if db_user.password_hash != hashed_input:
        raise HTTPException(status_code=400, detail="비밀번호가 일치하지 않습니다.")
        
    return {
        "token": f"mock-jwt-token-{req.studentId}",
        "user": map_user_info(student)
    }

@router.post("/register", summary="실제 회원가입 API")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if req.studentId in STUDENTS:
        raise HTTPException(status_code=400, detail="이미 등록된 학번입니다.")
        
    db_student = db.query(Student).filter(Student.student_number == req.studentId).first()
    if db_student:
        raise HTTPException(status_code=400, detail="이미 등록된 학번입니다.")
        
    # STUDENTS 가상 데이터베이스에 추가
    STUDENTS[req.studentId] = {
        "name": req.name,
        "password": req.password,
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
    
    # SQLite DB에 사용자와 학생 즉시 연동 생성
    max_user_id = db.query(func.max(User.user_id)).scalar() or 0
    next_user_id = max_user_id + 1

    new_user = User(
        user_id=next_user_id,
        login_id=req.studentId,
        password_hash=hash_password(req.password),
        role="STUDENT"
    )
    db.add(new_user)
    db.commit()

    max_student_id = db.query(func.max(Student.student_id)).scalar() or 0
    next_student_id = max_student_id + 1

    db_student_new = Student(
        student_id=next_student_id,
        user_id=next_user_id,
        student_number=req.studentId,
        admission_year=int(req.studentId[:4]) if len(req.studentId) >= 4 else 2026,
        current_grade=1
    )
    db.add(db_student_new)
    db.commit()
    
    return {"message": "회원가입이 완료되었습니다."}

@router.put("/profile", summary="실제 프로필 정보 수정 API")
def update_profile(req: schemas.ProfileUpdateRequest):
    student = get_student(req.studentId)
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
    student["name"] = req.name
    student["department"] = req.department
    if req.mileage is not None:
        student["mileage"] = req.mileage
    if req.current_semester is not None:
        student["current_semester"] = req.current_semester
    if req.major_tracks is not None:
        student["major_tracks"] = req.major_tracks
    STUDENTS[req.studentId] = student
    return {"success": True}

class PasswordChangeRequest(BaseModel):
    studentId: str
    currentPassword: str
    newPassword: str

@router.post("/change-password", summary="비밀번호 변경 API (DB 연동)")
@router.post("/password", summary="비밀번호 변경 API (하위 호환)")
def change_password_db(req: PasswordChangeRequest, db: Session = Depends(get_db)):
    student = get_student(req.studentId)
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")

    db_student = db.query(Student).filter(Student.student_number == req.studentId).first()
    if not db_student:
        default_pwd = student.get("password") or "1234"
        max_user_id = db.query(func.max(User.user_id)).scalar() or 0
        next_user_id = max_user_id + 1

        new_user = User(
            user_id=next_user_id,
            login_id=req.studentId,
            password_hash=hash_password(default_pwd),
            role="STUDENT"
        )
        db.add(new_user)
        db.commit()

        max_student_id = db.query(func.max(Student.student_id)).scalar() or 0
        next_student_id = max_student_id + 1

        db_student = Student(
            student_id=next_student_id,
            user_id=next_user_id,
            student_number=req.studentId,
            admission_year=int(req.studentId[:4]) if len(req.studentId) >= 4 else 2026,
            current_grade=4
        )
        db.add(db_student)
        db.commit()

    db_user = db.query(User).filter(User.login_id == req.studentId).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")

    hashed_current = hash_password(req.currentPassword)
    if db_user.password_hash != hashed_current:
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")

    if not req.newPassword or len(req.newPassword.strip()) == 0:
        raise HTTPException(status_code=400, detail="새 비밀번호를 입력해 주세요.")

    db_user.password_hash = hash_password(req.newPassword)
    db.commit()

    student["password"] = req.newPassword
    STUDENTS[req.studentId] = student

    return {"success": True, "message": "비밀번호가 성공적으로 변경되었습니다."}