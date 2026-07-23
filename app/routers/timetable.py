from fastapi import APIRouter, Header, HTTPException, Query
from typing import Optional, List

from backend.core.data.students import get_student
from backend.core.data.csv_loader import load_courses
from backend.core.scheduler import generate_timetable

router = APIRouter()

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

@router.get("/recommend", summary="실제 조건부 시간표 추천 API")
def get_recommendations(authorization: Optional[str] = Header(None)):
    student = get_student_from_token(authorization)
    schedules = generate_timetable(student, max_schedules=1)
    
    schedule_blocks = []
    schedule_reasons = []
    
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
            {"icon": "GraduationCap", "text": "미이수한 졸업 필수 1과목 자동 배정"},
            {"icon": "CalendarOff", "text": "선호 요일 최적 배정 완료"},
            {"icon": "BrainCircuit", "text": "이동 거리 최소화를 위한 한 건물 위주 배정"}
        ]
    else:
        schedule_reasons = [{"icon": "AlertTriangle", "text": "추천 조건에 맞는 조합이 존재하지 않습니다."}]

    return {
        "scheduleDays": ["월", "화", "수", "목", "금"],
        "scheduleHours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "scheduleBlocks": schedule_blocks,
        "scheduleReasons": schedule_reasons,
        "pastelPalette": pastel_palette[:3]
    }

@router.get("/mock-courses", summary="실제 개설 과목 목록 반환 (검색 지원)")
def get_all_courses(q: Optional[str] = Query(None, description="과목명 또는 코드 검색")):
    courses_db = load_courses()
    data = []
    
    for code, info in courses_db.items():
        if q:
            if q.lower() not in info["name"].lower() and q.lower() not in code.lower():
                continue
                
        # API 응답 포맷 맞춤
        schedules = []
        for o in info.get("offerings", []):
            for d, start, end in o.get("time_slots", []):
                schedules.append({
                    "day": d,
                    "start_time": start,
                    "end_time": end,
                    "classroom": o.get("classrooms", ["미정"])[0] if o.get("classrooms") else "미정"
                })
                
        data.append({
            "offering_id": info.get("offerings", [{}])[0].get("offering_id", 0) if info.get("offerings") else 0,
            "course_id": code,
            "title": info["name"],
            "credit": float(info["credits"]),
            "program_type": "MAJOR" if "전공" in info["category"] else "LIBERAL",
            "professor": info.get("professor", "교수"),
            "schedules": schedules,
            "keywords": [info["category"], info.get("department", "AISW")]
        })
        
    return {
        "status": "success",
        "data": data[:100]  # 상위 100개로 제한
    }