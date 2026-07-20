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


def get_available_courses(student: dict) -> list[dict]:
    """학생이 아직 수강하지 않은 과목 중 수강 가능 과목 반환"""
    _ensure_loaded()
    completed = set(student.get("completed_courses", []))
    in_progress = set(student.get("in_progress_courses", []))
    taken = completed | in_progress

    return [course for code, course in COURSES.items() if code not in taken]


def get_required_remaining(student: dict) -> list[dict]:
    """졸업에 필요한 필수 과목 중 미이수 과목 반환"""
    _ensure_loaded()
    completed = set(student.get("completed_courses", []))
    in_progress = set(student.get("in_progress_courses", []))
    taken = completed | in_progress

    return [
        course for code, course in COURSES.items()
        if code not in taken and course["type"] in ("전공필수", "required")
    ]
