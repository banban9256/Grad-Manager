"""학사일정 데이터 모듈 - CSV 기반 실제 데이터 로딩"""

from datetime import datetime, timedelta
from .csv_loader import load_academic_schedule

# CSV에서 로드된 학사일정 데이터 (지연 로딩)
ACADEMIC_SCHEDULE = None


def _ensure_loaded():
    """필요시 CSV에서 학사일정 데이터 로드"""
    global ACADEMIC_SCHEDULE
    if ACADEMIC_SCHEDULE is None:
        ACADEMIC_SCHEDULE = load_academic_schedule()


def get_all_schedules() -> list[dict]:
    """전체 학사일정 반환"""
    _ensure_loaded()
    return ACADEMIC_SCHEDULE


def get_upcoming_schedules(days_ahead: int = 30) -> list[dict]:
    """향후 N일 이내 학사일정 반환"""
    _ensure_loaded()
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
    _ensure_loaded()
    return [s for s in ACADEMIC_SCHEDULE if s["category"] == category]
