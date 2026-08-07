"""졸업을 부탁해 (GradManager) - 메인 진입점

모든 모듈을 통합하여 실행하는 CLI 인터페이스입니다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.data.students import get_student, get_all_students
from core.data.courses import (
    get_required_remaining,
    get_available_courses,
    get_required_remaining_by_track,
    get_graduation_credit_summary,
    validate_completed_categories,
    get_interest_matching_courses,
)
from core.scheduler import generate_timetable
from core.notifications import (
    search_notices,
    register_keyword_alert,
    get_keyword_alerts,
    remove_keyword_alert,
    check_keyword_alert_deadlines,
    get_upcoming_alerts,
    check_deadline_triggers,
    format_notification,
)


def print_header():
    print("=" * 60)
    print("  🎓 졸업을 부탁해 (GradManager) - AI 졸업 도우미")
    print("=" * 60)


def print_student_status(student: dict):
    remaining_required = get_required_remaining(student)
    credits_needed = student["required_credits"] - student["completed_credits"]

    print(f"\n📋 {student['name']} 학생의 이수 현황")
    print(f"  학과: {student['department']} | 전공: {', '.join(student['major_tracks'])}")
    print(f"  학점: {student['completed_credits']}/{student['required_credits']} ({credits_needed}학점 부족)")
    print(f"  GPA: {student['gpa']} | 마일리지: {student['mileage']}")

    if remaining_required:
        print(f"\n  ⚠️ 미이수 전공 필수 ({len(remaining_required)}과목):")
        for c in remaining_required:
            print(f"    - {c['code']} {c['name']} ({c['credits']}학점)")
    else:
        print("  ✅ 전공 필수 과목 모두 이수 완료!")


def print_graduation_summary(student: dict):
    print(f"\n📊 이수구분별 졸업요건 현황")
    try:
        summary = get_graduation_credit_summary(student)
        for cat, info in summary.items():
            if info["required"] > 0:
                status = "✅ 충족" if info["remaining"] == 0 else f"⚠️ {info['remaining']}학점 부족"
                print(f"  {cat}: {info['completed']}/{info['required']}학점 ({status})")
            elif info["completed"] > 0:
                print(f"  {cat}: {info['completed']}학점 이수 (요건 없음)")
    except Exception as e:
        print(f"  졸업요건 조회 실패: {e}")


def print_validation_result(student: dict):
    print(f"\n🔍 이수구분 검증 결과")
    try:
        result = validate_completed_categories(student)
        summary = result["category_summary"]
        print(f"  이수구분별 학점 요약:")
        for cat, credits in summary.items():
            if credits > 0:
                print(f"    {cat}: {credits}학점")

        mismatched = result["mismatched_courses"]
        if mismatched:
            print(f"\n  ⚠️ 이수구분 불일치 과목 ({len(mismatched)}과목):")
            for m in mismatched:
                print(f"    - {m['code']} {m['name']}: 기준 '{m['curriculum_type']}' vs 코드 기준 '{m['inferred_type']}'")
        else:
            print(f"  ✅ 모든 과목의 이수구분이 일치합니다.")
    except Exception as e:
        print(f"  검증 실패: {e}")


def print_timetable_schedules(schedules: list[dict]):
    if not schedules:
        print("\n추천 가능한 시간표가 없습니다.")
        return

    print(f"\n📅 시간표 추천 ({len(schedules)}개)")
    for i, schedule in enumerate(schedules, 1):
        print(f"\n  추천 {i} (총 {schedule['total_credits']}학점)")
        if schedule.get("missing_required"):
            print(f"    ⚠️ 미배치 필수과목: {', '.join(schedule['missing_required'])}")

        for course in schedule["courses"]:
            times = ", ".join(f"{d} {s}~{e}" for d, s, e in course["time_slots"])
            required_mark = "🔴" if course["code"] in schedule.get("included_required", []) else "  "
            print(f"    {required_mark} {course['code']} {course['name']} [{times}] ({course.get('professor', '')})")


def run_cli():
    print_header()

    students = get_all_students()
    print("\n등록된 학생 목록:")
    for sid, s in students.items():
        print(f"  - {sid} {s['name']}")

    student_id = input("\n학번을 입력하세요: ").strip()
    student = get_student(student_id)

    if not student:
        print("해당 학생을 찾을 수 없습니다.")
        return

    print_student_status(student)
    print_graduation_summary(student)
    print_validation_result(student)

    existing_alerts = get_keyword_alerts(student_id)
    keyword_prefs = student.get("keyword_preferences", [])
    all_keywords = list(set(keyword_prefs + existing_alerts))
    print(f"\n현재 설정된 키워드: {', '.join(all_keywords) if all_keywords else '없음'}")

    custom_keywords = input("알림 키워드를 추가하세요 (쉼표 구분, 엔터 시 건너뜀): ").strip()
    if custom_keywords:
        keywords = [kw.strip() for kw in custom_keywords.split(",")]
        result = register_keyword_alert(student_id, keywords)
        print(f"  → {result['message']}")

    alerts = get_upcoming_alerts(30)
    if alerts:
        print(f"\n🔔 향후 30일 이내 학사일정 ({len(alerts)}건)")
        for alert in alerts[:5]:
            print(f"  [{alert['urgency']}] {alert['alert_message']}")
            if alert.get("prerequisite_warning"):
                print(f"         {alert['prerequisite_warning']}")

    triggers = check_deadline_triggers(student)
    if triggers:
        print(f"\n⚡ 현재 관련 알림 ({len(triggers)}건)")
        for t in triggers:
            print(f"  - [{t['status']}] {t['message']}")

    keyword_reminders = check_keyword_alert_deadlines(student_id)
    if keyword_reminders:
        print(f"\n🔑 키워드 알림 리마인더 ({len(keyword_reminders)}건)")
        for r in keyword_reminders[:5]:
            print(f"  [{r['urgency']}] {r['message']}")

    try:
        track_remaining = get_required_remaining_by_track(student)
        if track_remaining:
            print(f"\n📚 트랙별 미이수 필수 과목 ({len(track_remaining)}과목):")
            for c in track_remaining[:10]:
                print(f"  - {c['code']} {c['name']} ({c['credits']}학점)")
    except Exception:
        pass

    print("\n💬 AI 조교와 대화하기 (종료: 'quit')")
    from core.chatbot import chat

    history = []
    while True:
        user_input = input("\n나: ").strip()
        if user_input.lower() in ("quit", "exit", "종료"):
            print("대화를 종료합니다. 안녕히 가세요! 🎓")
            break
        if not user_input:
            continue

        result = chat(user_input, student_id=student_id, history=history)
        response = result["message"]
        print(f"\n그레듀: {response}")

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})

        if len(history) > 20:
            history = history[-10:]


if __name__ == "__main__":
    run_cli()
