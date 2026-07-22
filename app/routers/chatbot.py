from fastapi import APIRouter

router = APIRouter()

@router.post("/chat", summary="임시 챗봇 대화 API")
def chat_message():
    return {"response": "안녕하세요! 졸업을 부탁해 AI 조교입니다. 아직 연동 준비 중이에요."}