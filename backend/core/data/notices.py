"""공지사항 데이터 모듈 - CSV 기반 실제 데이터 로딩"""

from .csv_loader import load_notices

# CSV에서 로드된 공지사항 데이터 (지연 로딩)
NOTICES = None


def _ensure_loaded():
    """필요시 CSV에서 공지사항 데이터 로드"""
    global NOTICES
    if NOTICES is None:
        NOTICES = load_notices()


def get_all_notices() -> list[dict]:
    """전체 공지사항 목록 반환"""
    _ensure_loaded()
    return NOTICES


def get_notice_by_id(notice_id: int) -> dict | None:
    """공지 ID로 조회"""
    _ensure_loaded()
    for notice in NOTICES:
        if notice["id"] == notice_id:
            return notice
    return None
