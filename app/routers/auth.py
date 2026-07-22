from fastapi import APIRouter

router = APIRouter()

@router.post("/login", summary="임시 로그인 API")
def login():
    return {"status": "success", "message": "로그인 성공 (임시)"}