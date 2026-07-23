from fastapi import APIRouter, Header, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List

from backend.core.data.students import get_student, STUDENTS
from backend.core.notifications import get_upcoming_alerts, register_keyword_alert, search_notices

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
    
    # 해당 학생의 키워드 취향에 알맞는 공지사항 검색
    keywords = student.get("keyword_preferences", [])
    alerts = []
    
    # 키워드별 검색
    for kw in keywords[:3]:
        results = search_notices(kw)
        for r in results[:2]:
            alerts.append({
                "id": f"notice-{kw}-{r['id']}",
                "title": f"[{kw} 매칭] {r['title']}",
                "date": r["date"],
                "isNew": True
            })
            
    # 매칭 결과가 없을 경우 백업
    if not alerts:
        alerts = [
            {"id": 101, "title": "[인턴 매칭] 2026 동계 SW인턴십 모집 안내", "date": "2026-07-22", "isNew": True},
            {"id": 102, "title": "[장학 매칭] AI특화 학업 우수 장학금 신청 연장", "date": "2026-07-21", "isNew": False}
        ]
        
    return {
        "interestKeywords": [{"id": idx, "text": kw, "active": True} for idx, kw in enumerate(keywords)],
        "urgentNotice": {
            "id": 200,
            "title": "[긴급] 졸업자격설정 제출 마감 임박 안내 (~07/31)",
            "date": "2026-07-22",
            "isNew": True
        },
        "academicCalendar": alerts
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