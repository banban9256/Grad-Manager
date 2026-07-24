import csv
from pathlib import Path
from functools import lru_cache

_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "output"


def _read_csv(filename: str) -> list[dict]:
    """CSV 파일을 읽어 dict 리스트로 반환 (BOM 처리 포함)"""
    filepath = _OUTPUT_DIR / filename
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ==============================
# 과목 데이터
# ==============================

@lru_cache(maxsize=1)
def load_courses() -> dict[str, dict]:
    """
    courses.csv + course_offerings.csv + course_schedules.csv를 조인하여
    course_code를 키로 하는 과목 dict를 반환

    각 과목은 여러 분반(offering)과 시간표(schedule)를 포함
    time_slots는 2026-1학기 분반 기준으로 구성
    """
    courses_raw = _read_csv("courses.csv")
    offerings_raw = _read_csv("course_offerings.csv")
    schedules_raw = _read_csv("course_schedules.csv")

    # curriculum_courses에서 과목 타입 정보 로드
    curriculum_raw = _read_csv("curriculum_courses.csv")
    course_type_map = _build_course_type_map(curriculum_raw)

    # course_id → offering 매핑
    offering_map: dict[int, list[dict]] = {}
    for o in offerings_raw:
        cid = int(o["course_id"])
        offering_map.setdefault(cid, []).append(o)

    # offering_id → schedule 매핑
    schedule_map: dict[int, list[dict]] = {}
    for s in schedules_raw:
        oid = int(s["offering_id"])
        schedule_map.setdefault(oid, []).append(s)

    # 과목 dict 구성
    courses: dict[str, dict] = {}
    for c in courses_raw:
        cid = int(c["course_id"])
        code = c["course_code"].lstrip("*")
        credit = float(c["credit"])

        # 해당 과목의 분반들
        offs = offering_map.get(cid, [])

        # 2026-1학기 분반 우선, 없으면 첫 번째 분반 사용
        primary_offering = None
        for o in offs:
            if o["semester"] == "1학기" and o["academic_year"] == "2026":
                primary_offering = o
                break
        if not primary_offering and offs:
            primary_offering = offs[0]

        # 분반별 시간표 구성
        offering_details = []
        for o in offs:
            oid = int(o["offering_id"])
            scheds = schedule_map.get(oid, [])
            time_slots = [
                (s["day_of_week"], s["start_time"], s["end_time"])
                for s in scheds
            ]
            offering_details.append({
                "offering_id": oid,
                "section": o["section"],
                "professor": o["professor_name"],
                "academic_year": o["academic_year"],
                "semester": o["semester"],
                "time_slots": time_slots,
                "classrooms": [s["classroom"] for s in scheds],
            })

        # 기본 time_slots: 첫 번째 분반의 시간표
        default_time_slots = []
        default_professor = ""
        default_room = "미정"
        if primary_offering:
            oid = int(primary_offering["offering_id"])
            scheds = schedule_map.get(oid, [])
            default_time_slots = [
                (s["day_of_week"], s["start_time"], s["end_time"])
                for s in scheds
            ]
            default_professor = primary_offering["professor_name"]
            default_room = scheds[0]["classroom"] if scheds else "미정"

        # 과목 타입 결정
        course_type = course_type_map.get(cid, _infer_type_from_code(code))

        courses[code] = {
            "code": code,
            "name": c["course_name"],
            "type": course_type,
            "credits": int(credit) if credit == int(credit) else credit,
            "category": _category_label(course_type),
            "department": _department_from_code(code),
            "professor": default_professor,
            "room": default_room,
            "time_slots": default_time_slots,
            "capacity": 0,
            "enrolled": 0,
            "description": c["course_description"],
            "offerings": offering_details,
        }

    try:
        import sqlite3
        db_path = Path(__file__).resolve().parent.parent.parent.parent / "gradmanager.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT course_id, course_code, course_name, credit FROM courses")
            db_courses = cursor.fetchall()
            for cid, code, name, credit in db_courses:
                code_clean = code.lstrip("*")
                if code_clean not in courses:
                    inferred_cat = _infer_type_from_code(code_clean)
                    courses[code_clean] = {
                        "code": code_clean,
                        "name": name,
                        "type": inferred_cat,
                        "credits": int(credit) if credit is not None and credit == int(credit) else (float(credit) if credit is not None else 3.0),
                        "category": _category_label(inferred_cat),
                        "department": _department_from_code(code_clean),
                        "professor": "미정",
                        "room": "미정",
                        "time_slots": [],
                        "capacity": 0,
                        "enrolled": 0,
                        "description": "",
                        "offerings": [],
                    }
            conn.close()
    except Exception as e:
        print(f"SQLite courses merge error: {e}")

    return courses


def _normalize_completion_type(ctype: str) -> str:
    """축약형이나 다양한 이수구분 명칭을 6가지 표준 명칭으로 통일"""
    if not ctype:
        return "일반선택"
    
    ctype = ctype.strip()
    
    mapping = {
        # 전공필수
        "전공필수": "전공필수",
        "전필": "전공필수",
        "복수필수": "전공필수",
        "복필": "전공필수",
        "부전공필수": "전공필수",
        "부필": "전공필수",
        
        # 전공선택
        "전공선택": "전공선택",
        "전선": "전공선택",
        "복수선택": "전공선택",
        "복선": "전공선택",
        "부전공선택": "전공선택",
        "부선": "전공선택",
        "융합선택": "전공선택",
        "융선": "전공선택",
        "특성화선택": "전공선택",
        "특선": "전공선택",
        "융합": "전공선택",
        
        # 교양필수
        "교양필수": "교양필수",
        "교필": "교양필수",
        
        # 교양선택
        "교양선택": "교양선택",
        "교선": "교양선택",
        "교양": "교양선택",
        
        # 계열공통
        "계열공통": "계열공통",
        "계공": "계열공통",
        "공통선택": "계열공통",
        "공선": "계열공통",
        
        # 일반선택
        "일반선택": "일반선택",
        "일선": "일반선택",
        "일반": "일반선택"
    }
    
    return mapping.get(ctype, ctype)


def _build_course_type_map(curriculum_rows: list[dict]) -> dict[int, str]:
    """curriculum_courses.csv에서 course_id → type 매핑 생성"""
    type_map: dict[int, str] = {}
    for row in curriculum_rows:
        cid = int(row["course_id"])
        completion_type = row["completion_type"]
        is_required = row["is_required"] == "True"

        normalized_type = _normalize_completion_type(completion_type)

        if normalized_type and cid not in type_map:
            type_map[cid] = normalized_type
        if is_required:
            type_map[cid] = "전공필수"

    return type_map


def _category_label(course_type: str) -> str:
    """과목 타입을 한국어 카테고리로 변환"""
    return _normalize_completion_type(course_type)


def _infer_type_from_code(code: str) -> str:
    """과목 코드 접두사로 타입 추론"""
    if "전공필수" in code:
        return "전공필수"
    if "전공선택" in code:
        return "전공선택"
    if "교양필수" in code:
        return "교양필수"
    if "교양선택" in code:
        return "교양선택"
    if "계열공통" in code:
        return "계열공통"
    if "일반선택" in code:
        return "일반선택"

    core_liberal_requirements = {"KY100", "KY101", "KY201", "KY217", "KY304", "KY313"}
    if code in core_liberal_requirements:
        return "교양필수"

    prefix = "".join(ch for ch in code if ch.isalpha())
    if prefix in ("KY", "KYC", "KYA", "KYD"):
        return "교양선택"
    elif prefix == "AC":
        return "전공필수"
    elif prefix in ("FLOW",):
        return "계열공통"
    else:
        return "전공선택"


def _category_label(course_type: str) -> str:
    """과목 타입을 한국어 카테고리로 변환"""
    mapping = {
        "전공필수": "전공필수",
        "전공선택": "전공선택",
        "교양필수": "교양필수",
        "교양선택": "교양선택",
        "교양": "교양선택",
        "계열공통": "계열공통",
    }
    return mapping.get(course_type, course_type)


def _department_from_code(code: str) -> str:
    """과목 코드로 학과 추론"""
    prefix = "".join(ch for ch in code if ch.isalpha())
    if prefix in ("KY", "KYC", "KYA", "KYD"):
        return "교양"
    elif prefix == "AC":
        return "AISW"
    elif prefix == "FLOW":
        return "계열공통"
    else:
        return "AISW"


# ==============================
# 공지사항 데이터
# ==============================

@lru_cache(maxsize=1)
def load_notices() -> list[dict]:
    """
    notices.csv를 로드하여 기존 모듈이 사용하는 형식으로 변환합니다.

    반환 형식:
    - id, title, content, source, date, keywords, url
    """
    raw = _read_csv("notices.csv")
    notices = []
    for n in raw:
        # 제목에서 키워드 추출
        title = n["title"]
        keywords = _extract_keywords_from_title(title)

        notices.append({
            "id": int(n["notice_id"]),
            "title": title,
            "content": n.get("content", "") or title,  # content가 비어있으면 title 사용
            "source": n["source_board"],
            "date": n["posted_date"],
            "keywords": keywords,
            "url": n.get("notice_url", ""),
            "category": n.get("category", ""),
        })
    return notices


def _extract_keywords_from_title(title: str) -> list[str]:
    """제목에서 의미있는 키워드 추출"""
    keywords = []
    important_terms = [
        "장학금", "공모전", "인턴", "취업", "수강신청", "졸업",
        "전공", "특화", "융합", "SW", "AI", "경진대회", "산학협력",
        "강의평가", "성적", "휴학", "복학", "등록금", "멘토링",
        "프로그래밍", "동아리", "특강", "캠프", "교육과정",
    ]
    for term in important_terms:
        if term.lower() in title.lower():
            keywords.append(term)
    if not keywords:
        # 제목의 주요 명사 추출 (간단한 휴리스틱)
        words = title.replace("[", "").replace("]", "").split()
        for w in words:
            if len(w) >= 2 and not w.startswith("("):
                keywords.append(w)
                if len(keywords) >= 3:
                    break
    return keywords


# ==============================
# 학사일정 데이터
# ==============================

@lru_cache(maxsize=1)
def load_academic_schedule() -> list[dict]:
    """
    academic_events.csv를 로드하여 기존 모듈이 사용하는 형식으로 변환합니다.

    반환 형식:
    - id, title, start_date, end_date, category, alert_days_before, prerequisite, description
    """
    raw = _read_csv("academic_events.csv")
    schedule = []
    for e in raw:
        event_type = e["event_type"]

        # 이벤트 타입 → 카테고리 매핑
        category = _map_event_type_to_category(event_type)

        # 알림 일수 결정
        alert_days = _default_alert_days(event_type)

        # 선행 일정
        prerequisite = _determine_prerequisite(event_type)

        schedule.append({
            "id": int(e["event_id"]),
            "title": e["event_name"],
            "start_date": e["start_date"],
            "end_date": e["end_date"],
            "category": category,
            "alert_days_before": alert_days,
            "prerequisite": prerequisite,
            "description": e.get("description", ""),
        })
    return schedule


def _map_event_type_to_category(event_type: str) -> str:
    """CSV 이벤트 타입을 기존 카테고리로 매핑"""
    mapping = {
        "COURSE_REGISTRATION": "수강신청",
        "TUITION_PAYMENT": "등록",
        "FINAL_COURSE_EVALUATION": "평가",
        "EXAM": "시험",
        "GRADE_INQUIRY": "성적",
        "PRE_REGISTRATION": "수강신청",
        "ADMINISTRATIVE": "행정",
    }
    return mapping.get(event_type, "기타")


def _default_alert_days(event_type: str) -> int:
    """이벤트 타입별 기본 알림 일수"""
    mapping = {
        "COURSE_REGISTRATION": 7,
        "TUITION_PAYMENT": 3,
        "FINAL_COURSE_EVALUATION": 3,
        "EXAM": 14,
        "GRADE_INQUIRY": 5,
        "PRE_REGISTRATION": 7,
        "ADMINISTRATIVE": 7,
    }
    return mapping.get(event_type, 7)


def _determine_prerequisite(event_type: str) -> str | None:
    """이벤트 타입별 선행 조건"""
    mapping = {
        "GRADE_INQUIRY": "기말 강의 평가 완료",
        "ADMINISTRATIVE": None,
    }
    return mapping.get(event_type)
