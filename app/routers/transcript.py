from fastapi import APIRouter, Header, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import traceback

from backend.core.data.students import get_student, STUDENTS
from backend.core.pdf_parser import extract_text_from_pdf, parse_transcript_with_ai, match_courses_to_db
from backend.core.data.csv_loader import load_courses, hanja_to_hangul

router = APIRouter()


def get_student_from_token(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="인증 토큰이 없습니다. 로그인 후 이용해주세요.")
    try:
        token = authorization.split(" ")[1]
        student_id = token.replace("mock-jwt-token-", "")
        student = get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
        return student
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")


class TranscriptConfirmRequest(BaseModel):
    courses: List[dict]
    studentInfo: Optional[dict] = None


@router.post("/upload", summary="성적확인서 PDF 업로드 및 AI 파싱")
async def upload_transcript(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    """
    PDF 성적확인서를 업로드하면 AI가 자동으로 과목 정보를 추출합니다.
    추출된 과목은 확인 후 저장할 수 있습니다.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    student = get_student_from_token(authorization)
    student_id = student["student_id"]

    try:
        pdf_bytes = await file.read()
        if len(pdf_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기는 10MB 이하여야 합니다.")

        pdf_text = extract_text_from_pdf(pdf_bytes)
        if not pdf_text or len(pdf_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="PDF에서 텍스트를 추출할 수 없습니다. 스캔된 이미지 PDF는 지원하지 않습니다.")

        parsed_data = parse_transcript_with_ai(pdf_text)

        courses_db = load_courses()
        matched_results = match_courses_to_db(parsed_data.get("courses", []), courses_db)

        response_courses = []
        for m in matched_results:
            parsed = m["parsed"]
            entry = {
                "courseName": hanja_to_hangul(parsed.get("course_name", "")),
                "courseCode": m.get("matched_code") or parsed.get("course_code") or "",
                "courseType": parsed.get("course_type", "일반선택"),
                "credits": parsed.get("credits", 3.0),
                "grade": parsed.get("grade", ""),
                "semester": parsed.get("semester", ""),
                "matchConfidence": m.get("confidence", "none"),
                "dbMatched": m.get("matched_course") is not None,
                "dbName": hanja_to_hangul(m["matched_course"]["name"]) if m.get("matched_course") else "",
            }
            response_courses.append(entry)

        return {
            "success": True,
            "studentInfo": parsed_data.get("student_info", {}),
            "courses": response_courses,
            "totalExtracted": len(response_courses),
            "totalMatched": sum(1 for c in response_courses if c["dbMatched"]),
            "message": f"{len(response_courses)}개 과목이 추출되었습니다. ({sum(1 for c in response_courses if c['dbMatched'])}개 DB 매칭 완료)"
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF 파싱 중 오류가 발생했습니다: {str(e)}")


@router.post("/confirm", summary="추출된 과목 목록을 DB에 저장")
def confirm_transcript_courses(
    req: TranscriptConfirmRequest,
    authorization: Optional[str] = Header(None)
):
    """
    AI가 추출한 과목 목록을 확인하고 DB에 저장합니다.
    student_course_history + courses 테이블에 저장됩니다.
    """
    student = get_student_from_token(authorization)
    student_id = student["student_id"]
    student_id_int = int(student_id)

    try:
        from app.database import SessionLocal
        from app import models

        db = SessionLocal()
        try:
            courses_db = load_courses()

            saved_count = 0
            skipped_count = 0
            completed_codes = list(student.get("completed_courses", []))
            total_credits = 0

            for course_data in req.courses:
                course_name = hanja_to_hangul(course_data.get("courseName", ""))
                course_code = course_data.get("courseCode", "")
                course_type = course_data.get("courseType", "일반선택")
                credits = float(course_data.get("credits", 3.0))
                grade = course_data.get("grade", "A+")
                semester = course_data.get("semester", "")

                if not course_name:
                    skipped_count += 1
                    continue

                existing_code = course_code if course_code else None
                c_record = None

                if existing_code:
                    c_record = db.query(models.Course).filter(
                        models.Course.course_code == existing_code
                    ).first()

                if not c_record and course_name:
                    c_record = db.query(models.Course).filter(
                        models.Course.course_name == course_name
                    ).first()

                if not c_record:
                    new_course_code = course_code if course_code else f"TRANS-{student_id}-{saved_count}"
                    c_record = models.Course(
                        course_code=new_course_code,
                        course_name=course_name,
                        credit=credits,
                        source_url="transcript_upload",
                        theory_hours=0.0,
                        practice_hours=0.0,
                        course_description=f"성적확인서에서 자동 추출된 과목 ({course_type})"
                    )
                    db.add(c_record)
                    db.commit()
                    db.refresh(c_record)

                existing_history = db.query(models.StudentCourseHistory).filter(
                    models.StudentCourseHistory.student_id == student_id_int,
                    models.StudentCourseHistory.course_id == c_record.course_id
                ).first()

                if existing_history:
                    if grade and grade != "F":
                        existing_history.grade = grade
                        existing_history.earned_credit = credits
                        existing_history.semester_taken = semester
                        existing_history.course_type = course_type
                        existing_history.completion_status = "이수"
                    skipped_count += 1
                else:
                    new_history = models.StudentCourseHistory(
                        student_id=student_id_int,
                        course_id=c_record.course_id,
                        semester_taken=semester,
                        grade=grade,
                        earned_credit=credits,
                        completion_status="이수",
                        is_retake=False,
                        course_type=course_type,
                    )
                    db.add(new_history)
                    saved_count += 1

                if grade and grade.upper() != "F" and grade.upper() != "NP":
                    actual_code = c_record.course_code
                    if actual_code and actual_code not in completed_codes:
                        completed_codes.append(actual_code)
                        total_credits += credits

            db.commit()

            student["completed_courses"] = completed_codes
            student["completed_credits"] = sum(
                courses_db.get(code, {}).get("credits", 3.0)
                for code in completed_codes
                if courses_db.get(code)
            )
            STUDENTS[student_id] = student

            return {
                "success": True,
                "savedCount": saved_count,
                "skippedCount": skipped_count,
                "totalCompletedCourses": len(completed_codes),
                "totalCredits": student["completed_credits"],
                "message": f"{saved_count}개 과목이 저장되었습니다. (이미 존재하여 스킵: {skipped_count}개)"
            }

        finally:
            db.close()

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"과목 저장 중 오류가 발생했습니다: {str(e)}")
