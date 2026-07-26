# app/routers/student.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Student, StudentCourseHistory
from app.schemas import StudentSyncRequest

# 기존에 만들어두신 졸업 요건/부족 학점 계산 로직 함수가 있다면 가져옵니다.
# (예시: from app.services.graduation import calculate_graduation_credits)

router = APIRouter(prefix="/api/v1/student", tags=["Student Sync"])

@router.post("/sync")
def sync_student_course_history(
    payload: StudentSyncRequest, 
    db: Session = Depends(get_db)
):
    """
    프론트엔드에서 전송한 학생 정보 및 수강 내역을 받아서
    DB에 직접 저장/업데이트하고 졸업 요건 계산 로직을 연결하는 API
    """
    # 1. 학생 정보(Student) DB 확인 및 저장/갱신
    student = db.query(Student).filter(Student.student_number == payload.student_number).first()
    
    if not student:
        student = Student(
            user_id=payload.user_id,
            student_number=payload.student_number,
            admission_year=payload.admission_year,
            current_grade=payload.current_grade
        )
        db.add(student)
        db.flush()  # student_id 값을 즉시 얻기 위해 처리
    else:
        student.admission_year = payload.admission_year
        student.current_grade = payload.current_grade

    # 2. 기존 해당 학생의 수강 내역을 지우고 최신 내역으로 재등록 (덮어쓰기)
    db.query(StudentCourseHistory).filter(
        StudentCourseHistory.student_id == student.student_id
    ).delete()

    # 3. 전달받은 수강 내역 DB(student_course_history)에 일괄 저장
    for item in payload.course_history:
        history_entry = StudentCourseHistory(
            student_id=student.student_id,
            course_id=item.course_id,
            semester_taken=item.semester_taken,
            grade=item.grade,
            earned_credit=item.earned_credit,
            completion_status=item.completion_status,
            is_retake=item.is_retake,
            course_type=item.course_type
        )
        db.add(history_entry)

    db.commit()

    # 4. 이전에 질문자님이 구현하신 '부족한 학점 계산 로직' 호출 (있다면 주석 해제)
    # simulation_result = calculate_graduation_credits(db, student.student_id)

    return {
        "status": "success",
        "message": "학생 정보 및 수강 내역 데이터가 성공적으로 DB에 저장되었습니다.",
        "student_id": student.student_id,
        # "simulation": simulation_result
    }