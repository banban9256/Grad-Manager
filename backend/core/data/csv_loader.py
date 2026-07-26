import csv
import re
from pathlib import Path
from functools import lru_cache

_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "output"


# ==============================
# 한자 → 한글 변환 유틸리티
# ==============================

_HANJA_MAP = {
    "寫": "사", "作": "작", "深化": "심화", "新": "신", "中": "중", "國": "국",
    "語": "어", "文": "문", "化": "화", "學": "학", "年": "년", "月": "월",
    "日": "일", "時": "시", "分": "분", "期": "기", "試": "시", "驗": "험",
    "講": "강", "義": "의", "論": "논", "述": "술", "集": "집", "會": "회",
    "院": "원", "館": "관", "室": "실", "實": "실", "習": "습", "設": "설",
    "計": "계", "製": "제", "作": "작", "業": "업", "技": "기", "術": "술",
    "工": "공", "程": "정", "科": "과", "目": "목", "類": "류", "分": "분",
    "析": "석", "統": "통", "計": "계", "數": "수", "據": "거", "値": "치",
    "質": "질", "量": "량", "性": "성", "能": "능", "力": "력", "場": "장",
    "合": "합", "的": "적", "用": "용", "法": "법", "理": "리", "道": "도",
    "氣": "기", "電": "전", "子": "자", "腦": "뇌", "信": "신", "號": "호",
    "網": "망", "路": "로", "統": "통", "信": "신", "處": "처", "理": "리",
    "情": "정", "報": "보", "通": "통", "知": "지", "識": "식", "智": "지",
    "慧": "혜", "感": "감", "知": "지", "覚": "각", "認": "인", "人": "인",
    "間": "간", "社": "사", "會": "회", "經": "경", "濟": "제", "政": "정",
    "治": "치", "法": "법", "律": "률", "規": "규", "則": "칙", "度": "도",
    "基": "기", "準": "준", "根": "근", "本": "본", "原": "원", "理": "리",
    "想": "상", "念": "념", "思": "사", "考": "고", "察": "찰", "察": "찰",
    "問": "문", "答": "답", "對": "대", "話": "화", "語": "어", "文": "문",
    "字": "자", "音": "음", "聲": "성", "色": "색", "光": "광", "影": "영",
    "形": "형", "象": "상", "圖": "도", "畫": "화", "像": "상", "映": "영",
    "視": "시", "聽": "청", "觸": "촉", "味": "미", "香": "향", "臭": "취",
    "冷": "냉", "熱": "열", "乾": "건", "濕": "습", "輕": "경", "重": "중",
    "速": "속", "遲": "지", "強": "강", "弱": "약", "大": "대", "小": "소",
    "多": "다", "少": "소", "長": "장", "短": "단", "高": "고", "低": "저",
    "深": "심", "淺": "천", "廣": "광", "狹": "협", "厚": "후", "薄": "박",
    "明": "명", "暗": "암", "正": "정", "邪": "사", "善": "선", "惡": "악",
    "美": "미", "醜": "추", "真": "진", "僞": "위", "實": "실", "虛": "허",
    "有": "유", "無": "무", "生": "생", "死": "사", "老": "로", "少": "소",
    "男": "남", "女": "여", "子": "자", "父": "부", "母": "모", "兄": "형",
    "弟": "제", "姉": "자", "妹": "매", "友": "유", "師": "사", "弟": "제",
    "書": "서", "畫": "화", "數": "수", "理": "리", "工": "공", "醫": "의",
    "農": "농", "商": "상", "兵": "병", "軍": "군", "船": "선", "車": "차",
    "飛": "비", "機": "기", "關": "관", "門": "문", "戶": "호", "屋": "옥",
    "家": "가", "室": "실", "庭": "정", "園": "원", "林": "림", "森": "삼",
    "山": "산", "川": "천", "海": "해", "池": "지", "湖": "호", "島": "도",
    "石": "석", "金": "금", "銀": "은", "銅": "동", "鐵": "철", "木": "목",
    "竹": "축", "花": "화", "草": "초", "果": "과", "穀": "곡", "肉": "육",
    "魚": "어", "鳥": "조", "獸": "수", "蟲": "충", "貝": "패", "角": "각",
    "牙": "아", "齒": "치", "骨": "골", "血": "혈", "肉": "육", "皮": "피",
    "毛": "모", "髮": "발", "目": "목", "耳": "이", "鼻": "비", "口": "구",
    "手": "수", "足": "족", "心": "심", "身": "신", "首": "수", "頭": "두",
    "面": "면", "頸": "경", "肩": "견", "背": "배", "胸": "흉", "腹": "복",
    "腰": "요", "膝": "슬", "脛": "경", "足": "족", "步": "보", "立": "립",
    "坐": "좌", "臥": "와", "眠": "면", "夢": "몽", "覺": "각", "醉": "취",
    "醒": "성", "食": "식", "飮": "음", "飢": "기", "飽": "포", "渴": "갈",
    "寒": "한", "暑": "서", "溫": "온", "涼": "량", "風": "풍", "雨": "우",
    "雪": "설", "雷": "뇌", "電": "전", "雲": "운", "霧": "무", "霜": "상",
    "露": "로", "冰": "빙", "火": "화", "炎": "염", "烟": "연", "灰": "회",
    "土": "토", "泥": "니", "沙": "사", "塵": "진", "空": "공", "天": "천",
    "地": "지", "日": "일", "月": "월", "星": "성", "辰": "신", "宿": "숙",
    "度": "도", "次": "차", "第": "제", "等": "등", "級": "급", "品": "품",
    "位": "위", "祿": "록", "俸": "봉", "賞": "상", "罰": "벌", "罪": "죄",
    "刑": "형", "法": "법", "令": "영", "制": "제", "度": "도", "規": "규",
    "格": "격", "式": "식", "型": "형", "模": "모", "範": "범", "準": "준",
    "繩": "승", "墨": "묵", "鉛": "연", "筆": "필", "硯": "연", "紙": "지",
    "帛": "백", "絹": "견", "綾": "릉", "羅": "라", "緞": "단", "布": "포",
    "麻": "마", "絲": "사", "縷": "루", "線": "선", "織": "직", "染": "염",
    "色": "색", "彩": "채", "紅": "홍", "紫": "자", "黃": "황", "白": "백",
    "黑": "흑", "碧": "벽", "綠": "록", "藍": "남", "赤": "적", "朱": "주",
    "丹": "단", "墨": "묵", "硃": "주", "翠": "취", "霞": "하", "虹": "홍",
    "霧": "무", "霜": "상", "露": "로", "雷": "뇌", "電": "전", "風": "풍",
    "雨": "우", "雪": "설", "雲": "운", "日": "일", "月": "월", "星": "성",
    "火": "화", "水": "수", "木": "목", "金": "금", "土": "토",
    "深化": "심화", "新": "신",
    "寫作": "사작",
}

_HANJA_PATTERN = re.compile(
    "|".join(re.escape(k) for k in sorted(_HANJA_MAP.keys(), key=len, reverse=True))
)


def hanja_to_hangul(text: str) -> str:
    """한자(漢字)를 한글(한국어 음독)로 변환합니다."""
    if not text:
        return text
    return _HANJA_PATTERN.sub(lambda m: _HANJA_MAP[m.group()], text)


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
            "name": hanja_to_hangul(c["course_name"]),
            "type": course_type,
            "credits": int(credit) if credit == int(credit) else credit,
            "category": _category_label(course_type),
            "department": _department_from_code(code),
            "professor": default_professor,
            "room": default_room,
            "time_slots": default_time_slots,
            "capacity": 0,
            "enrolled": 0,
            "description": hanja_to_hangul(c["course_description"]),
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
                        "name": hanja_to_hangul(name),
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
            "title": hanja_to_hangul(title),
            "content": hanja_to_hangul(n.get("content", "") or title),
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
            "title": hanja_to_hangul(e["event_name"]),
            "start_date": e["start_date"],
            "end_date": e["end_date"],
            "category": category,
            "alert_days_before": alert_days,
            "prerequisite": prerequisite,
            "description": hanja_to_hangul(e.get("description", "")),
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


# ==============================
# 교육과정/트랙/졸업요건 데이터
# ==============================

@lru_cache(maxsize=1)
def load_programs() -> dict[int, dict]:
    """programs.csv를 로드하여 program_id → 프로그램 정보 dict 반환"""
    raw = _read_csv("programs.csv")
    programs = {}
    for p in raw:
        pid = int(p["program_id"])
        programs[pid] = {
            "program_id": pid,
            "name": p["program_name"],
            "type": p["program_type"],
            "required_credits": float(p["required_credits"]) if p.get("required_credits") else 0,
            "effective_from_year": p.get("effective_from_year", ""),
        }
    return programs


@lru_cache(maxsize=1)
def load_curriculum_courses() -> dict[int, list[dict]]:
    """
    curriculum_courses.csv를 로드하여 program_id → 과목 리스트 매핑 반환

    반환 형식:
    {
        5: [
            {
                "course_id": 346,
                "completion_type": "전공선택",
                "is_required": False,
                "recommended_grade": 2,
                "semester": "1학기",
                "note": "",
                "curriculum_year": 2026,
            },
            ...
        ],
        0: [...],  # program_id가 없는 일반 교육과정
    }
    """
    raw = _read_csv("curriculum_courses.csv")
    courses_by_program: dict[int, list[dict]] = {}
    for row in raw:
        pid_str = row.get("program_id", "").strip()
        pid = int(pid_str) if pid_str else 0

        entry = {
            "course_id": int(row["course_id"]),
            "completion_type": _normalize_completion_type(row["completion_type"]),
            "is_required": row["is_required"] == "True",
            "recommended_grade": int(row["recommended_grade"]) if row.get("recommended_grade") else None,
            "semester": row.get("semester", ""),
            "note": row.get("note", ""),
            "curriculum_year": int(row["curriculum_year"]) if row.get("curriculum_year") else None,
            "program_id": pid,
        }
        courses_by_program.setdefault(pid, []).append(entry)
    return courses_by_program


@lru_cache(maxsize=1)
def load_graduation_requirements() -> list[dict]:
    """graduation_requirements.csv를 로드하여 졸업요건 리스트 반환"""
    raw = _read_csv("graduation_requirements.csv")
    requirements = []
    for r in raw:
        pid_str = r.get("program_id", "").strip()
        requirements.append({
            "requirement_id": int(r["requirement_id"]),
            "admission_year": int(r["admission_year"]) if r.get("admission_year") else None,
            "program_id": int(pid_str) if pid_str else None,
            "requirement_category": r["requirement_category"],
            "required_credits": float(r["required_credits"]) if r.get("required_credits") else None,
            "requirement_text": r.get("requirement_text", ""),
        })
    return requirements


@lru_cache(maxsize=1)
def load_course_keywords() -> dict[int, list[dict]]:
    """course_keywords.csv를 로드하여 offering_id → 키워드 리스트 매핑 반환"""
    raw = _read_csv("course_keywords.csv")
    keywords_map: dict[int, list[dict]] = {}
    for row in raw:
        oid = int(row["offering_id"])
        keywords_map.setdefault(oid, []).append({
            "keyword": row["keyword"],
            "keyword_category": row.get("keyword_category", ""),
            "confidence_score": float(row["confidence_score"]) if row.get("confidence_score") else 0.0,
        })
    return keywords_map


@lru_cache(maxsize=1)
def load_course_relationships() -> list[dict]:
    """course_relationships.csv를 로드하여 과목 간 관계 리스트 반환"""
    raw = _read_csv("course_relationships.csv")
    relationships = []
    for row in raw:
        relationships.append({
            "from_course_id": int(row["from_course_id"]),
            "to_course_id": int(row["to_course_id"]),
            "relationship_type": row["relationship_type"],
            "program_id": int(row["program_id"]) if row.get("program_id", "").strip() else None,
            "note": row.get("note", ""),
        })
    return relationships
