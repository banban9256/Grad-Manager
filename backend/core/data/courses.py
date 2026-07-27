"""과목 데이터 모듈 - CSV 기반 실제 데이터 로딩 + 트랙/이수구분 검증 + 학과 필터링"""

from .csv_loader import (
    load_courses,
    load_programs,
    load_curriculum_courses,
    load_graduation_requirements,
    load_course_keywords,
    load_course_relationships,
    _normalize_completion_type,
    hanja_to_hangul,
)

COURSES = None

# ==============================
# 학과/트랙 필터링 상수
# ==============================

# AISW 학과 관련 과목 코드 접두사 (전공 과목)
_AISW_MAJOR_PREFIXES = {"SH", "DS", "AI"}

# 교양 과목 코드 접두사
_LIBERAL_PREFIXES = {"KY", "KYC", "KYA", "KYD"}

# 계열공통 과목 코드 접두사
_COMMON_PREFIXES = {"FLOW"}

# 채플 과목 코드
_CHAPEL_CODES = {"KY100", "KY101", "KY201", "KY304", "KY509"}

# 특화/융합 전공 키워드 (타전공 추천 차단 대상)
_SPECIALIZATION_KEYWORDS = ["특화", "융합", "특화전공", "융합전공"]


def _ensure_loaded():
    global COURSES
    if COURSES is None:
        COURSES = load_courses()


def get_course(course_code: str) -> dict | None:
    _ensure_loaded()
    return COURSES.get(course_code)


def _normalize_course_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def _get_course_prefix(code: str) -> str:
    """과목 코드에서 접두사 추출 (문자 부분만)"""
    return "".join(ch for ch in code if ch.isalpha())


def _is_chapel_course(course: dict) -> bool:
    """과목이 채플 과목인지 확인"""
    code = (course.get("code") or "").lstrip("*")
    name = course.get("name", "")
    return code in _CHAPEL_CODES or "채플" in name


def _get_taken_course_filter(student: dict) -> tuple[set[str], set[str]]:
    _ensure_loaded()
    completed = set(student.get("completed_courses", []))
    in_progress = set(student.get("in_progress_courses", []))
    taken_codes = completed | in_progress

    taken_names = set()
    for code in taken_codes:
        course = COURSES.get(code)
        if course:
            normalized_name = _normalize_course_name(course.get("name", ""))
            if normalized_name:
                taken_names.add(normalized_name)

    return taken_codes, taken_names


def _is_course_already_taken(course: dict, taken_codes: set[str], taken_names: set[str]) -> bool:
    if not course:
        return False

    raw_code = course.get("code") or ""
    code_key = raw_code.strip().lstrip("*").lower()
    if code_key and code_key in {c.strip().lstrip("*").lower() for c in taken_codes if c}:
        return True

    normalized_name = _normalize_course_name(course.get("name", ""))
    return bool(normalized_name and normalized_name in taken_names)


def _is_course_allowed_for_department(course: dict, student: dict) -> bool:
    """
    과목이 해당 학생의 학과/트랙에서 수강할 수 있는 과목인지 확인합니다.

    규칙:
    1. 교양 과목(KY, KYC, KYA, KYD) → 항상 허용
    2. 계열공통(FLOW) → 항상 허용
    3. AISW 전공 과목(SH, DS, AI) → AISW 학생에게 허용
    4. 타전공 과목 → 전선/계공/교필/교양 학점이 모두 충족된 경우에만 허용
       단, 특화/융합 전공 사용자에게는 타전공 추천 차단
    """
    code = (course.get("code") or "").lstrip("*")
    prefix = _get_course_prefix(code)
    course_type = _normalize_completion_type(course.get("type", ""))

    # 1. 교양 과목은 항상 허용
    if prefix in _LIBERAL_PREFIXES:
        return True

    # 2. 계열공통은 항상 허용
    if prefix in _COMMON_PREFIXES:
        return True

    # 3. AISW 전공 과목은 AISW 학생에게 허용
    if prefix in _AISW_MAJOR_PREFIXES:
        return True

    # 4. 타전공 과목 필터링
    # 특화/융합 전공 사용자에게는 타전공 추천 차단
    specialized_track = student.get("specialized_track", "")
    convergence_major = student.get("convergence_major", "")
    has_specialization = any(kw in specialized_track for kw in _SPECIALIZATION_KEYWORDS)
    has_convergence = any(kw in convergence_major for kw in _SPECIALIZATION_KEYWORDS)

    if has_specialization or has_convergence:
        return False

    # 전선/계공/교필/교양 학점이 모두 충족된 경우에만 타전공 허용
    if _are_core_categories_satisfied(student):
        return True

    # 그 외 타전공 과목은 추천 후보에서 제외
    return False


def _are_core_categories_satisfied(student: dict) -> bool:
    """
    핵심 카테고리(전공선택, 계열공통, 교양필수, 교양선택)의 학점이 모두 충족되었는지 확인합니다.
    """
    grad_summary = get_graduation_credit_summary(student)
    core_categories = ["전공선택", "계열공통", "교양필수", "교양선택"]

    for cat in core_categories:
        info = grad_summary.get(cat, {"remaining": 0})
        if info.get("remaining", 0) > 0:
            return False
    return True


def get_available_courses(student: dict, semester: str = None) -> list[dict]:
    _ensure_loaded()
    taken, taken_names = _get_taken_course_filter(student)

    sem = semester or student.get("target_semester")
    target_year = None
    target_sem = None
    if sem and "-" in sem:
        parts = sem.split("-", 1)
        target_year = parts[0]
        target_sem = parts[1]

    # 채플 8회 이수 완료 체크
    completed_codes = student.get("completed_courses", [])
    chapel_completed_count = 0
    for code in completed_codes:
        code_clean = code.lstrip("*")
        course_obj = COURSES.get(code_clean)
        if _is_chapel_course({"code": code_clean, "name": course_obj.get("name", "") if course_obj else ""}):
            chapel_completed_count += 1

    is_chapel_satisfied = chapel_completed_count >= 8

    filtered_courses = []
    for code, course in COURSES.items():
        # 1. 기이수/수강중 과목 완전 차단
        if _is_course_already_taken(course, taken, taken_names):
            continue

        # 2. 채플 이수 요건 충족 시 채플 과목 완전 제외
        if is_chapel_satisfied and _is_chapel_course(course):
            continue

        # 3. 학과/트랙 필터링 (타전공 우선순위 기반)
        if not _is_course_allowed_for_department(course, student):
            continue

        # 4. 학기 필터링
        if target_year and target_sem:
            offerings = course.get("offerings", [])
            if len(offerings) > 0:
                has_matching = any(
                    str(o.get("academic_year")) == target_year and o.get("semester") == target_sem
                    for o in offerings
                )
                if not has_matching:
                    continue

        filtered_courses.append(course)
    return filtered_courses


def get_required_remaining(student: dict, semester: str = None) -> list[dict]:
    _ensure_loaded()
    # AISW 학과는 전공 필수 과목이 없으므로 빈 리스트 반환
    if student.get("department") in ("AISW", "AI.SW학", "인공지능소프트웨어학과", "인공지능소프트웨어학부"):
        return []

    taken, taken_names = _get_taken_course_filter(student)

    sem = semester or student.get("target_semester")
    target_year = None
    target_sem = None
    if sem and "-" in sem:
        parts = sem.split("-", 1)
        target_year = parts[0]
        target_sem = parts[1]

    filtered_courses = []
    for code, course in COURSES.items():
        if _is_course_already_taken(course, taken, taken_names):
            continue
        if course.get("type") not in ("전공필수", "required"):
            continue
        if target_year and target_sem:
            offerings = course.get("offerings", [])
            if len(offerings) > 0:
                has_matching = any(
                    str(o.get("academic_year")) == target_year and o.get("semester") == target_sem
                    for o in offerings
                )
                if not has_matching:
                    continue
        filtered_courses.append(course)
    return filtered_courses


def get_all_remaining_required_for_semester(student: dict, semester: str = None) -> dict:
    """미이수 필수 과목(전공필수 + 교양필수 + 계열공통) 중 해당 학기에 개설된 과목을 반환합니다."""
    _ensure_loaded()
    taken, taken_names = _get_taken_course_filter(student)

    sem = semester or student.get("target_semester")
    target_year = None
    target_sem = None
    if sem and "-" in sem:
        parts = sem.split("-", 1)
        target_year = parts[0]
        target_sem = parts[1]

    # AISW 학과는 전공필수 과목이 없으므로 필수 과목 타입 목록에서 제외하되 계열공통 추가
    is_aisw = student.get("department") in ("AISW", "AI.SW학", "인공지능소프트웨어학과", "인공지능소프트웨어학부")
    required_types = {"교양필수", "general_required", "계열공통"} if is_aisw else {"전공필수", "교양필수", "required", "general_required", "계열공통"}

    by_category = {}
    for code, course in COURSES.items():
        if _is_course_already_taken(course, taken, taken_names):
            continue
        ctype = course.get("type", "")
        if ctype not in required_types:
            continue

        is_available_this_sem = False
        if target_year and target_sem:
            offerings = course.get("offerings", [])
            if len(offerings) > 0:
                is_available_this_sem = any(
                    str(o.get("academic_year")) == target_year and o.get("semester") == target_sem
                    for o in offerings
                )
            else:
                is_available_this_sem = True
        else:
            is_available_this_sem = True

        label = ctype
        if label not in by_category:
            by_category[label] = {"available_now": [], "not_available_now": []}

        entry = {
            "code": code,
            "name": course.get("name", ""),
            "credits": course.get("credits", 0),
            "type": ctype,
            "time_slots": course.get("time_slots", []),
            "professor": course.get("professor", "미정"),
            "room": course.get("room", "미정"),
        }

        if is_available_this_sem:
            by_category[label]["available_now"].append(entry)
        else:
            by_category[label]["not_available_now"].append(entry)

    return by_category


def get_all_semesters() -> list[str]:
    from .csv_loader import _read_csv
    import sqlite3
    from pathlib import Path

    semesters = set()
    try:
        offerings_raw = _read_csv("course_offerings.csv")
        for o in offerings_raw:
            year = o.get("academic_year")
            sem = o.get("semester")
            if year and sem:
                semesters.add(f"{year}-{sem}")
    except Exception:
        pass

    try:
        db_path = Path(__file__).resolve().parent.parent.parent.parent / "gradmanager.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='course_offerings'")
            if cursor.fetchone():
                cursor.execute("SELECT DISTINCT academic_year, semester FROM course_offerings")
                for year, sem in cursor.fetchall():
                    if year and sem:
                        semesters.add(f"{year}-{sem}")
            conn.close()
    except Exception:
        pass

    if not semesters:
        semesters = {
            "2026-2학기", "2026-1학기", "2025-2학기", "2025-1학기",
            "2024-2학기", "2024-1학기", "2023-2학기", "2023-1학기",
        }

    # 항상 최신 학기 포함 (CSV에 없어도)
    semesters.add("2026-2학기")
    semesters.add("2026-1학기")

    def semester_sort_key(s):
        try:
            parts = s.split("-", 1)
            return (int(parts[0]), 2 if "2" in parts[1] else 1)
        except Exception:
            return (0, 0)

    return sorted(list(semesters), key=semester_sort_key, reverse=True)


# ==============================
# 트랙/전공 매핑
# ==============================

_TRACK_NAME_TO_PROGRAM_ID = {
    "AISW 본전공": 1, "소프트웨어전공": 8, "인공지능전공": 9,
    "데이터사이언스전공": 10, "XR콘텐츠전공": 11, "지능형IoT전공": 12,
    "인지 감성 특화": 5, "인지감성 특화": 5, "인지감성": 5,
    "앰비언트 특화": 6, "앰비언트": 6,
    "AI융합장애인라이프케어": 19, "AI융합시니어라이프케어": 20,
    "장애인라이프케어": 19, "시니어라이프케어": 20,
}


def _resolve_program_ids(student: dict) -> list[int]:
    program_ids = []
    for track in student.get("major_tracks", []):
        for name, pid in _TRACK_NAME_TO_PROGRAM_ID.items():
            if name in track and pid not in program_ids:
                program_ids.append(pid)
    spec = student.get("specialized_track", "")
    if spec:
        for name, pid in _TRACK_NAME_TO_PROGRAM_ID.items():
            if name in spec and pid not in program_ids:
                program_ids.append(pid)
    conv = student.get("convergence_major", "")
    if conv:
        for name, pid in _TRACK_NAME_TO_PROGRAM_ID.items():
            if name in conv and pid not in program_ids:
                program_ids.append(pid)
    if not program_ids:
        program_ids.append(1)
    return program_ids


def _build_course_id_to_code_map() -> dict[int, str]:
    """course_id (numeric) → course_code 매핑 구축"""
    import sqlite3
    from pathlib import Path
    id_to_code = {}
    try:
        db_path = Path(__file__).resolve().parent.parent.parent.parent / "gradmanager.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT course_id, course_code FROM courses")
            for cid, code in cursor.fetchall():
                id_to_code[int(cid)] = code.lstrip("*")
            conn.close()
    except Exception:
        pass

    for code, course in COURSES.items():
        pass
    return id_to_code


def _get_course_id_for_code(code: str) -> int | None:
    """course_code → course_id (numeric) 역매핑"""
    import sqlite3
    from pathlib import Path
    try:
        db_path = Path(__file__).resolve().parent.parent.parent.parent / "gradmanager.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT course_id FROM courses WHERE course_code = ?", (code,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return int(row[0])
    except Exception:
        pass
    return None


# ==============================
# 트랙별 교육과정 조회
# ==============================

def get_track_curriculum(student: dict) -> dict:
    program_ids = _resolve_program_ids(student)
    programs = load_programs()
    curriculum = load_curriculum_courses()
    grad_reqs = load_graduation_requirements()
    admission_year = student.get("enrolled_year", 2023)

    relevant_programs = {}
    courses_by_program = {}
    for pid in program_ids:
        if pid in programs:
            relevant_programs[pid] = programs[pid]
        courses_by_program[pid] = curriculum.get(pid, [])

    relevant_requirements = []
    available_years = sorted(set(r["admission_year"] for r in grad_reqs if r["admission_year"]))
    if not available_years:
        relevant_requirements = grad_reqs
    else:
        matched_year = admission_year
        if matched_year not in available_years:
            candidates = [y for y in available_years if y <= admission_year]
            if candidates:
                matched_year = candidates[-1]
            else:
                matched_year = available_years[0]
        relevant_requirements = [
            r for r in grad_reqs
            if r["admission_year"] == matched_year
            and (r["program_id"] is None or r["program_id"] in program_ids)
        ]

    return {
        "programs": relevant_programs,
        "courses_by_program": courses_by_program,
        "requirements": relevant_requirements,
        "completed_courses": student.get("completed_courses", []),
    }


# ==============================
# 트랙별 미이수 필수 과목
# ==============================

def get_required_remaining_by_track(student: dict, semester: str = None) -> list[dict]:
    _ensure_loaded()
    curriculum_info = get_track_curriculum(student)
    taken, taken_names = _get_taken_course_filter(student)

    sem = semester or student.get("target_semester")
    target_year = None
    target_sem = None
    if sem and "-" in sem:
        parts = sem.split("-", 1)
        target_year = parts[0]
        target_sem = parts[1]

    id_to_code = _build_course_id_to_code_map()
    required_course_codes = set()
    for pid, courses_list in curriculum_info["courses_by_program"].items():
        for entry in courses_list:
            if entry["is_required"]:
                cid = entry["course_id"]
                code = id_to_code.get(cid)
                if code:
                    required_course_codes.add(code)

    result = []
    for code, course in COURSES.items():
        if _is_course_already_taken(course, taken, taken_names):
            continue
        if code not in required_course_codes and course.get("type") != "전공필수":
            continue
        if target_year and target_sem:
            offerings = course.get("offerings", [])
            if offerings:
                has_offering = any(
                    str(o.get("academic_year")) == target_year and o.get("semester") == target_sem
                    for o in offerings
                )
                if not has_offering:
                    continue
        result.append(course)
    return result


# ==============================
# 이수구분별 학점 요약
# ==============================

def get_graduation_credit_summary(student: dict) -> dict:
    _ensure_loaded()
    curriculum_info = get_track_curriculum(student)
    
    # DB 수강 기록 조회 및 course_type/earned_credit 매핑 구축
    course_types = {}
    completed_credits_map = {}
    try:
        from app.database import SessionLocal
        from app import models as db_models
        db = SessionLocal()
        sid_int = int(student["student_id"])
        histories = db.query(db_models.StudentCourseHistory).filter(
            db_models.StudentCourseHistory.student_id == sid_int
        ).all()
        
        history_records = []
        for h in histories:
            c_rec = db.query(db_models.Course).filter(
                db_models.Course.course_id == h.course_id
            ).first()
            code = c_rec.course_code if c_rec else f"UNKNOWN-{h.course_id}"
            cat = getattr(h, 'course_type', None) or ""
            history_records.append({
                "code": code,
                "grade": h.grade or "",
                "category": cat,
                "credit": float(h.earned_credit) if h.earned_credit else 0,
                "is_retake": h.is_retake or False,
                "history_id": h.history_id,
                "semester": h.semester_taken or "",
            })
            
        # 재수강 포기 식별
        from collections import defaultdict
        import re
        n = len(history_records)
        parent = list(range(n))
        def find(i):
            if parent[i] == i: return i
            parent[i] = find(parent[i])
            return parent[i]
        def union(i, j):
            ri, rj = find(i), find(j)
            if ri != rj: parent[ri] = rj

        for i in range(n):
            for j in range(i+1, n):
                if history_records[i]["code"] == history_records[j]["code"]:
                    union(i, j)
        groups = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(history_records[i])

        forfeited_ids = set()
        for root, instances in groups.items():
            has_retake = any(inst["is_retake"] for inst in instances)
            if has_retake and len(instances) > 1:
                def sem_score(s):
                    m = re.match(r'(\d+)-(\d)', s)
                    return int(m.group(1))*10 + int(m.group(2)) if m else 0
                sorted_inst = sorted(instances, key=lambda x: sem_score(x["semester"]))
                for inst in sorted_inst[:-1]:
                    forfeited_ids.add(inst["history_id"])

        for rec in history_records:
            if rec["history_id"] in forfeited_ids:
                continue
            if rec["grade"].upper() == "F":
                continue
            course_types[rec["code"]] = rec["category"]
            completed_credits_map[rec["code"]] = rec["credit"]
        db.close()
    except Exception:
        pass

    completed = set(student.get("completed_courses", []))
    in_progress = set(student.get("in_progress_courses", []))
    taken = completed | in_progress

    categories = {
        "전공필수": {"required": 0, "completed": 0, "remaining": 0},
        "전공선택": {"required": 0, "completed": 0, "remaining": 0},
        "교양필수": {"required": 0, "completed": 0, "remaining": 0},
        "교양선택": {"required": 0, "completed": 0, "remaining": 0},
        "계열공통": {"required": 0, "completed": 0, "remaining": 0},
        "일반선택": {"required": 0, "completed": 0, "remaining": 0},
    }

    is_aisw = student.get("department") in ("AISW", "AI.SW학", "인공지능소프트웨어학과", "인공지능소프트웨어학부")

    for req in curriculum_info["requirements"]:
        cat = req["requirement_category"]
        credits = req["required_credits"] or 0
        cat_lower = cat.lower()
        if "최대" in cat_lower or "인정한도" in cat_lower:
            continue
        if "총 이수학점" in cat_lower:
            continue
        if "타전공" in cat_lower:
            continue
        if "채플" in cat_lower:
            continue
        if "기독교" in cat_lower:
            continue
        if "계열공통" in cat_lower:
            categories["계열공통"]["required"] += credits
        elif "전공" in cat_lower and "특화" not in cat_lower:
            if is_aisw:
                categories["전공선택"]["required"] += credits
            elif "필수" in cat_lower:
                categories["전공필수"]["required"] += credits
            elif "선택" in cat_lower:
                categories["전공선택"]["required"] += credits
            else:
                categories["전공선택"]["required"] += credits
        elif "교양" in cat_lower:
            if "필수" in cat_lower:
                categories["교양필수"]["required"] += credits
            else:
                categories["교양선택"]["required"] += credits

    for code in taken:
        course = COURSES.get(code)
        ctype = course_types.get(code) if code in course_types else None
        if not ctype:
            ctype = _normalize_completion_type(course.get("type", "")) if course else "일반선택"
        else:
            ctype = _normalize_completion_type(ctype)
            
        credits = completed_credits_map.get(code) if code in completed_credits_map else (course.get("credits", 0) if course else 3)

        # AISW 학과 학생은 전공필수 과목도 전공선택으로 인정
        if is_aisw and ctype == "전공필수":
            ctype = "전공선택"

        if ctype in categories:
            categories[ctype]["completed"] += credits
        else:
            categories["일반선택"]["completed"] += credits

    for cat in categories:
        categories[cat]["remaining"] = max(0, categories[cat]["required"] - categories[cat]["completed"])

    return categories


# ==============================
# 이수구분 검증
# ==============================

def validate_completed_categories(student: dict) -> dict:
    """
    학생의 기수강 과목들이 졸업요건 기준 이수구분과 맞는지 검증합니다.

    curriculum_courses.csv와 courses.csv에서 이중으로 이수구분을 확인하여
    전공인지 일반선택인지 등을 판단합니다.
    """
    _ensure_loaded()
    completed = student.get("completed_courses", [])
    in_progress = student.get("in_progress_courses", [])

    curriculum = load_curriculum_courses()
    id_to_code = _build_course_id_to_code_map()

    curriculum_type_by_code = {}
    for pid, courses_list in curriculum.items():
        for entry in courses_list:
            cid = entry["course_id"]
            code = id_to_code.get(cid)
            if not code:
                continue
            ctype = entry["completion_type"]
            if entry["is_required"]:
                ctype = "전공필수"
            if code not in curriculum_type_by_code:
                curriculum_type_by_code[code] = ctype

    validated = []
    mismatched = []
    category_summary = {
        "전공필수": 0, "전공선택": 0, "교양필수": 0,
        "교양선택": 0, "계열공통": 0, "일반선택": 0,
    }

    all_taken = completed + in_progress
    for code in all_taken:
        course = COURSES.get(code)
        if not course:
            continue

        inferred_type = _normalize_completion_type(course.get("type", ""))
        curriculum_type = curriculum_type_by_code.get(code, inferred_type)

        is_match = (curriculum_type == inferred_type) or (
            curriculum_type in ("전공필수", "전공선택") and inferred_type in ("전공필수", "전공선택")
        )

        entry = {
            "code": code,
            "name": course.get("name", code),
            "curriculum_type": curriculum_type,
            "inferred_type": inferred_type,
            "match": is_match,
        }
        validated.append(entry)

        if not is_match:
            mismatched.append(entry)

        if curriculum_type in category_summary:
            category_summary[curriculum_type] += course.get("credits", 0)
        else:
            category_summary["일반선택"] += course.get("credits", 0)

    return {
        "validated_courses": validated,
        "mismatched_courses": mismatched,
        "category_summary": category_summary,
    }


# ==============================
# 관심 키워드 기반 과목 추천
# ==============================

_INTEREST_CATEGORY_MAP = {
    "ai": ["전공필수", "전공선택", "계열공통"],
    "인공지능": ["전공필수", "전공선택", "계열공통"],
    "프로그래밍": ["전공필수", "전공선택"],
    "코딩": ["전공필수", "전공선택"],
    "소프트웨어": ["전공필수", "전공선택", "계열공통"],
    "sw": ["전공필수", "전공선택", "계열공통"],
    "데이터": ["전공필수", "전공선택"],
    "컴퓨터": ["전공필수", "전공선택"],
    "머신러닝": ["전공필수", "전공선택"],
    "딥러닝": ["전공필수", "전공선택"],
    "알고리즘": ["전공필수", "전공선택"],
    "운동": ["교양선택"],
    "체육": ["교양선택"],
    "스포츠": ["교양선택"],
    "축구": ["교양선택"],
    "농구": ["교양선택"],
    "테니스": ["교양선택"],
    "등산": ["교양선택"],
    "음악": ["교양선택"],
    "미술": ["교양선택"],
    "영어": ["교양필수", "교양선택"],
    "독서": ["교양선택"],
    "철학": ["교양선택"],
    "역사": ["교양선택"],
    "심리": ["교양선택"],
    "경제": ["교양선택"],
    "경영": ["교양선택"],
    "글쓰기": ["교양필수", "교양선택"],
    "커뮤니케이션": ["교양선택"],
    "기독교": ["교양필수"],
    "봉사": ["교양선택"],
    "보안": ["전공선택"],
    "네트워크": ["전공선택"],
    "웹": ["전공선택"],
    "서버": ["전공선택"],
}


def get_interest_matching_courses(student: dict, interest_keywords: list[str]) -> list[dict]:
    """
    관심 키워드로 과목을 검색하고, 졸업요건 카테고리에 맞는 과목을 추천합니다.

    반환 형식:
    [
        {"course": dict, "category": str, "relevance_score": float, "reason": str, "matched_keywords": list},
        ...
    ]
    """
    _ensure_loaded()
    taken, taken_names = _get_taken_course_filter(student)

    target_categories = set()
    matched_labels = []
    for kw in interest_keywords:
        kw_lower = kw.lower().strip()
        for keyword, categories in _INTEREST_CATEGORY_MAP.items():
            if keyword in kw_lower or kw_lower in keyword:
                target_categories.update(categories)
                matched_labels.append(kw)

    if not target_categories:
        target_categories = {"전공필수", "전공선택", "교양선택", "계열공통"}

    # 채플 8회 이수 완료 체크
    completed_codes = student.get("completed_courses", [])
    chapel_completed_count = 0
    for code in completed_codes:
        code_clean = code.lstrip("*")
        course_obj = COURSES.get(code_clean)
        if _is_chapel_course({"code": code_clean, "name": course_obj.get("name", "") if course_obj else ""}):
            chapel_completed_count += 1
    is_chapel_satisfied = chapel_completed_count >= 8

    results = []
    for code, course in COURSES.items():
        # 기이수/수강중 과목 차단
        if _is_course_already_taken(course, taken, taken_names):
            continue

        # 채플 과목 차단
        if is_chapel_satisfied and _is_chapel_course(course):
            continue

        # 학과/트랙 필터링 (타전공 우선순위 기반)
        if not _is_course_allowed_for_department(course, student):
            continue

        category = _normalize_completion_type(course.get("type", ""))
        if category not in target_categories:
            continue

        course_text = (course.get("name", "") + " " + course.get("description", "")).lower()
        relevance = 0.0
        matched_kws = []
        for kw in interest_keywords:
            if kw.lower() in course_text:
                relevance += 1.0
                matched_kws.append(kw)

        base_score = 0.5
        if category in ("전공필수", "교양필수"):
            base_score = 0.7
        elif category in ("전공선택", "교양선택"):
            base_score = 0.6

        total_score = base_score + relevance

        if relevance > 0 or total_score > 0.5:
            reason_parts = []
            if matched_kws:
                reason_parts.append(f"'{', '.join(matched_kws)}' 관련")
            reason_parts.append(f"{category} 과목")
            reason_parts.append(f"({course['credits']}학점)")

            results.append({
                "course": course,
                "category": category,
                "relevance_score": total_score,
                "reason": " ".join(reason_parts),
                "matched_keywords": matched_kws,
            })

    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results


# ==============================
# 관심 키워드 + 졸업요건 기반 추천
# ==============================

def recommend_by_interest_with_graduation(student: dict, interest_text: str) -> list[dict]:
    """
    사용자 관심사 텍스트를 분석하여 졸업요건에 해당하는 과목을 추천합니다.

    예: "AI에 관심 있어" → 전공필수/전공선택/계열공통 중 AI 관련 과목
    예: "운동 교양 듣고 싶어" → 교양선택 중 체육 관련 과목

    반환 형식:
    [
        {
            "course": dict,
            "category": str,
            "credit_status": str,  # "졸업요건 충족" / "학점 여유 있음" / "이미 충족"
            "reason": str,
        },
        ...
    ]
    """
    grad_summary = get_graduation_credit_summary(student)

    raw_results = get_interest_matching_courses(student, [interest_text])

    for item in raw_results:
        cat = item["category"]
        info = grad_summary.get(cat, {"remaining": 0})
        if info["remaining"] > 0:
            item["credit_status"] = f"졸업요건 미충족 ({cat} {info['remaining']}학점 부족)"
        else:
            item["credit_status"] = f"{cat} 요건 충족 완료"

    return raw_results
