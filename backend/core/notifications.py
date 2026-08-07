"""알림 모듈 - 키워드 매칭 + 학사일정 트리거 + 키워드 알림 지속성 + 마감 리마인더"""

import re
from datetime import datetime, timedelta

from .data.notices import get_all_notices
from .data.academic_schedule import get_all_schedules, get_upcoming_schedules
from .data.csv_loader import load_notices


# ==============================
# 공지사항 키워드 매칭
# ==============================

def search_notices(query: str) -> list[dict]:
    notices = get_all_notices()
    keywords = re.findall(r'[\w가-힣]+', query)

    if not keywords:
        return []

    results = []
    for notice in notices:
        searchable = (
            notice["title"].lower() + " " +
            notice["content"].lower() + " " +
            " ".join(notice["keywords"]).lower()
        )

        match_count = 0
        matched_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in searchable:
                match_count += 1
                matched_keywords.append(kw)

        if match_count > 0:
            results.append({
                **notice,
                "match_count": match_count,
                "matched_keywords": matched_keywords,
            })

    results.sort(key=lambda x: x["match_count"], reverse=True)
    return results


def filter_notices_by_keywords(keywords: list[str]) -> list[dict]:
    notices = get_all_notices()
    today = datetime.now().date()
    results = []

    for notice in notices:
        notice_date_str = notice.get("date", "")
        if notice_date_str:
            try:
                notice_date = datetime.strptime(notice_date_str, "%Y-%m-%d").date()
                if (today - notice_date).days > 30:
                    continue
            except Exception:
                pass

        notice_text = (
            notice["title"] + " " +
            notice["content"] + " " +
            " ".join(notice["keywords"])
        ).lower()

        matched = [kw for kw in keywords if kw.lower() in notice_text]
        if matched:
            results.append({
                **notice,
                "matched_keywords": matched,
            })
    return results


# ==============================
# 키워드 알림 지속성 (학생별)
# ==============================

def register_keyword_alert(student_id: str, keywords: list[str]) -> dict:
    """
    사용자의 알림 키워드를 등록합니다.
    학생 프로필에 keyword_alerts 필드에 저장합니다.
    """
    from .data.students import get_student, save_student

    student = get_student(student_id)
    if not student:
        return {
            "student_id": student_id,
            "registered_keywords": keywords,
            "existing_matches": [],
            "message": "학생 정보를 찾을 수 없습니다.",
        }

    existing_alerts = student.get("keyword_alerts", [])
    new_keywords = [kw for kw in keywords if kw not in existing_alerts]
    all_keywords = existing_alerts + new_keywords

    student["keyword_alerts"] = all_keywords
    save_student(student_id, student)

    existing_matches = filter_notices_by_keywords(all_keywords)

    return {
        "student_id": student_id,
        "registered_keywords": all_keywords,
        "new_keywords": new_keywords,
        "existing_matches": existing_matches,
        "message": f"{len(new_keywords)}개 새 키워드 등록 완료 (총 {len(all_keywords)}개). {len(existing_matches)}건의 기존 공지가 매칭됩니다.",
    }


def get_keyword_alerts(student_id: str) -> list[str]:
    """학생의 등록된 키워드 알림 목록을 반환합니다."""
    from .data.students import get_student
    student = get_student(student_id)
    if not student:
        return []
    return student.get("keyword_alerts", [])


def remove_keyword_alert(student_id: str, keywords: list[str]) -> dict:
    """학생의 키워드 알림을 제거합니다."""
    from .data.students import get_student, save_student

    student = get_student(student_id)
    if not student:
        return {"message": "학생 정보를 찾을 수 없습니다."}

    existing = student.get("keyword_alerts", [])
    remaining = [kw for kw in existing if kw not in keywords]
    student["keyword_alerts"] = remaining
    save_student(student_id, student)

    return {
        "removed": keywords,
        "remaining": remaining,
        "message": f"{len(keywords)}개 키워드 제거 완료. 남은 키워드: {len(remaining)}개",
    }


def get_keyword_notification_alerts(student_id: str, keywords: list[str]) -> list[dict]:
    """
    프론트엔드 알림 트리거용: 키워드 매칭 공지 중 마감 임박/진행중 건 반환.

    1주전, 1일전, 당일 기준 알림 생성.
    """
    if not keywords:
        return []

    matched_notices = filter_notices_by_keywords(keywords)
    if not matched_notices:
        return []

    today = datetime.now().date()
    alerts = []

    for notice in matched_notices:
        notice_date_str = notice.get("date", "")
        if not notice_date_str:
            continue
        try:
            notice_date = datetime.strptime(notice_date_str, "%Y-%m-%d").date()
        except Exception:
            continue

        days_since = (today - notice_date).days

        if days_since < 0:
            days_until = abs(days_since)
            if days_until <= 1:
                alert_type = "긴급"
                message = f"📢 '{notice['title']}' 마감이 {days_until}일 남았습니다!"
            elif days_until <= 7:
                alert_type = "주의"
                message = f"📋 '{notice['title']}' 마감이 {days_until}일 남았습니다."
            else:
                alert_type = "알림"
                message = f"📅 '{notice['title']}' ({notice_date_str})"
        elif days_since == 0:
            alert_type = "긴급"
            message = f"📢 '{notice['title']}' 오늘 마감!"
        elif days_since <= 7:
            alert_type = "주의"
            message = f"⏰ '{notice['title']}' {days_since}일 전 게시"
        else:
            continue

        alerts.append({
            "notice": notice,
            "matched_keywords": notice.get("matched_keywords", []),
            "alert_type": alert_type,
            "message": message,
        })

    urgency_order = {"긴급": 0, "주의": 1, "알림": 2}
    alerts.sort(key=lambda x: (urgency_order.get(x["alert_type"], 99),))
    return alerts


# ==============================
# 키워드 알림 데드라인 리마인더
# ==============================

def check_keyword_alert_deadlines(student_id: str) -> list[dict]:
    """
    학생의 키워드 알림에 매칭되는 공지사항 중 마감이 임박한 것들을 리마인더로 반환합니다.

    리마인더 기준:
    - 당일 마감: 긴급
    - 1일 전: 주의
    - 7일 전: 알림

    반환 형식:
    [
        {
            "notice": dict,
            "matched_keywords": list,
            "days_until_deadline": int,
            "urgency": str,
            "message": str,
        },
        ...
    ]
    """
    keywords = get_keyword_alerts(student_id)
    if not keywords:
        return []

    keyword_prefs = []
    from .data.students import get_student
    student = get_student(student_id)
    if student:
        keyword_prefs = student.get("keyword_preferences", [])

    all_keywords = list(set(keywords + keyword_prefs))

    matched_notices = filter_notices_by_keywords(all_keywords)
    if not matched_notices:
        return []

    today = datetime.now().date()
    reminders = []

    for notice in matched_notices:
        notice_date_str = notice.get("date", "")
        if not notice_date_str:
            continue

        try:
            notice_date = datetime.strptime(notice_date_str, "%Y-%m-%d").date()
        except Exception:
            continue

        days_since = (today - notice_date).days

        if days_since < 0:
            days_until = abs(days_since)
            if days_until <= 1:
                urgency = "긴급"
                message = f"📢 '{notice['title']}' 마감이 {days_until}일 후입니다!"
            elif days_until <= 7:
                urgency = "주의"
                message = f"📋 '{notice['title']}' 마감이 {days_until}일 후입니다."
            else:
                urgency = "알림"
                message = f"📅 '{notice['title']}' ({notice_date_str} 마감)"
        elif days_since == 0:
            urgency = "긴급"
            message = f"📢 '{notice['title']}' 오늘 마감입니다!"
        elif days_since <= 7:
            urgency = "주의"
            message = f"⏰ '{notice['title']}' {days_since}일 전 게시 (최신 공지 확인 필요)"
        else:
            continue

        reminders.append({
            "notice": notice,
            "matched_keywords": notice.get("matched_keywords", []),
            "days_until_deadline": days_since,
            "urgency": urgency,
            "message": message,
        })

    urgency_order = {"긴급": 0, "주의": 1, "알림": 2}
    reminders.sort(key=lambda x: (urgency_order.get(x["urgency"], 99), x["days_until_deadline"]))

    return reminders


# ==============================
# 학사일정 알림 트리거
# ==============================

def get_upcoming_alerts(days_ahead: int = 30) -> list[dict]:
    upcoming = get_upcoming_schedules(days_ahead)
    today = datetime.now().date()

    alerts = []
    for schedule in upcoming:
        start_date = datetime.strptime(schedule["start_date"], "%Y-%m-%d").date()
        days_until = (start_date - today).days

        if days_until <= 3:
            urgency = "긴급"
        elif days_until <= 7:
            urgency = "주의"
        elif days_until <= 14:
            urgency = "알림"
        else:
            urgency = "예정"

        alert = {
            **schedule,
            "days_until": days_until,
            "urgency": urgency,
            "alert_message": _build_alert_message(schedule, days_until),
        }

        if schedule.get("prerequisite"):
            alert["prerequisite_warning"] = (
                f"⚠️ '{schedule['prerequisite']}'를 먼저 완료해야 합니다."
            )

        alerts.append(alert)

    urgency_order = {"긴급": 0, "주의": 1, "알림": 2, "예정": 3}
    alerts.sort(key=lambda x: (urgency_order.get(x["urgency"], 99), x["days_until"]))

    return alerts


def _build_alert_message(schedule: dict, days_until: int) -> str:
    title = schedule["title"]
    if days_until == 0:
        return f"📢 오늘부터 '{title}'이(가) 시작됩니다!"
    elif days_until == 1:
        return f"📢 내일부터 '{title}'이(가) 시작됩니다."
    elif days_until <= 3:
        return f"⏰ {days_until}일 후 '{title}'이(가) 시작됩니다."
    elif days_until <= 7:
        return f"📋 {days_until}일 후 '{title}'이(가) 예정되어 있습니다."
    else:
        return f"📅 {days_until}일 후 '{title}'이(가) 예정되어 있습니다."


def check_deadline_triggers(student: dict) -> list[dict]:
    triggers = []
    today = datetime.now().date()
    all_schedules = get_all_schedules()

    for schedule in all_schedules:
        start_date = datetime.strptime(schedule["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(schedule["end_date"], "%Y-%m-%d").date()

        if start_date <= today <= end_date:
            trigger = {
                "schedule": schedule,
                "status": "진행중",
                "message": f"현재 '{schedule['title']}'이(가) 진행 중입니다.",
            }
            if schedule.get("prerequisite"):
                trigger["prerequisite_check"] = (
                    f"'{schedule['prerequisite']}' 확인이 필요합니다."
                )
            triggers.append(trigger)

        elif today < start_date and (start_date - today).days <= schedule.get("alert_days_before", 7):
            triggers.append({
                "schedule": schedule,
                "status": "임박",
                "message": _build_alert_message(schedule, (start_date - today).days),
            })

    return triggers


def format_notification(notice: dict) -> str:
    keywords_str = ", ".join(notice.get("matched_keywords", []))
    return (
        f"📢 [{notice['source']}] {notice['title']}\n"
        f"   날짜: {notice['date']}\n"
        f"   키워드 매칭: {keywords_str}\n"
        f"   {notice['content'][:150]}..."
    )
