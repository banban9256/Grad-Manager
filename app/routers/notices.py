from datetime import datetime, timedelta

from fastapi import APIRouter, Header, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List

from backend.core.data.students import get_student, STUDENTS
from backend.core.data.academic_schedule import get_all_schedules
from backend.core.notifications import (
    get_upcoming_alerts,
    register_keyword_alert,
    filter_notices_by_keywords,
    get_keyword_notification_alerts,
)

router = APIRouter()

class KeywordRegisterRequest(BaseModel):
    studentId: str
    keywords: List[str]

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

@router.get("/alerts", summary="실제 공지사항 및 키워드 매칭 알림 리스트")
def get_notice_alerts(authorization: Optional[str] = Header(None)):
    student = get_student_from_token(authorization)
    student_id = student["student_id"]
    today = datetime.now().date()

    # ── 1) 학사일정 (academic_events.csv 전부,重要的 고정 일정 포함) ──
    all_events = get_all_schedules()
    academic_calendar = []
    for evt in all_events:
        start = evt.get("start_date", "")
        end = evt.get("end_date", "")
        is_new = False
        is_upcoming = False
        try:
            if start:
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
                is_new = (today - start_date).days <= 7
                is_upcoming = start_date >= today
        except Exception:
            pass
        is_mandatory = evt.get("is_mandatory", False)
        academic_calendar.append({
            "id": f"event-{evt['id']}",
            "title": evt["title"],
            "date": start,
            "endDate": end,
            "isNew": is_new,
            "isUpcoming": is_upcoming,
            "category": evt.get("category", ""),
            "isMandatory": is_mandatory,
            "content": evt.get("description", evt.get("alert_message", "")),
            "desc": evt.get("description", evt.get("alert_message", "")),
        })
    # upcoming 우선, mandatory 우선 정렬
    academic_calendar.sort(key=lambda x: (
        0 if x.get("isUpcoming") else 1,
        0 if x.get("isMandatory") else 1,
        x["date"] or "",
    ))

    # ── 2) 키워드 매칭 공지 (filter_notices_by_keywords 사용) ──
    keyword_prefs = student.get("keyword_preferences", [])
    keyword_alerts_list = student.get("keyword_alerts", [])
    all_keywords = list(dict.fromkeys(keyword_prefs + keyword_alerts_list))

    keyword_matched_notices = filter_notices_by_keywords(all_keywords) if all_keywords else []
    keyword_notices = []
    for n in keyword_matched_notices[:10]:
        keyword_notices.append({
            "id": f"notice-{n['id']}",
            "title": f"[{', '.join(n.get('matched_keywords', [])[:2])} 매칭] {n['title']}" if n.get("matched_keywords") else n["title"],
            "date": n.get("date", ""),
            "isNew": True,
            "url": n.get("url", ""),
            "content": n.get("content", ""),
            "category": n.get("category", ""),
        })

    # ── 3) 알림 트리거 (get_keyword_notification_alerts 사용) ──
    triggers_raw = get_keyword_notification_alerts(student_id, all_keywords)
    notification_triggers = []
    for t in triggers_raw[:5]:
        notice = t.get("notice", {})
        notification_triggers.append({
            "id": f"trigger-{notice.get('id', 'unknown')}",
            "title": t.get("message", ""),
            "date": notice.get("date", ""),
            "alert_type": t.get("alert_type", ""),
            "matched_keywords": t.get("matched_keywords", []),
            "isNew": True,
            "url": notice.get("url", ""),
            "content": notice.get("content", ""),
            "category": notice.get("category", ""),
        })

    # ── 4) 긴급 공지 (urgentNotice) ──
    urgent_notice = None
    if academic_calendar:
        for evt in academic_calendar:
            if evt.get("isMandatory") and evt.get("isUpcoming"):
                urgent_notice = {
                    "id": evt["id"],
                    "title": evt["title"],
                    "date": evt["date"],
                    "isNew": evt["isNew"],
                    "url": "",
                    "desc": evt.get("desc", evt.get("content", "")),
                    "content": evt.get("content", ""),
                }
                break
        if not urgent_notice:
            for evt in academic_calendar:
                if evt.get("isMandatory"):
                    urgent_notice = {
                        "id": evt["id"],
                        "title": evt["title"],
                        "date": evt["date"],
                        "isNew": evt["isNew"],
                        "url": "",
                        "desc": evt.get("desc", evt.get("content", "")),
                        "content": evt.get("content", ""),
                    }
                    break
        if not urgent_notice and academic_calendar:
            first = academic_calendar[0]
            urgent_notice = {
                "id": first["id"],
                "title": first["title"],
                "date": first["date"],
                "isNew": first["isNew"],
                "url": "",
                "desc": first.get("desc", first.get("content", "")),
                "content": first.get("content", ""),
            }
    if not urgent_notice:
        urgent_notice = {
            "id": 0,
            "title": "등록된 긴급 공지가 없습니다.",
            "date": today.strftime("%Y-%m-%d"),
            "isNew": False,
            "url": "",
            "desc": "",
        }

    return {
        "interestKeywords": [{"id": idx, "text": kw, "active": True} for idx, kw in enumerate(all_keywords)],
        "urgentNotice": urgent_notice,
        "academicCalendar": academic_calendar,
        "keywordNotices": keyword_notices,
        "notificationTriggers": notification_triggers,
    }

@router.post("/keywords", summary="알림 키워드 등록 API")
def register_keywords(req: KeywordRegisterRequest):
    student = get_student(req.studentId)
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
        
    # 메모리 내 가상 학생 데이터 업데이트
    student["keyword_preferences"] = req.keywords
    STUDENTS[req.studentId] = student
        
    result = register_keyword_alert(req.studentId, req.keywords)
    return {
        "success": True,
        "message": result["message"],
        "keywords": student.get("keyword_preferences", [])
    }