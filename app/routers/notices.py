from fastapi import APIRouter

router = APIRouter()

@router.get("/alerts", summary="임시 키워드 공지 알림 리스트")
def get_notice_alerts():
    return {"alerts": [{"id": 1, "title": "[장학] 2026년 2학기 특화전공 장학생 선발 안내"}]}