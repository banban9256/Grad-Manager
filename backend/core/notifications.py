"""알림 모듈 - 키워드 매칭 + 학사일정 트리거"""

import re
from datetime import datetime, timedelta

from .data.notices import NOTICES
from .data.academic_schedule import ACADEMIC_SCHEDULE, get_upcoming_schedules


# ==============================
# 공지사항 키워드 매칭
# ==============================

def search_notices(query: str) -> list[dict]:
    """
    사용자 입력에서 키워드를 추출하여 공지사항을 검색합니다.

    검색 방식:
    - 제목, 본문, 키워드 필드에서 부분 일치 검색
    - OR 로직: 하나라도 매칭되면 결과에 포함
    -levance 순 정렬 (매칭된 키워드 수 기준)
    """
    # 입력에서 키워드 추출 (공백, 특수문자 기준 분리)
    keywords = re.findall(r'[\w가-힣]+', query)

    if not keywords:
        return []

    results = []
    for notice in NOTICES:
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

    # 매칭 수 기준 내림차순 정렬
    results.sort(key=lambda x: x["match_count"], reverse=True)
    return results


def filter_notices_by_keywords(keywords: list[str]) -> list[dict]:
    """
    설정된 키워드 목록으로 공지사항을 필터링합니다.
    알림 시스템에서 사용.
    """
    results = []
    for notice in NOTICES:
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


def register_keyword_alert(student_id: str, keywords: list[str]) -> dict:
    """
    사용자의 알림 키워드를 등록합니다.
    (실제 서비스에서는 DB에 저장, 현재는 세션 관리)

    Returns:
        등록 결과 및 기존 매칭 공지 목록
    """
    existing_matches = filter_notices_by_keywords(keywords)

    return {
        "student_id": student_id,
        "registered_keywords": keywords,
        "existing_matches": existing_matches,
        "message": f"{len(keywords)}개 키워드가 등록되었습니다. {len(existing_matches)}건의 기존 공지가 매칭됩니다.",
    }


# ==============================
# 학사일정 알림 트리거
# ==============================

def get_upcoming_alerts(days_ahead: int = 30) -> list[dict]:
    """향후 N일 이내 학사일정을 알림 형태로 반환"""
    upcoming = get_upcoming_schedules(days_ahead)
    today = datetime.now().date()

    alerts = []
    for schedule in upcoming:
        start_date = datetime.strptime(schedule["start_date"], "%Y-%m-%d").date()
        days_until = (start_date - today).days

        # 긴급도判定
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

        # 선행 일정 체크
        if schedule.get("prerequisite"):
            alert["prerequisite_warning"] = (
                f"⚠️ '{schedule['prerequisite']}'를 먼저 완료해야 합니다."
            )

        alerts.append(alert)

    # 긴급도 순 정렬
    urgency_order = {"긴급": 0, "주의": 1, "알림": 2, "예정": 3}
    alerts.sort(key=lambda x: (urgency_order.get(x["urgency"], 99), x["days_until"]))

    return alerts


def _build_alert_message(schedule: dict, days_until: int) -> str:
    """일정별 알림 메시지 생성"""
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
    """
    특정 학생에게 관련된 마감 트리거를 확인합니다.

    예시:
    - 기말 강의 평가 미완료 시 → 성적 조회 불가 경고
    - 졸업신청 기간 → 졸업 요건 충족 여부 확인 안내
    """
    triggers = []
    today = datetime.now().date()

    for schedule in ACADEMIC_SCHEDULE:
        start_date = datetime.strptime(schedule["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(schedule["end_date"], "%Y-%m-%d").date()

        if start_date <= today <= end_date:
            # 진행 중인 일정
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
            # 임박한 일정
            triggers.append({
                "schedule": schedule,
                "status": "임박",
                "message": _build_alert_message(schedule, (start_date - today).days),
            })

    return triggers


def format_notification(notice: dict) -> str:
    """공지사항을 알림 문자열로 포맷"""
    keywords_str = ", ".join(notice.get("matched_keywords", []))
    return (
        f"📢 [{notice['source']}] {notice['title']}\n"
        f"   날짜: {notice['date']}\n"
        f"   키워드 매칭: {keywords_str}\n"
        f"   {notice['content'][:150]}..."
    )
