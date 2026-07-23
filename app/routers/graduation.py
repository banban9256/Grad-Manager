from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from backend.core.data.students import get_student, STUDENTS
from backend.core.data.csv_loader import load_courses
from backend.core.data.courses import get_required_remaining
from backend.core.scheduler import generate_timetable
from backend.core.notifications import get_upcoming_alerts, search_notices

router = APIRouter()

class UpdateCoursesRequest(BaseModel):
    studentId: str
    completedCourses: List[str]

def get_student_from_token(authorization: Optional[str]) -> dict:
    # Authorization header 파싱하여 학번 추출
    if not authorization:
        # 헤더가 없으면 기본 데모 계정 반환
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

def map_user_info(student: dict) -> dict:
    completed = student.get("completed_credits", 0)
    required = student.get("required_credits", 130)
    
    completed_details = {}
    try:
        courses_db = load_courses()
        for code in student.get("completed_courses", []):
            course = courses_db.get(code)
            if course:
                completed_details[code] = course.get("name", code)
            else:
                completed_details[code] = code
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

@router.get("/summary", summary="종합 졸업학점 진단 결과 API")
def get_graduation_summary(authorization: Optional[str] = Header(None)):
    student = get_student_from_token(authorization)
    student_id = student["student_id"]
    
    courses_db = load_courses()
    
    # 1. creditCategories 계산
    # 카테고리별 기본 목표치 설정
    category_goals = {
        "전공필수": 18,
        "전공선택": 45,
        "교양필수": 14,
        "교양선택": 20,
        "계열공통": 12,
    }
    
    category_earned = {cat: 0 for cat in category_goals.keys()}
    category_earned["일반선택"] = 0
    
    for code in student.get("completed_courses", []):
        course = courses_db.get(code)
        if course:
            cat = course.get("category", "일반선택")
            credits = course.get("credits", 3)
            if cat in category_earned:
                category_earned[cat] += credits
            else:
                category_earned["일반선택"] += credits
        else:
            category_earned["일반선택"] += 3

    category_keys = {
        "전공필수": "major_req",
        "전공선택": "major_sel",
        "교양필수": "liberal_req",
        "교양선택": "liberal_sel",
        "계열공통": "core_common",
        "일반선택": "general_sel"
    }

    category_tones = {
        "전공필수": "chart-1",
        "전공선택": "chart-2",
        "교양필수": "chart-3",
        "교양선택": "chart-1",
        "계열공통": "chart-2",
        "일반선택": "chart-3"
    }

    credit_categories = []
    for cat, req_credits in category_goals.items():
        credit_categories.append({
            "key": category_keys.get(cat, "etc"),
            "label": cat,
            "current": int(category_earned[cat]),
            "required": req_credits,
            "tone": category_tones.get(cat, "chart-1")
        })
    # 일반선택 추가
    credit_categories.append({
        "key": "general_sel",
        "label": "일반선택",
        "current": int(category_earned["일반선택"]),
        "required": 21,
        "tone": "chart-3"
    })

    # 2. 시간표 추천 데이터 (첫 번째 시간표를 scheduleBlocks 형태로 파싱)
    schedules = generate_timetable(student, max_schedules=1)
    schedule_blocks = []
    schedule_reasons = []
    
    if schedules:
        sched = schedules[0]
        # Pastel Color mapping
        pastel_palette = [
            {"bg": "bg-[#e8f3ff]", "text": "text-[#1b64da]", "bar": "bg-[#3182f6]"},
            {"bg": "bg-[#daf2ee]", "text": "text-[#008f80]", "bar": "bg-[#00b5a3]"},
            {"bg": "bg-[#fff3f5]", "text": "text-[#d6284a]", "bar": "bg-[#f04452]"},
            {"bg": "bg-[#f4edff]", "text": "text-[#6b31f6]", "bar": "bg-[#8f5cf0]"},
            {"bg": "bg-[#fffae8]", "text": "text-[#b08b00]", "bar": "bg-[#ffc900]"}
        ]
        
        day_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4}
        
        for idx, c in enumerate(sched["courses"]):
            color = pastel_palette[idx % len(pastel_palette)]
            for d, start, end in c.get("time_slots", []):
                if d in day_map:
                    # '09:00' -> 9.0
                    try:
                        sh, sm = map(int, start.split(":"))
                        eh, em = map(int, end.split(":"))
                        start_h = sh + sm / 60
                        end_h = eh + em / 60
                        
                        schedule_blocks.append({
                          "id": f"block-{c['code']}-{d}",
                          "name": c["name"],
                          "professor": c["professor"],
                          "day": day_map[d],
                          "start": start_h,
                          "end": end_h,
                          "color": color["bg"],
                          "textColor": color["text"]
                        })
                    except Exception:
                        pass
        
        schedule_reasons = [
            {"icon": "GraduationCap", "text": "졸업 필수 과목 배치 완료"},
            {"icon": "CalendarOff", "text": "선호하시는 요일 최적 배정"},
            {"icon": "BrainCircuit", "text": "여유로운 점심 시간대 보장"}
        ]
    else:
        schedule_reasons = [{"icon": "AlertTriangle", "text": "조건에 맞는 추천 시간표가 없습니다."}]

    # 3. 공지 알림 데이터
    notice_alerts = get_upcoming_alerts(30)
    academic_cal = []
    for a in notice_alerts:
        academic_cal.append({
            "id": a.get("id", 1),
            "title": a.get("alert_message", ""),
            "date": a.get("start_date", "2026-08-01"),
            "category": "일반",
            "isNew": True
        })
    if not academic_cal:
        academic_cal = [
            {"id": 1, "title": "2026학년도 2학기 수강신청 안내", "date": "2026-08-10", "category": "학사", "isNew": True},
            {"id": 2, "title": "졸업앨범 촬영 일정 안내", "date": "2026-09-15", "category": "학사", "isNew": False}
        ]

    # 4. 디지털 트윈 상태
    remaining_req = get_required_remaining(student)
    digital_twin = {
        "name": student["name"],
        "progress": int((student["completed_credits"] / student["required_credits"]) * 100) if student["required_credits"] > 0 else 0,
        "remainingCredits": max(0, student["required_credits"] - student["completed_credits"]),
        "aiProbability": 94 if len(remaining_req) == 0 else max(40, 94 - len(remaining_req) * 15),
        "expectedGraduation": "2027년 2월 (정기)",
        "completedCourses": len(student.get("completed_courses", [])),
        "majorCourses": len([c for c in student.get("completed_courses", []) if courses_db.get(c, {}).get("category") in ("전공필수", "전공선택")]),
        "liberalCourses": len([c for c in student.get("completed_courses", []) if courses_db.get(c, {}).get("category") in ("교양필수", "교양선택", "교양")]),
        "scenarioCount": 3,
        "scenarioStatus": "안정" if len(remaining_req) == 0 else "주의"
    }

    # 5. AI 수강 추천 과목
    ai_courses = []
    colors = ["violet", "pink", "teal"]
    # 미이수 필수 과목과 수강 가능 추천 과목 조립
    for idx, r in enumerate(remaining_req[:5]):
        prof = r.get("professor", "미지정")
        ai_courses.append({
            "id": f"ai-course-{r['code']}",
            "code": r["code"],
            "name": r["name"],
            "credit": r["credits"],
            "match": 98,
            "tags": ["전공필수", prof],
            "reason": "미이수한 전공필수 과목입니다.",
            "color": colors[idx % len(colors)],
            "professor": prof,
            "category": "전공필수"
        })
    # 전공선택 추가
    if len(ai_courses) < 6:
        for code, info in list(courses_db.items()):
            if code not in student.get("completed_courses", []) and info["category"] == "전공선택":
                idx = len(ai_courses)
                prof = info.get("professor", "이교수")
                ai_courses.append({
                    "id": f"ai-course-{code}",
                    "code": code,
                    "name": info["name"],
                    "credit": info["credits"],
                    "match": 85,
                    "tags": ["전공선택", prof],
                    "reason": "추천 전공 트랙 관심 과목입니다.",
                    "color": colors[idx % len(colors)],
                    "professor": prof,
                    "category": "전공선택"
                })
                if len(ai_courses) >= 6:
                    break

    return {
        "user": {
            "userInfo": map_user_info(student),
            "creditCategories": credit_categories,
            "quickMenus": [
                {"key": "diagnostic", "label": "졸업요건 진단", "icon": "GraduationCap", "title": "졸업요건 진단", "description": "나의 부족 학점 확인"},
                {"key": "recommend", "label": "AI 과목 추천", "icon": "Sparkles", "title": "AI 과목 추천", "description": "인공지능 시간표 추천"},
                {"key": "timetable", "label": "모의 시간표", "icon": "CalendarRange", "title": "모의 시간표", "description": "나만의 예비 시간표"}
            ]
        },
        "schedule": {
            "scheduleDays": ["월", "화", "수", "목", "금"],
            "scheduleHours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "scheduleBlocks": schedule_blocks,
            "scheduleReasons": schedule_reasons,
            "pastelPalette": [
                {"bg": "bg-[#e8f3ff]", "text": "text-[#1b64da]", "bar": "bg-[#3182f6]"},
                {"bg": "bg-[#daf2ee]", "text": "text-[#008f80]", "bar": "bg-[#00b5a3]"},
                {"bg": "bg-[#fff3f5]", "text": "text-[#d6284a]", "bar": "bg-[#f04452]"}
            ]
        },
        "notice": {
            "interestKeywords": [
                {"id": idx, "text": kw, "active": True}
                for idx, kw in enumerate(student.get("keyword_preferences", []))
            ],
            "urgentNotice": {
                "id": 100,
                "title": "[중요] 2026학년도 전기(2월) 예비졸업사정 대상자 조회 안내",
                "date": "2026-07-20",
                "isNew": True
            },
            "academicCalendar": academic_cal
        },
        "chat": {
            "recommendedCourses": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "professor": c["professor"],
                    "credit": c["credit"],
                    "time": "월 10:30 ~ 12:00",
                    "match": c["match"],
                    "tags": [c["category"], "추천"],
                    "retake": False
                }
                for c in ai_courses[:4]
            ],
            "chatSimSummary": {
                "avgMatch": 94,
                "freeDay": "금요일",
                "totalCredits": sum(c["credit"] for c in ai_courses[:4]),
                "courseCount": len(ai_courses[:4]),
                "reasons": [
                    {"icon": "GraduationCap", "text": "필수과목 모두 배치 완료"},
                    {"icon": "CalendarOff", "text": "금요일 공강 보장"}
                ]
            }
        },
        "digitalTwin": digital_twin,
        "aiRecommendation": {
            "aiFilters": [
                {"key": "all", "label": "전체"},
                {"key": "major", "label": "전공필수/선택"},
                {"key": "liberal", "label": "교양"},
                {"key": "settings", "label": "설정", "addOnly": True}
            ],
            "aiCourses": ai_courses
        }
    }

@router.put("/courses", summary="기수강 과목 목록 갱신 API")
def update_completed_courses(req: UpdateCoursesRequest):
    student = get_student(req.studentId)
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
        
    courses_db = load_courses()
    
    # 기수강 과목 목록 업데이트
    student["completed_courses"] = req.completedCourses
    
    # 이수한 과목들의 총 학점 합산 및 completed_credits 업데이트
    total_credits = 0
    for code in req.completedCourses:
        course = courses_db.get(code)
        if course:
            total_credits += course.get("credits", 3)
        else:
            total_credits += 3 # 매칭 코드가 없으면 기본 3학점 취급
            
    student["completed_credits"] = total_credits
    
    # 변경 사항을 STUDENTS에 저장
    STUDENTS[req.studentId] = student
    
    return {
        "success": True, 
        "completed_credits": total_credits,
        "completed_courses_count": len(req.completedCourses)
    }