from fastapi import APIRouter

router = APIRouter()

@router.get("/summary", summary="임시 졸업학점 진단 결과")
def get_graduation_summary():
    return {"total_credits_required": 130, "current_credits": 85, "status": "warning"}