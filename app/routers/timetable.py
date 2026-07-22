from fastapi import APIRouter

router = APIRouter()

@router.get("/mock-courses", summary="프론트엔드 화면 테스트용 임시 과목 리스트")
def get_mock_courses():
    return {
        "status": "success",
        "data": [
            {
              "offering_id": 101,
              "course_id": "AISW001",
              "title": "운영체제",
              "credit": 3.0,
              "program_type": "MAJOR", 
              "professor": "김한신 교수",
              "schedules": [
                {"day": "월", "start_time": "09:00", "end_time": "10:30", "classroom": "공학관 301호"},
                {"day": "수", "start_time": "09:00", "end_time": "10:30", "classroom": "공학관 301호"}
              ],
              "keywords": ["OS", "시스템", "전공필수"]
            },
            {
              "offering_id": 102,
              "course_id": "AISW002",
              "title": "인공지능 특화 전공 세미나",
              "credit": 3.0,
              "program_type": "SPECIALIZED",
              "professor": "이AI 교수",
              "schedules": [
                {"day": "화", "start_time": "13:30", "end_time": "15:00", "classroom": "인문관 202호"}
              ],
              "keywords": ["딥러닝", "특화전공", "AI"]
            }
        ]
    }