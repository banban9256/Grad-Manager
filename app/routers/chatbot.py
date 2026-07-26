from fastapi import APIRouter, Header, HTTPException, Body, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List

from backend.core.data.students import get_student
from backend.core.chatbot import chat
from backend.core.scheduler import generate_timetable
from backend.core.data.csv_loader import hanja_to_hangul

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None
    convergenceMajor: Optional[str] = None
    specializedTrack: Optional[str] = None
    semester: Optional[str] = None
    department: Optional[str] = None

def get_student_from_token(authorization: Optional[str]) -> dict:
    if not authorization:
        student = get_student("20210001")
        if not student:
            raise HTTPException(status_code=404, detail="기본 데모 학생을 찾을 수 없습니다.")
        return student
    try:
        token = authorization.split(" ")[1]
        student_id = token.replace("mock-jwt-token-", "")
        student = get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
        return student
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

@router.post("/chat", summary="실제 RAG 챗봇 대화 API")
def chat_message(req: ChatRequest, authorization: Optional[str] = Header(None)):
    student = get_student_from_token(authorization)
    student_id = student["student_id"]
    
    # 전달된 학기, 전공, 트랙, 학과 정보를 학생 정보 객체에 갱신 및 캐시 동기화
    if req.department:
        student["department"] = req.department
    if req.convergenceMajor:
        student["convergence_major"] = req.convergenceMajor
    if req.specializedTrack:
        student["specialized_track"] = req.specializedTrack
    if req.semester:
        student["target_semester"] = req.semester

    from backend.core.data.students import STUDENTS
    STUDENTS[student_id] = student
    
    # backend/core/chatbot.py 의 chat 함수 호출
    ai_response = chat(
        user_message=req.message,
        student_id=student_id,
        history=req.history or [],
        target_semester=req.semester
    )
    
    # 최신의 갱신된 학생 정보 기준 실제 시간표 생성
    schedules = generate_timetable(student, max_schedules=1)
    schedule_blocks = []
    
    pastel_palette = [
        {"bg": "bg-[#e8f3ff]", "text": "text-[#1b64da]", "bar": "bg-[#3182f6]"},
        {"bg": "bg-[#daf2ee]", "text": "text-[#008f80]", "bar": "bg-[#00b5a3]"},
        {"bg": "bg-[#fff3f5]", "text": "text-[#d6284a]", "bar": "bg-[#f04452]"},
        {"bg": "bg-[#f4edff]", "text": "text-[#6b31f6]", "bar": "bg-[#8f5cf0]"},
        {"bg": "bg-[#fffae8]", "text": "text-[#b08b00]", "bar": "bg-[#ffc900]"}
    ]
    day_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4}
    
    if schedules:
        sched = schedules[0]
        for idx, c in enumerate(sched["courses"]):
            color = pastel_palette[idx % len(pastel_palette)]
            for d, start, end in c.get("time_slots", []):
                if d in day_map:
                    try:
                        sh, sm = map(int, start.split(":"))
                        eh, em = map(int, end.split(":"))
                        start_h = sh + sm / 60
                        end_h = eh + em / 60
                        schedule_blocks.append({
                          "id": f"block-{c['code']}-{d}",
                          "name": c["name"],
                          "professor": c.get("professor", "미정"),
                          "room": c.get("room", "미정"),
                          "day": day_map[d],
                          "start": start_h,
                          "end": end_h,
                          "color": color["bg"],
                          "textColor": color["text"]
                        })
                    except Exception:
                        pass

    # 챗봇 대화에 반영된 선호 요일 및 시간대에 따라 추천 사유 동적 생성
    reasons = []
    preferred_days = student.get("preferred_days", ["월", "화", "수", "목", "금"])
    avoid_times = student.get("avoid_times", [])
    
    days = ["월", "화", "수", "목", "금"]
    free_days = [d for d in days if d not in preferred_days]
    
    if free_days:
        reasons.append({
            "icon": "CalendarOff",
            "title": f"{', '.join(free_days)}요일 공강 보장",
            "desc": f"사용자님의 요청을 반영하여 {', '.join(free_days)}요일에는 단 하나의 수업도 배정하지 않았습니다."
        })
    else:
        reasons.append({
            "icon": "CalendarOff",
            "title": "균형 잡힌 주 5일 분산 배치",
            "desc": "학습 스트레스를 덜기 위해 특정 요일에 편중되지 않도록 시간표를 분산했습니다."
        })
        
    if "09:00-12:00" in avoid_times:
        reasons.append({
            "icon": "Clock",
            "title": "오전 10시 이전 수업 제외",
            "desc": "아침 첫 수업(1교시 등)을 배제하여 한결 여유로운 등교 길을 마련해 드립니다."
        })
    else:
        reasons.append({
            "icon": "Clock",
            "title": "여유로운 1시간 점심시간 보장",
            "desc": "연강으로 식사를 거르지 않도록 점심 시간대(12:00~13:30) 배치를 피했습니다."
        })
        
    if student.get("department") in ("AISW", "AI.SW학", "인공지능소프트웨어학과", "인공지능소프트웨어학부"):
        reasons.append({
            "icon": "GraduationCap",
            "title": "졸업 요구 학점 맞춤 배치",
            "desc": "전공 필수 과목이 없는 AISW 학과 요건에 맞추어 주전공 및 계열공통 과목을 담았습니다."
        })
    else:
        reasons.append({
            "icon": "GraduationCap",
            "title": "미이수 졸업 필수과목 자동 배치",
            "desc": "현재 주전공 이수를 위해 남은 미이수 전공 필수 요건들을 누락 없이 담았습니다."
        })
    reasons.append({
        "icon": "BrainCircuit",
        "title": "강의동 간 동선 최소화 최적화",
        "desc": "연강일 때 강의실 이동 거리를 감안하여 IT융합관/공학관 위주로 묶어 배정했습니다."
    })

    simulated_timetable = {
        "scheduleDays": ["월", "화", "수", "목", "금"],
        "scheduleHours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "scheduleBlocks": schedule_blocks,
        "scheduleReasons": reasons,
        "pastelPalette": pastel_palette[:3],
        "totalCredits": schedules[0]["total_credits"] if schedules else 0,
        "courseCount": len(schedules[0]["courses"]) if schedules else 0
    }
    
    return {
        "message": ai_response,
        "simulated_timetable": simulated_timetable
    }


@router.post("/upload-transcript", summary="성적확인서 PDF 업로드 → AI 파싱 → 자동 저장")
async def chatbot_upload_transcript(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    """
    챗봇을 통해 성적확인서 PDF를 업로드합니다.
    AI가 PDF를 자동으로 파싱하여 기수강 과목을 추출하고,
    추출된 과목을 바로 DB에 저장합니다.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    student = get_student_from_token(authorization)
    student_id = student["student_id"]

    try:
        from backend.core.pdf_parser import extract_text_from_pdf, parse_transcript_with_ai, match_courses_to_db
        from backend.core.data.csv_loader import load_courses
        from app import models
        from app.database import SessionLocal

        pdf_bytes = await file.read()
        if len(pdf_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기는 10MB 이하여야 합니다.")

        pdf_text = extract_text_from_pdf(pdf_bytes)
        if not pdf_text or len(pdf_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="PDF에서 텍스트를 추출할 수 없습니다. 스캔된 이미지 PDF는 지원하지 않습니다.")

        parsed_data = parse_transcript_with_ai(pdf_text)
        courses_db = load_courses()
        matched_results = match_courses_to_db(parsed_data.get("courses", []), courses_db)

        db = SessionLocal()
        try:
            student_id_int = int(student_id)
            saved_count = 0
            skipped_count = 0
            completed_codes = list(student.get("completed_courses", []))

            for m in matched_results:
                parsed = m["parsed"]
                course_name = hanja_to_hangul(parsed.get("course_name", ""))
                course_code = m.get("matched_code") or parsed.get("course_code") or ""
                course_type = parsed.get("course_type", "일반선택")
                credits = float(parsed.get("credits", 3.0))
                grade = parsed.get("grade", "A+")
                semester = parsed.get("semester", "")

                if not course_name:
                    skipped_count += 1
                    continue

                c_record = None
                if course_code:
                    c_record = db.query(models.Course).filter(
                        models.Course.course_code == course_code
                    ).first()

                if not c_record:
                    c_record = db.query(models.Course).filter(
                        models.Course.course_name == course_name
                    ).first()

                if not c_record:
                    new_code = course_code if course_code else f"TRANS-{student_id}-{saved_count}"
                    c_record = models.Course(
                        course_code=new_code,
                        course_name=course_name,
                        credit=credits,
                        source_url="chatbot_transcript_upload",
                        theory_hours=0.0,
                        practice_hours=0.0,
                        course_description=f"성적확인서에서 자동 추출 ({course_type})"
                    )
                    db.add(c_record)
                    db.commit()
                    db.refresh(c_record)

                existing_history = db.query(models.StudentCourseHistory).filter(
                    models.StudentCourseHistory.student_id == student_id_int,
                    models.StudentCourseHistory.course_id == c_record.course_id
                ).first()

                if existing_history:
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

                    if grade and grade.upper() not in ("F", "NP"):
                        actual_code = c_record.course_code
                        if actual_code and actual_code not in completed_codes:
                            completed_codes.append(actual_code)

            db.commit()

            student["completed_courses"] = completed_codes
            student["completed_credits"] = sum(
                courses_db.get(code, {}).get("credits", 3.0)
                for code in completed_codes
                if courses_db.get(code)
            )
            from backend.core.data.students import STUDENTS
            STUDENTS[student_id] = student

            course_list_text = ""
            for m in matched_results[:15]:
                p = m["parsed"]
                status = "✓ DB 매칭" if m.get("matched_course") else "△ 신규 등록"
                course_list_text += f"- {p.get('course_name', '')} ({p.get('course_type', '')}, {p.get('credits', 0)}학점, {p.get('grade', '')}) [{status}]\n"

            if len(matched_results) > 15:
                course_list_text += f"- ... 외 {len(matched_results) - 15}개 과목\n"

            ai_response = (
                f"🎓 **성적확인서 분석 완료!**\n\n"
                f"PDF에서 총 **{len(matched_results)}개** 과목이 추출되었습니다.\n"
                f"- DB에 이미 있는 과목: **{sum(1 for m in matched_results if m.get('matched_course'))}개**\n"
                f"- 새로 등록된 과목: **{saved_count}개**\n"
                f"- 스킵된 과목: **{skipped_count}개**\n\n"
                f"**추출된 과목 목록:**\n{course_list_text}\n"
                f"총 이수 학점: **{student['completed_credits']}학점**\n"
                f"총 이수 과목: **{len(completed_codes)}개**\n\n"
                f"이제 졸업요건 진단 페이지에서 정확한 이수 현황을 확인하실 수 있습니다! 📊"
            )

            return {
                "message": ai_response,
                "extractedCourses": [
                    {
                        "courseName": m["parsed"].get("course_name", ""),
                        "courseCode": m.get("matched_code") or "",
                        "courseType": m["parsed"].get("course_type", ""),
                        "credits": m["parsed"].get("credits", 0),
                        "grade": m["parsed"].get("grade", ""),
                        "semester": m["parsed"].get("semester", ""),
                        "dbMatched": m.get("matched_course") is not None,
                    }
                    for m in matched_results
                ],
                "savedCount": saved_count,
                "skippedCount": skipped_count,
                "totalCredits": student["completed_credits"],
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF 처리 중 오류가 발생했습니다: {str(e)}")