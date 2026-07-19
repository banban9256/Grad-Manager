"""가상 학사일정 데이터 - 나중에 실제 데이터로 교체 예정"""

ACADEMIC_SCHEDULE = [
    {
        "id": 1,
        "title": "2026-1학기 수강신청",
        "start_date": "2026-02-10",
        "end_date": "2026-02-14",
        "category": "수강신청",
        "alert_days_before": 7,
        "prerequisite": None,
        "description": "희망 과목을 수강신청합니다.",
    },
    {
        "id": 2,
        "title": "수강정정 기간",
        "start_date": "2026-02-17",
        "end_date": "2026-02-21",
        "category": "수강신청",
        "alert_days_before": 3,
        "prerequisite": "수강신청 완료",
        "description": "수강신청한 과목을 정정합니다.",
    },
    {
        "id": 3,
        "title": "중간고사",
        "start_date": "2026-04-06",
        "end_date": "2026-04-10",
        "category": "시험",
        "alert_days_before": 14,
        "prerequisite": None,
        "description": "중간고사 기간입니다.",
    },
    {
        "id": 4,
        "title": "기말 강의 평가",
        "start_date": "2026-06-01",
        "end_date": "2026-06-12",
        "category": "평가",
        "alert_days_before": 3,
        "prerequisite": None,
        "description": "기말 강의 평가를 진행합니다. 미평가 시 성적 조회 제한.",
    },
    {
        "id": 5,
        "title": "기말고사",
        "start_date": "2026-06-15",
        "end_date": "2026-06-19",
        "category": "시험",
        "alert_days_before": 14,
        "prerequisite": None,
        "description": "기말고사 기간입니다.",
    },
    {
        "id": 6,
        "title": "성적 조회 및 이의신청",
        "start_date": "2026-06-25",
        "end_date": "2026-06-30",
        "category": "성적",
        "alert_days_before": 5,
        "prerequisite": "기말 강의 평가 완료",
        "description": "성적 조회 및 이의신청 기간입니다.",
    },
    {
        "id": 7,
        "title": "2026-2학기 수강신청",
        "start_date": "2026-08-10",
        "end_date": "2026-08-14",
        "category": "수강신청",
        "alert_days_before": 7,
        "prerequisite": None,
        "description": "2026-2학기 수강신청 기간입니다.",
    },
    {
        "id": 8,
        "title": "졸업신청",
        "start_date": "2026-03-01",
        "end_date": "2026-03-31",
        "category": "졸업",
        "alert_days_before": 14,
        "prerequisite": "졸업요건 충족 확인",
        "description": "졸업 신청 기간입니다. 졸업요건 미충족 시 신청 불가.",
    },
]


def get_all_schedules() -> list[dict]:
    """전체 학사일정 반환"""
    return ACADEMIC_SCHEDULE


def get_upcoming_schedules(days_ahead: int = 30) -> list[dict]:
    """향후 N일 이내 학사일정 반환"""
    from datetime import datetime, timedelta

    today = datetime.now().date()
    deadline = today + timedelta(days=days_ahead)

    upcoming = []
    for schedule in ACADEMIC_SCHEDULE:
        schedule_start = datetime.strptime(schedule["start_date"], "%Y-%m-%d").date()
        if today <= schedule_start <= deadline:
            upcoming.append(schedule)
    return upcoming


def get_schedule_by_category(category: str) -> list[dict]:
    """카테고리별 학사일정 조회"""
    return [s for s in ACADEMIC_SCHEDULE if s["category"] == category]
