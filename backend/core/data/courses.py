"""과목 데이터 모듈 - CSV 기반 실제 데이터 로딩"""

from .csv_loader import load_courses

# CSV에서 로드된 과목 데이터 (지연 로딩)
COURSES = None


def _ensure_loaded():
    """필요시 CSV에서 과목 데이터 로드"""
    global COURSES
    if COURSES is None:
        COURSES = load_courses()


def get_course(course_code: str) -> dict | None:
    """과목 코드로 과목 정보 조회"""
    _ensure_loaded()
    return COURSES.get(course_code)


def get_available_courses(student: dict, semester: str = None) -> list[dict]:
    """학생이 아직 수강하지 않은 과목 중 수강 가능 과목 반환"""
    _ensure_loaded()
    completed = set(student.get("completed_courses", []))
    in_progress = set(student.get("in_progress_courses", []))
    taken = completed | in_progress

    sem = semester or student.get("target_semester")
    target_year = None
    target_sem = None
    if sem and "-" in sem:
        parts = sem.split("-", 1)
        target_year = parts[0]
        target_sem = parts[1]

    filtered_courses = []
    for code, course in COURSES.items():
        if code in taken:
            continue
        
        # 학기 필터링
        if target_year and target_sem:
            offerings = course.get("offerings", [])
            if len(offerings) > 0:
                has_matching = False
                for o in offerings:
                    if str(o.get("academic_year")) == target_year and o.get("semester") == target_sem:
                        has_matching = True
                        break
                if not has_matching:
                    continue
        filtered_courses.append(course)
        
    return filtered_courses


def get_required_remaining(student: dict, semester: str = None) -> list[dict]:
    """졸업에 필요한 필수 과목 중 미이수 과목 반환"""
    _ensure_loaded()
    completed = set(student.get("completed_courses", []))
    in_progress = set(student.get("in_progress_courses", []))
    taken = completed | in_progress

    sem = semester or student.get("target_semester")
    target_year = None
    target_sem = None
    if sem and "-" in sem:
        parts = sem.split("-", 1)
        target_year = parts[0]
        target_sem = parts[1]

    filtered_courses = []
    for code, course in COURSES.items():
        if code in taken:
            continue
        if course.get("type") not in ("전공필수", "required"):
            continue
        
        if target_year and target_sem:
            offerings = course.get("offerings", [])
            if len(offerings) > 0:
                has_matching = False
                for o in offerings:
                    if str(o.get("academic_year")) == target_year and o.get("semester") == target_sem:
                        has_matching = True
                        break
                if not has_matching:
                    continue
        filtered_courses.append(course)
        
    return filtered_courses


def get_all_semesters() -> list[str]:
    """모든 개설된 분반 정보로부터 고유 학기 목록 추출하여 정렬해 반환"""
    from .csv_loader import _read_csv
    import sqlite3
    from pathlib import Path

    semesters = set()

    # 1. CSV 데이터에서 추출
    try:
        offerings_raw = _read_csv("course_offerings.csv")
        for o in offerings_raw:
            year = o.get("academic_year")
            sem = o.get("semester")
            if year and sem:
                semesters.add(f"{year}-{sem}")
    except Exception as e:
        print(f"Failed to read course_offerings.csv for semesters: {e}")

    # 2. SQLite 데이터베이스에서 추출 (존재하는 경우)
    try:
        db_path = Path(__file__).resolve().parent.parent.parent.parent / "gradmanager.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='course_offerings'")
            if cursor.fetchone():
                cursor.execute("SELECT DISTINCT academic_year, semester FROM course_offerings")
                db_sems = cursor.fetchall()
                for year, sem in db_sems:
                    if year and sem:
                        semesters.add(f"{year}-{sem}")
            conn.close()
    except Exception:
        pass

    # 만약 결과가 비어있다면 기본 제공 하드코딩 백업
    if not semesters:
        semesters = {
            "2026-2학기", "2026-1학기", "2025-2학기", "2025-1학기",
            "2024-2학기", "2024-1학기", "2023-2학기", "2023-1학기",
            "2022-2학기", "2022-1학기", "2021-2학기", "2021-1학기"
        }

    # 정렬 (최신 순서: 연도 역순, 학기 역순)
    def semester_sort_key(sem_str: str):
        try:
            parts = sem_str.split("-", 1)
            year = int(parts[0])
            sem_num = 2 if "2" in parts[1] else 1
            return (year, sem_num)
        except Exception:
            return (0, 0)

    sorted_sems = sorted(list(semesters), key=semester_sort_key, reverse=True)
    return sorted_sems
