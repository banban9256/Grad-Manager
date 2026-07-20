"""가상 학생 데이터 - 나중에 실제 DB로 교체 예정"""

STUDENTS = {
    "20210001": {
        "name": "김정보",
        "student_id": "20210001",
        "department": "AISW",
        "major_tracks": ["AISW 본전공"],
        "enrolled_year": 2021,
        "current_semester": 7,
        "completed_credits": 90,
        "required_credits": 130,
        "completed_courses": [
            # 교양 필수
            "UNIV101", "UNIV102", "ENG101", "ENG102",
            "KR101", "MATH101",
            # 교양 선택
            "GEN201", "GEN202", "GEN301",
            # AISW 전공 기초
            "CS101", "CS102", "CS201", "CS202", "CS203",
            "MATH201", "MATH202",
            # AISW 전공 심화
            "AISW301", "AISW302", "AISW303",
        ],
        "in_progress_courses": ["AISW304", "CS301"],
        "gpa": 3.8,
        "mileage": 45,
        "keyword_preferences": ["장학금", "AI", "인턴"],
        "preferred_days": ["월", "화", "수"],
        "preferred_times": ["09:00-12:00", "14:00-17:00"],
        "avoid_times": ["18:00-21:00"],
    },
    "20220001": {
        "name": "박졸업",
        "student_id": "20220001",
        "department": "AISW",
        "major_tracks": ["AISW 본전공", "인지 감성 특화"],
        "enrolled_year": 2022,
        "current_semester": 5,
        "completed_credits": 70,
        "required_credits": 130,
        "completed_courses": [
            "UNIV101", "UNIV102", "ENG101", "ENG102",
            "KR101", "MATH101",
            "GEN201", "GEN202",
            "CS101", "CS102", "CS201", "CS202",
            "MATH201",
            "AISW301",
        ],
        "in_progress_courses": ["CS203", "AISW302"],
        "gpa": 3.5,
        "mileage": 30,
        "keyword_preferences": ["공모전", "특화전공", "융합"],
        "preferred_days": ["화", "목"],
        "preferred_times": ["10:00-18:00"],
        "avoid_times": [],
    },
}


def get_student(student_id: str) -> dict | None:
    """학번으로 학생 정보 조회"""
    return STUDENTS.get(student_id)


def get_all_students() -> dict:
    """전체 학생 목록 반환"""
    return STUDENTS
