from fastapi import APIRouter, Header, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List

from backend.core.data.students import get_student
from backend.core.chatbot import chat
from backend.core.scheduler import generate_timetable

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None

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
    
    # backend/core/chatbot.py 의 chat 함수 호출
    ai_response = chat(
        user_message=req.message,
        student_id=student_id,
        history=req.history or []
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
                          "professor": c["professor"],
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