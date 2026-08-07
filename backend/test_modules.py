"""테스트 스크립트 - CSV 기반 실제 데이터로 각 모듈 동작 확인"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from core.data.csv_loader import load_courses, load_notices, load_academic_schedule
from core.data.students import get_student, get_all_students
from core.data.courses import get_required_remaining, get_available_courses, get_course, _ensure_loaded as _ensure_courses
from core.data.notices import NOTICES, get_all_notices
from core.data.academic_schedule import ACADEMIC_SCHEDULE, get_all_schedules
from core.scheduler import generate_timetable, _has_time_conflict, _fits_preferences
from core.notifications import (
    search_notices,
    filter_notices_by_keywords,
    get_upcoming_alerts,
    check_deadline_triggers,
    register_keyword_alert,
)


def test_csv_loading():
    print("=" * 60)
    print("TEST: CSV 데이터 로딩")
    print("=" * 60)

    t0 = time.time()
    courses = load_courses()
    t1 = time.time()
    print(f"  과목: {len(courses)}개 로드 ({t1-t0:.3f}초)")

    # 타입 분포
    type_counts = {}
    for c in courses.values():
        t = c["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {t}: {cnt}개")

    # 시간표 있는 과목 수
    with_schedule = sum(1 for c in courses.values() if c.get("time_slots"))
    print(f"  시간표 있는 과목: {with_schedule}개")

    # courses 모듈도 초기화
    _ensure_courses()

    t0 = time.time()
    notices = load_notices()
    t1 = time.time()
    print(f"\n  공지사항: {len(notices)}개 로드 ({t1-t0:.3f}초)")

    t0 = time.time()
    schedule = load_academic_schedule()
    t1 = time.time()
    print(f"  학사일정: {len(schedule)}개 로드 ({t1-t0:.3f}초)")


def test_students():
    print("\n" + "=" * 60)
    print("TEST: 학생 데이터")
    print("=" * 60)
    students = get_all_students()
    for sid, s in students.items():
        remaining = get_required_remaining(s)
        available = get_available_courses(s)
        print(f"  {sid} {s['name']} - {s['department']} ({s['completed_credits']}/{s['required_credits']}학점)")
        print(f"    미이수 필수: {len(remaining)}개, 수강가능: {len(available)}개")


def test_courses():
    print("\n" + "=" * 60)
    print("TEST: 과목 데이터 (CSV 기반)")
    print("=" * 60)

    _ensure_courses()
    from core.data.courses import COURSES as courses_dict

    # 샘플 과목 출력
    sample_codes = list(courses_dict.keys())[:10]
    for code in sample_codes:
        c = courses_dict[code]
        times = ", ".join(f"{d} {s}~{e}" for d, s, e in c.get("time_slots", []))
        print(f"  {c['code']} {c['name']} [{c['type']}] ({c['credits']}학점) {times}")

    # 전체 통계
    total_credits = sum(c["credits"] for c in courses_dict.values())
    print(f"\n  전체 과목: {len(courses_dict)}개, 전체 학점: {total_credits}")


def test_same_name_completed_course_is_not_recommended():
    import core.data.courses as course_module

    original_courses = course_module.COURSES
    try:
        course_module.COURSES = {
            "SH101": {"code": "SH101", "name": "알고리즘", "credits": 3, "type": "전공선택", "offerings": []},
            "SH999": {"code": "SH999", "name": "알고리즘", "credits": 3, "type": "전공선택", "offerings": []},
            "SH200": {"code": "SH200", "name": "데이터베이스", "credits": 3, "type": "전공선택", "offerings": []},
        }

        student = {
            "student_id": "20210001",
            "department": "AISW",
            "completed_courses": ["SH101"],
            "in_progress_courses": []
        }
        available = get_available_courses(student)
        codes = [course["code"] for course in available]

        assert "SH999" not in codes
        assert "SH200" in codes
    finally:
        course_module.COURSES = original_courses


def test_chapel_satisfied_rule():
    import core.data.courses as course_module

    original_courses = course_module.COURSES
    try:
        # 가상의 개설 과목 등록
        # KY100: 이수 완료한 채플 (학점 0.5)
        # KY201: 미이수한 채플 (학점 0.5)
        course_module.COURSES = {
            "KY100": {"code": "KY100", "name": "채플", "credits": 0.5, "type": "교양필수", "offerings": []},
            "KY201": {"code": "KY201", "name": "채플", "credits": 0.5, "type": "교양필수", "offerings": []},
            "SH200": {"code": "SH200", "name": "데이터베이스", "credits": 3, "type": "전공선택", "offerings": []},
        }

        # 1. 0.5학점 채플을 4번 이수한 학생 (과목명이 '채플')
        student_satisfied = {
            "completed_courses": ["KY100", "KY102", "KY103", "KY104"],
            "completed_course_names": ["채플", "채플", "채플", "채플"],
            "completed_courses_detail": [
                {"code": "KY100", "name": "채플", "credits": 0.5},
                {"code": "KY102", "name": "채플", "credits": 0.5},
                {"code": "KY103", "name": "채플", "credits": 0.5},
                {"code": "KY104", "name": "채플", "credits": 0.5},
            ],
            "in_progress_courses": [],
            "department": "AISW"
        }
        available_satisfied = get_available_courses(student_satisfied)
        satisfied_codes = [c["code"] for c in available_satisfied]
        
        # 채플 요건을 만족했으므로 미이수한 KY201(채플)도 추천에서 빠져야 함
        assert "KY201" not in satisfied_codes
        assert "SH200" in satisfied_codes

        # 2. 채플을 3번 이수한 학생
        student_unsatisfied = {
            "completed_courses": ["KY100", "KY102", "KY103"],
            "completed_course_names": ["채플", "채플", "채플"],
            "completed_courses_detail": [
                {"code": "KY100", "name": "채플", "credits": 0.5},
                {"code": "KY102", "name": "채플", "credits": 0.5},
                {"code": "KY103", "name": "채플", "credits": 0.5},
            ],
            "in_progress_courses": [],
            "department": "AISW"
        }
        available_unsatisfied = get_available_courses(student_unsatisfied)
        unsatisfied_codes = [c["code"] for c in available_unsatisfied]
        
        # 채플 요건을 만족하지 못했으므로 미이수한 KY201(채플)은 추천에 포함되어야 함
        assert "KY201" in unsatisfied_codes
        assert "SH200" in unsatisfied_codes
    finally:
        course_module.COURSES = original_courses


def test_special_track_credit_only_counts_special_electives():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from backend.app.routers.graduation import _calculate_track_credits

    history_details = [
        {"history_id": 1, "course_code": "SP1", "grade": "A", "earned_credit": 3, "course_type": "특화전공 전선"},
        {"history_id": 2, "course_code": "SP2", "grade": "A", "earned_credit": 3, "course_type": "전공선택"},
        {"history_id": 3, "course_code": "CV1", "grade": "A", "earned_credit": 3, "course_type": "융합전공 전선"},
        {"history_id": 4, "course_code": "SP3", "grade": "F", "earned_credit": 3, "course_type": "특화전공 전선"},
    ]

    spec_earned, conv_earned = _calculate_track_credits(
        history_details,
        forfeited_ids=set(),
        spec_track_name="인지감성컴퓨팅 특화전공",
        conv_major_name="융합전공",
        courses_db={},
    )

    assert spec_earned == 3
    assert conv_earned == 3


def test_timetable():
    print("\n" + "=" * 60)
    print("TEST: 시간표 시뮬레이션 (CSV 기반)")
    print("=" * 60)

    student = get_student("20210001")
    t0 = time.time()
    schedules = generate_timetable(student, max_schedules=3)
    t1 = time.time()
    print(f"  추천 시간표: {len(schedules)}개 ({t1-t0:.3f}초)")

    for i, s in enumerate(schedules, 1):
        print(f"\n  추천 {i} (총 {s['total_credits']}학점)")
        if s.get("missing_required"):
            print(f"    미배치 필수: {s['missing_required']}")
        for c in s["courses"]:
            times = ", ".join(f"{d} {start}~{end}" for d, start, end in c.get("time_slots", []))
            print(f"    - {c['code']} {c['name']} [{times}] ({c['professor']})")


def test_time_conflict():
    print("\n" + "=" * 60)
    print("TEST: 시간 충돌 체크")
    print("=" * 60)

    _ensure_courses()
    from core.data.courses import COURSES as courses_dict

    # 시간표가 있는 과목들만 테스트
    courses_with_time = [c for c in courses_dict.values() if c.get("time_slots")]
    if len(courses_with_time) < 2:
        print("  테스트 가능한 과목이 부족합니다.")
        return

    a = courses_with_time[0]
    b = courses_with_time[1]
    result = _has_time_conflict(a, b)
    print(f"  {a['code']} vs {b['code']}: 충돌={result}")


def test_preferences():
    print("\n" + "=" * 60)
    print("TEST: 선호 시간대 필터링")
    print("=" * 60)

    _ensure_courses()
    from core.data.courses import COURSES as courses_dict

    student = get_student("20210001")
    preferred_days = student["preferred_days"]
    preferred_times = student["preferred_times"]
    avoid_times = student["avoid_times"]

    print(f"  선호 요일: {preferred_days}")
    print(f"  선호 시간: {preferred_times}")
    print(f"  피하는 시간: {avoid_times}")

    # 시간표가 있는 과목 중 처음 10개
    courses_with_time = [c for c in courses_dict.values() if c.get("time_slots")][:10]
    for course in courses_with_time:
        fits = _fits_preferences(course, preferred_days, preferred_times, avoid_times)
        marker = "✓" if fits else "✗"
        times = ", ".join(f"{d} {s}~{e}" for d, s, e in course.get("time_slots", []))
        print(f"  [{marker}] {course['code']} {course['name']} [{times}]")


def test_keyword_search():
    print("\n" + "=" * 60)
    print("TEST: 키워드 매칭 (CSV 기반)")
    print("=" * 60)

    queries = ["장학금", "공모전", "특화전공", "수강신청"]
    for q in queries:
        results = search_notices(q)
        print(f"\n  검색어: '{q}' → {len(results)}건")
        for r in results[:3]:
            print(f"    - [{r['date']}] {r['title'][:60]} (매칭키워드: {r['matched_keywords']})")


def test_academic_schedule():
    print("\n" + "=" * 60)
    print("TEST: 학사일정 알림 (CSV 기반)")
    print("=" * 60)

    alerts = get_upcoming_alerts(365)
    print(f"  향후 1년 내 일정: {len(alerts)}건")
    for a in alerts[:10]:
        print(f"  [{a['urgency']}] {a['alert_message']}")
        if a.get("prerequisite_warning"):
            print(f"         {a['prerequisite_warning']}")


def test_deadline_triggers():
    print("\n" + "=" * 60)
    print("TEST: 마감 트리거")
    print("=" * 60)

    student = get_student("20210001")
    triggers = check_deadline_triggers(student)
    print(f"  현재 관련 트리거: {len(triggers)}건")
    for t in triggers:
        print(f"  [{t['status']}] {t['message']}")


def test_keyword_registration():
    print("\n" + "=" * 60)
    print("TEST: 키워드 등록")
    print("=" * 60)

    result = register_keyword_alert("20210001", ["장학금", "AI", "공모전"])
    print(f"  {result['message']}")
    for n in result["existing_matches"][:5]:
        print(f"    - {n['title'][:60]}")
def test_chatbot_chapel_and_taken_courses():
    print("=" * 60)
    print("TEST: 챗봇 채플 및 기이수 과목명 필터링 검증")
    print("=" * 60)

    from core.chatbot import _count_chapel_completed, _get_unfinished_track_common

    # 채플을 8번 이수한 가상 학생
    student_satisfied = {
        "student_id": "9999",
        "completed_courses": ["KY101", "KY201", "KY304", "KY509", "KY901", "KY902", "KY903", "KY904"],
        "completed_course_names": ["채플", "채플", "채플", "채플", "채플", "채플", "채플", "채플"],
        "completed_courses_detail": [
            {"code": "KY101", "name": "채플", "credits": 0.5},
            {"code": "KY201", "name": "채플", "credits": 0.5},
            {"code": "KY304", "name": "채플", "credits": 0.5},
            {"code": "KY509", "name": "채플", "credits": 0.5},
            {"code": "KY901", "name": "채플", "credits": 0.5},
            {"code": "KY902", "name": "채플", "credits": 0.5},
            {"code": "KY903", "name": "채플", "credits": 0.5},
            {"code": "KY904", "name": "채플", "credits": 0.5},
        ]
    }

    # 채플을 1번 이수한 가상 학생
    student_unsatisfied = {
        "student_id": "8888",
        "completed_courses": ["KY101"],
        "completed_course_names": ["채플"],
        "completed_courses_detail": [
            {"code": "KY101", "name": "채플", "credits": 0.5}
        ]
    }

    sat_info = _count_chapel_completed(student_satisfied)
    unsat_info = _count_chapel_completed(student_unsatisfied)

    print(f"  8회 이수 학생 채플 카운트: {sat_info['completed_count']} (만족 여부: {sat_info['is_satisfied']})")
    print(f"  1회 이수 학생 채플 카운트: {unsat_info['completed_count']} (만족 여부: {unsat_info['is_satisfied']})")

    assert sat_info["is_satisfied"] == True
    assert unsat_info["is_satisfied"] == False

    # 웹프로그래밍을 이미 이수한 학생 (과목 코드 FLOW-050)
    student_web = {
        "student_id": "7777",
        "completed_courses": ["FLOW-050"],
        "completed_course_names": ["웹프로그래밍"]
    }

    unfinished_commons = _get_unfinished_track_common(student_web, "2학기")
    web_unfinished = [c for c in unfinished_commons["all_unfinished"] if c["name"] == "웹프로그래밍"]

    print(f"  웹프로그래밍(FLOW-050) 기이수 학생의 계공 미이수 목록 내 웹프로그래밍 포함 여부: {len(web_unfinished) > 0}")
    assert len(web_unfinished) == 0, "이미 과목명 '웹프로그래밍'으로 이수했으므로 미이수 계공에 나타나지 않아야 합니다."

    print("  [✓] 챗봇 검증 테스트 완료!")


def test_christianity_course_satisfied():
    print("=" * 60)
    print("TEST: 기독교/성서 계열 중복 이수 예외 처리 검증")
    print("=" * 60)

    from core.data.courses import get_available_courses

    # '성서와여성'을 기이수한 학생
    student_bible = {
        "student_id": "6666",
        "enrolled_year": 2024,
        "department": "AI.SW학",
        "major_tracks": ["AI.SW학 본전공"],
        "completed_courses": ["KY894"],
        "completed_course_names": ["성서와여성"],
        "in_progress_courses": [],
        "in_progress_course_names": [],
        "required_credits": 130,
        "completed_credits": 2,
        "gpa": 4.0,
        "preferred_days": ["월", "화", "수", "목", "금"],
        "preferred_times": ["09:00-12:00", "13:00-18:00"],
        "avoid_times": []
    }

    avail = get_available_courses(student_bible, "2학기")
    
    # 성서 관련 다른 과목인 '성서와평화'가 추천 목록에 등장하는지 확인
    bible_peace_avail = [c for c in avail if "성서" in c.get("name", "") or "기독교" in c.get("name", "")]
    
    print(f"  성서와여성 기이수 학생의 수강 가능 추천 목록 내 기독교/성서 과목 존재 여부: {len(bible_peace_avail) > 0}")
    assert len(bible_peace_avail) == 0, "이미 '성서와여성'을 이수했으므로 다른 성서/기독교 과목이 추천되지 않아야 합니다."
    
    print("  [✓] 기독교 중복 이수 배제 검증 완료!")


def test_chatbot_preferences():
    print("=" * 60)
    print("TEST: 챗봇 선호도 및 요일 분석 검증")
    print("=" * 60)

    from core.chatbot import _extract_preference_from_message

    tests = [
        ("월, 수 공강 만들어줘", {"remove_days": ["월", "수"]}),
        ("화, 목, 금만 학교 갈래", {"set_days": ["화", "목", "금"]}),
        ("월요일만 빼고 화목금 수업 들을래", {"remove_days": ["월"], "set_days": ["화", "목", "금"]}),
        ("오전 수업 선호해", {"prefer_morning": True}),
        ("오전 수업은 피하고 싶어", {"avoid_morning": True}),
        ("오후 위주로 짜줘", {"prefer_afternoon": True}),
        ("오후는 안돼", {"avoid_afternoon": True}),
        ("월요일 공강하고 오전 선호해", {"remove_days": ["월"], "prefer_morning": True}),
    ]

    for msg, expected in tests:
        res = _extract_preference_from_message(msg)
        for k, v in expected.items():
            assert k in res, f"키 {k}가 결과에 없음. 메시지: {msg}, 결과: {res}"
            assert res[k] == v, f"키 {k}의 값이 불일치. 예상: {v}, 결과: {res[k]}. 메시지: {msg}"
        
        # 원치 않는 키가 추가로 존재하지 않는지 검증
        for k in res:
            if k not in expected and k in ["remove_days", "set_days", "avoid_morning", "prefer_morning", "prefer_afternoon", "avoid_afternoon"]:
                raise AssertionError(f"원치 않는 키 {k}가 결과에 포함됨. 메시지: {msg}, 결과: {res}")

    print("  [✓] 챗봇 선호도 분석 검증 완료!")


def test_multiple_sections_search():
    print("\n" + "=" * 60)
    print("TEST: 다중 분반 탐색 및 Fallback 매핑 검증")
    print("=" * 60)
    
    # 1. 테스트용 과목 설정
    course_as004 = {
        "code": "AS004",
        "name": "AI·SW수학",
        "type": "계열공통",
        "credits": 3,
        "professor": "대표교수",
        "room": "대표실",
        "time_slots": [("화", "09:00", "12:00")], 
        "offerings": [
            {
                "offering_id": 1,
                "section": "A",
                "professor": "교수A",
                "academic_year": "2026",
                "semester": "2학기",
                "time_slots": [("화", "09:00", "12:00")],
                "classrooms": ["공학관101"]
            },
            {
                "offering_id": 2,
                "section": "B",
                "professor": "교수B",
                "academic_year": "2026",
                "semester": "2학기",
                "time_slots": [("월", "09:00", "12:00")],
                "classrooms": ["공학관102"]
            }
        ]
    }
    course_dummy1 = {
        "code": "DUMMY01",
        "name": "더미과목1",
        "type": "계열공통",
        "credits": 3,
        "professor": "더미교수1",
        "room": "더미실1",
        "time_slots": [("수", "09:00", "12:00")], 
        "offerings": [
            {
                "offering_id": 3,
                "section": "A",
                "professor": "더미교수1",
                "academic_year": "2026",
                "semester": "2학기",
                "time_slots": [("수", "09:00", "12:00")],
                "classrooms": ["더미실1"]
            }
        ]
    }
    course_dummy2 = {
        "code": "DUMMY02",
        "name": "더미과목2",
        "type": "계열공통",
        "credits": 3,
        "professor": "더미교수2",
        "room": "더미실2",
        "time_slots": [("목", "09:00", "12:00")], 
        "offerings": [
            {
                "offering_id": 4,
                "section": "A",
                "professor": "더미교수2",
                "academic_year": "2026",
                "semester": "2학기",
                "time_slots": [("목", "09:00", "12:00")],
                "classrooms": ["더미실2"]
            }
        ]
    }
    
    # 2. 테스트용 학생 설정 - 화요일 공강 원하는 학생 (화요일 기피)
    student = {
        "student_id": "test_student_1",
        "department": "AISW",
        "completed_courses": [],
        "in_progress_courses": [],
        "preferred_days": ["월", "수", "목", "금"],
        "preferred_times": [],
        "avoid_times": [],
        "target_semester": "2026-2학기",
        "chatbot_recommended_courses": ["AS004", "DUMMY01", "DUMMY02"]
    }
    
    available = [course_as004, course_dummy1, course_dummy2]
    from core.scheduler import _generate_timetable_with_preferences
    
    # 1차 검증: 화요일 공강이므로 화요일인 A반 대신 월요일인 B반으로 매핑되어야 함.
    results = _generate_timetable_with_preferences(
        student,
        required_remaining=[],
        available=available,
        preferred_days=student["preferred_days"],
        preferred_times=student["preferred_times"],
        avoid_times=student["avoid_times"],
        max_schedules=1,
        max_candidates=10,
        target_credits=9
    )
    
    assert len(results) > 0, "시간표가 생성되지 않았습니다."
    
    # AS004 과목을 찾음
    assigned_course = next((c for c in results[0]["courses"] if c["code"] == "AS004"), None)
    assert assigned_course is not None, "AS004 과목이 시간표에 포함되지 않았습니다."
    assert assigned_course["section"] == "B", f"B분반이 매핑되어야 하는데 {assigned_course.get('section')}가 매핑되었습니다."
    assert assigned_course["professor"] == "교수B", f"교수B여야 하는데 {assigned_course.get('professor')}입니다."
    assert assigned_course["time_slots"] == [("월", "09:00", "12:00")], f"월요일 시간표여야 하는데 {assigned_course.get('time_slots')}입니다."
    
    print("  [✓] 대체 분반 탐색 및 자동 매핑 성공 (화요일 공강 -> 월요일 B분반 자동 배정)")
    
    # 3. 2차 검증: 만약 모든 분반이 충돌하더라도 과목 배정이 누락되지 않고 첫 번째 분반(A반)으로 매핑되어야 함.
    student_all_conflict = {
        "student_id": "test_student_2",
        "department": "AISW",
        "completed_courses": [],
        "in_progress_courses": [],
        "preferred_days": ["수", "목", "금"],
        "preferred_times": [],
        "avoid_times": [],
        "target_semester": "2026-2학기",
        "chatbot_recommended_courses": ["AS004", "DUMMY01", "DUMMY02"]
    }
    
    results_conflict = _generate_timetable_with_preferences(
        student_all_conflict,
        required_remaining=[],
        available=available,
        preferred_days=student_all_conflict["preferred_days"],
        preferred_times=student_all_conflict["preferred_times"],
        avoid_times=student_all_conflict["avoid_times"],
        max_schedules=1,
        max_candidates=10,
        target_credits=9
    )
    
    assert len(results_conflict) > 0, "모든 분반 충돌 시 시간표가 누락되었습니다."
    assigned_course_conflict = next((c for c in results_conflict[0]["courses"] if c["code"] == "AS004"), None)
    assert assigned_course_conflict is not None, "모든 분반 충돌 시 AS004 과목이 시간표에서 누락되었습니다."
    assert assigned_course_conflict["section"] in ["A", ""], f"Fallback으로 첫 번째 분반이 배정되어야 하는데 {assigned_course_conflict.get('section')}가 배정되었습니다."
    
    print("  [✓] 모든 분반 충돌 시 누락 방지 및 Fallback 매핑 성공")


def test_universal_parsing():
    print("\n" + "=" * 60)
    print("TEST: 전역 복합 시간표 문자열 파싱 (Universal Parsing) 검증")
    print("=" * 60)
    
    test_cases = [
        ("화(09:30~10:45)목(11:00~12:15)", [("화", "09:30", "10:45"), ("목", "11:00", "12:15")]),
        ("화요일(09:30~10:45)목요일(11:00~12:15)", [("화", "09:30", "10:45"), ("목", "11:00", "12:15")]),
        ("월(13:00~14:15), 수요일(13:00~14:15)", [("월", "13:00", "14:15"), ("수", "13:00", "14:15")]),
    ]
    
    import parse_courses
    for raw_time, expected in test_cases:
        parsed = parse_courses.parse_time(raw_time)
        assert len(parsed) == len(expected), f"파싱 결과 개수 불일치. 입력: {raw_time}, 결과: {parsed}"
        for i, (day, start, end) in enumerate(parsed):
            assert day == expected[i][0], f"요일 불일치. 입력: {raw_time}, 결과: {day}"
            assert start == expected[i][1], f"시작시간 불일치. 입력: {raw_time}, 결과: {start}"
            assert end == expected[i][2], f"종료시간 불일치. 입력: {raw_time}, 결과: {end}"
            
    print("  [✓] parse_courses.parse_time 전역 파싱 검증 완료")

    import etl_generate
    etl_test_cases = [
        ("화(09:30~10:45)목(11:00~12:15)", [("화", "09:30:00", "10:45:00"), ("목", "11:00:00", "12:15:00")]),
        ("월요일(13:00~14:15)수요일(13:00~14:15)", [("월", "13:00:00", "14:15:00"), ("수", "13:00:00", "14:15:00")]),
    ]
    for raw_time, expected in etl_test_cases:
        parsed = etl_generate.parse_time_string(raw_time)
        assert len(parsed) == len(expected), f"etl 파싱 결과 개수 불일치. 입력: {raw_time}, 결과: {parsed}"
        for i, item in enumerate(parsed):
            assert item["day_of_week"] == expected[i][0], f"etl 요일 불일치. 입력: {raw_time}, 결과: {item['day_of_week']}"
            assert item["start_time"] == expected[i][1], f"etl 시작 불일치. 입력: {raw_time}, 결과: {item['start_time']}"
            assert item["end_time"] == expected[i][2], f"etl 종료 불일치. 입력: {raw_time}, 결과: {item['end_time']}"

    print("  [✓] etl_generate.parse_time_string 전역 파싱 검증 완료")


if __name__ == "__main__":
    print("🎓 졸업을 부탁해 - CSV 기반 모듈 테스트\n")

    test_csv_loading()
    test_students()
    test_courses()
    test_same_name_completed_course_is_not_recommended()
    test_chapel_satisfied_rule()
    test_chatbot_chapel_and_taken_courses()
    test_christianity_course_satisfied()
    test_chatbot_preferences()
    test_timetable()
    test_time_conflict()
    test_preferences()
    test_keyword_search()
    test_academic_schedule()
    test_deadline_triggers()
    test_keyword_registration()
    test_multiple_sections_search()
    test_universal_parsing()

    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)
