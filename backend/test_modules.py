"""테스트 스크립트 - CSV 기반 실제 데이터로 각 모듈 동작 확인"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

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


if __name__ == "__main__":
    print("🎓 졸업을 부탁해 - CSV 기반 모듈 테스트\n")

    test_csv_loading()
    test_students()
    test_courses()
    test_timetable()
    test_time_conflict()
    test_preferences()
    test_keyword_search()
    test_academic_schedule()
    test_deadline_triggers()
    test_keyword_registration()

    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)
