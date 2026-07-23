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
            "KY677", "KY921", "KYC56", "KYC55", "KY217",
            "KY313", "KYC54", "KYC69", "KY410",
            "SH304", "SH317", "SH318", "SH312", "SH355",
            "SH402", "SH403", "SH354", "DS301", "FLOW-065",
            "KY696", "KYC88", "KYC89", "KY245", "KY755",
            "KY961", "KYA81", "KYC45", "KY304", "KY201"
        ],
        "in_progress_courses": ["SH328", "SH322"],
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
            "KY677", "KY921", "KYC56", "KYC55", "KY217",
            "KY313", "KYC54", "KYC69", "KY410",
            "SH304", "SH317", "SH318", "SH312", "SH355",
            "SH402", "SH354", "DS301", "KY696", "KYC88",
            "KYC89", "KY245", "KY755", "KY304", "KY201"
        ],
        "in_progress_courses": ["SH322", "SH328"],
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
