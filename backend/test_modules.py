"""테스트 스크립트 - API 키 없이도 각 모듈 동작 확인 가능"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.data.students import get_student, get_all_students
from core.data.courses import get_required_remaining, get_available_courses, COURSES
from core.data.notices import NOTICES
from core.data.academic_schedule import ACADEMIC_SCHEDULE
from core.scheduler import generate_timetable, _has_time_conflict, _fits_preferences
from core.notifications import (
    search_notices,
    filter_notices_by_keywords,
    get_upcoming_alerts,
    check_deadline_triggers,
    register_keyword_alert,
)


def test_students():
    print("=" * 50)
    print("TEST: 학생 데이터")
    print("=" * 50)
    students = get_all_students()
    for sid, s in students.items():
        print(f"  {sid} {s['name']} - {s['department']} ({s['completed_credits']}/{s['required_credits']}학점)")

    student = get_student("20210001")
    remaining = get_required_remaining(student)
    print(f"\n  김정보 미이수 필수과목: {len(remaining)}개")
    for c in remaining:
        print(f"    - {c['code']} {c['name']}")


def test_timetable():
    print("\n" + "=" * 50)
    print("TEST: 시간표 시뮬레이션")
    print("=" * 50)

    student = get_student("20210001")
    schedules = generate_timetable(student, max_schedules=3)
    print(f"  추천 시간표: {len(schedules)}개")

    for i, s in enumerate(schedules, 1):
        print(f"\n  추천 {i} (총 {s['total_credits']}학점)")
        if s.get("missing_required"):
            print(f"    미배치 필수: {s['missing_required']}")
        for c in s["courses"]:
            times = ", ".join(f"{d} {start}~{end}" for d, start, end in c["time_slots"])
            print(f"    - {c['code']} {c['name']} [{times}]")


def test_time_conflict():
    print("\n" + "=" * 50)
    print("TEST: 시간 충돌 체크")
    print("=" * 50)

    # CS201 (화 13:00~14:30, 목 13:00~14:30) vs CS203 (화 15:00~16:30, 목 15:00~16:30)
    a = COURSES["CS201"]
    b = COURSES["CS203"]
    print(f"  {a['code']} vs {b['code']}: 충돌={_has_time_conflict(a, b)}")

    # CS201 (화 13:00~14:30) vs MATH101 (화 13:00~14:30)
    c = COURSES["MATH101"]
    print(f"  {a['code']} vs {c['code']}: 충돌={_has_time_conflict(a, c)}")

    # AISW301 (월 10:00~11:30) vs CS102 (월 10:00~11:30)
    d = COURSES["AISW301"]
    e = COURSES["CS102"]
    print(f"  {d['code']} vs {e['code']}: 충돌={_has_time_conflict(d, e)}")


def test_preferences():
    print("\n" + "=" * 50)
    print("TEST: 선호 시간대 필터링")
    print("=" * 50)

    student = get_student("20210001")
    preferred_days = student["preferred_days"]
    preferred_times = student["preferred_times"]
    avoid_times = student["avoid_times"]

    print(f"  선호 요일: {preferred_days}")
    print(f"  선호 시간: {preferred_times}")
    print(f"  피하는 시간: {avoid_times}")

    for code, course in list(COURSES.items())[:10]:
        fits = _fits_preferences(course, preferred_days, preferred_times, avoid_times)
        marker = "✓" if fits else "✗"
        print(f"  [{marker}] {code} {course['name']}")


def test_keyword_search():
    print("\n" + "=" * 50)
    print("TEST: 키워드 매칭")
    print("=" * 50)

    queries = ["장학금", "AI 공모전", "특화 전공", "인턴 취업"]
    for q in queries:
        results = search_notices(q)
        print(f"\n  검색어: '{q}' → {len(results)}건")
        for r in results[:3]:
            print(f"    - [{r['date']}] {r['title']} (매칭키워드: {r['matched_keywords']})")


def test_academic_schedule():
    print("\n" + "=" * 50)
    print("TEST: 학사일정 알림")
    print("=" * 50)

    alerts = get_upcoming_alerts(365)  # 1년 내
    print(f"  향후 1년 내 일정: {len(alerts)}건")
    for a in alerts:
        print(f"  [{a['urgency']}] {a['alert_message']}")
        if a.get("prerequisite_warning"):
            print(f"         {a['prerequisite_warning']}")


def test_deadline_triggers():
    print("\n" + "=" * 50)
    print("TEST: 마감 트리거")
    print("=" * 50)

    student = get_student("20210001")
    triggers = check_deadline_triggers(student)
    print(f"  현재 관련 트리거: {len(triggers)}건")
    for t in triggers:
        print(f"  [{t['status']}] {t['message']}")


def test_keyword_registration():
    print("\n" + "=" * 50)
    print("TEST: 키워드 등록")
    print("=" * 50)

    result = register_keyword_alert("20210001", ["장학금", "AI", "인턴", "공모전"])
    print(f"  {result['message']}")
    for n in result["existing_matches"][:3]:
        print(f"    - {n['title']}")


if __name__ == "__main__":
    print("🎓 졸업을 부탁해 - 모듈 테스트\n")

    test_students()
    test_timetable()
    test_time_conflict()
    test_preferences()
    test_keyword_search()
    test_academic_schedule()
    test_deadline_triggers()
    test_keyword_registration()

    print("\n" + "=" * 50)
    print("✅ 모든 테스트 완료!")
    print("=" * 50)
