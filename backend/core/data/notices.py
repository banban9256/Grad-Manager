"""가상 공지사항 데이터 - 나중에 실제 크롤링 데이터로 교체 예정"""

NOTICES = [
    {
        "id": 1,
        "title": "2026-1학기 수강신청 일정 안내",
        "content": "2026-1학기 수강신청은 2월 10일부터 2월 14일까지 진행됩니다. 반드시 학과 상담을 완료 후 신청하시기 바랍니다.",
        "source": "학사지원팀",
        "date": "2026-01-20",
        "keywords": ["수강신청", "일정"],
        "url": "https://example.com/notice/1",
    },
    {
        "id": 2,
        "title": "AI 분야 장학금 모집 공고",
        "content": "인공지능 및 소프트웨어 분야 우수 장학생을 모집합니다. 지원 자격: AISW 전공자, GPA 3.5 이상. 지원 기간: ~2월 28일까지.",
        "source": "장학팀",
        "date": "2026-01-25",
        "keywords": ["장학금", "AI", "장학"],
        "url": "https://example.com/notice/2",
    },
    {
        "id": 3,
        "title": "2026년 소프트웨어 공모전 안내",
        "content": "대全校 소프트웨어 공모전 참가팀을 모집합니다. 팀 구성: 3~5명, 주제: AI/ML 관련 서비스. 접수 마감: 3월 15일.",
        "source": "학과사무실",
        "date": "2026-02-01",
        "keywords": ["공모전", "소프트웨어", "SW"],
        "url": "https://example.com/notice/3",
    },
    {
        "id": 4,
        "title": "특화 전공 이수절차 변경 안내",
        "content": "데이터사이언스 특화 전공 이수 절차가 변경되었습니다. 2025학번부터 적용되며, 세부 사항은 학과 홈페이지를 참고하세요.",
        "source": "학과사무실",
        "date": "2026-02-05",
        "keywords": ["특화전공", "특화", "융합", "전공"],
        "url": "https://example.com/notice/4",
    },
    {
        "id": 5,
        "title": "기말 강의 평가 안내",
        "content": "2025-2학기 기말 강의 평가가 시작됩니다. 평가 기간: 12월 1일 ~ 12월 15일. 미평가 시 성적 조회가 제한됩니다.",
        "source": "학사지원팀",
        "date": "2025-12-01",
        "keywords": ["기말", "강의평가", "성적"],
        "url": "https://example.com/notice/5",
    },
    {
        "id": 6,
        "title": "인턴십 프로그램 모집 (삼성, 네이버)",
        "content": "삼성 SDS, 네이버 AI 인턴십 프로그램 참가자를 모집합니다. 모집 인원: 각 5명. 지원 자격: 3학년 이상.",
        "source": "취업지원팀",
        "date": "2026-02-10",
        "keywords": ["인턴", "취업", "삼성", "네이버"],
        "url": "https://example.com/notice/6",
    },
    {
        "id": 7,
        "title": "융합 전공 설명회 안내",
        "content": "AI+데이터 융합 전공 설명회를 개최합니다. 일시: 2월 20일 14:00, 장소: 공학관 101호.",
        "source": "학과사무실",
        "date": "2026-02-12",
        "keywords": ["융합", "전공", "설명회"],
        "url": "https://example.com/notice/7",
    },
    {
        "id": 8,
        "title": "졸업 요건 변경 공지",
        "content": "2027년부터 졸업에 필요한 최소 학점이 130점에서 136점으로 변경됩니다.",
        "source": "학사지원팀",
        "date": "2026-01-15",
        "keywords": ["졸업", "요건", "학점"],
        "url": "https://example.com/notice/8",
    },
]


def get_all_notices() -> list[dict]:
    """전체 공지사항 목록 반환"""
    return NOTICES


def get_notice_by_id(notice_id: int) -> dict | None:
    """공지 ID로 조회"""
    for notice in NOTICES:
        if notice["id"] == notice_id:
            return notice
    return None
