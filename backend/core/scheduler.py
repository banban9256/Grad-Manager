"""시간표 시뮬레이션 모듈 - 선호 시간대 기반 조합 알고리즘"""

from itertools import combinations

from .data.courses import COURSES, get_required_remaining, get_available_courses


def _time_to_minutes(time_str: str) -> int:
    """HH:MM 형식을 분으로 변환"""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def _has_time_conflict(course_a: dict, course_b: dict) -> bool:
    """두 과목이 시간이 겹치는지 확인"""
    for day_a, start_a, end_a in course_a["time_slots"]:
        for day_b, start_b, end_b in course_b["time_slots"]:
            if day_a != day_b:
                continue
            a_start = _time_to_minutes(start_a)
            a_end = _time_to_minutes(end_a)
            b_start = _time_to_minutes(start_b)
            b_end = _time_to_minutes(end_b)
            if a_start < b_end and b_start < a_end:
                return True
    return False


def _fits_preferences(course: dict, preferred_days: list[str], preferred_times: list[str], avoid_times: list[str]) -> bool:
    """과목이 사용자 선호 시간대에 맞는지 확인"""
    for day, start, end in course["time_slots"]:
        if day not in preferred_days:
            return False

        start_min = _time_to_minutes(start)
        end_min = _time_to_minutes(end)

        # 피하는 시간대 체크
        for avoid in avoid_times:
            if "~" in avoid:
                avoid_start_str, avoid_end_str = avoid.split("~")
                avoid_start = _time_to_minutes(avoid_start_str)
                avoid_end = _time_to_minutes(avoid_end_str)
                if start_min < avoid_end and avoid_start < end_min:
                    return False

        # 선호 시간대 체크 (하나라도 겹치면 OK)
        if preferred_times:
            in_preferred = False
            for pref in preferred_times:
                if "~" in pref:
                    pref_start_str, pref_end_str = pref.split("~")
                    pref_start = _time_to_minutes(pref_start_str)
                    pref_end = _time_to_minutes(pref_end_str)
                    if start_min < pref_end and pref_start < end_min:
                        in_preferred = True
                        break
            if not in_preferred:
                return False

    return True


def _score_schedule(schedule: list[dict], student: dict) -> float:
    """시간표 점수 계산 (높을수록 좋음)"""
    score = 0.0

    # 필수 과목 포함 시 보너스
    required = {c["code"] for c in get_required_remaining(student)}
    for course in schedule:
        if course["code"] in required:
            score += 10.0

    # 수강 가능한 과목 보너스
    available = {c["code"] for c in get_available_courses(student)}
    for course in schedule:
        if course["code"] in available:
            score += 5.0

    # 선호 시간대 매칭 보너스
    for course in schedule:
        if _fits_preferences(course, student["preferred_days"], student["preferred_times"], student.get("avoid_times", [])):
            score += 3.0

    # 학점 수 보너스 (많을수록 좋지만, 21학점 이상이면 감점)
    total_credits = sum(c["credits"] for c in schedule)
    score += total_credits * 1.0
    if total_credits > 21:
        score -= (total_credits - 21) * 2.0

    return score


def generate_timetable(student: dict, max_schedules: int = 3, max_candidates: int = 50) -> list[dict]:
    """
    학생의 선호 시간대와 남은 요건을 기반으로 시간표 조합을 생성합니다.

    알고리즘:
    1. 필수 미이수 과목을 우선 배치
    2. 수강 가능한 과목 풀에서 선호 시간대에 맞는 과목 선별
    3. 시간 충돌 없이 조합 탐색
    4. 점수 기반 상위 N개 시간표 반환
    """
    required_remaining = get_required_remaining(student)
    available = get_available_courses(student)

    preferred_days = student.get("preferred_days", ["월", "화", "수", "목", "금"])
    preferred_times = student.get("preferred_times", [])
    avoid_times = student.get("avoid_times", [])

    # 선호 시간대에 맞는 과목만 필터링
    preferred_available = [
        c for c in available
        if _fits_preferences(c, preferred_days, preferred_times, avoid_times)
    ]

    # 필수 과목 + 선호 과목 통합 풀
    course_pool = []
    seen_codes = set()

    # 필수 과목 먼저 (항상 포함)
    for c in required_remaining:
        if c["code"] not in seen_codes:
            course_pool.append(c)
            seen_codes.add(c["code"])

    # 선호 과목 추가
    for c in preferred_available:
        if c["code"] not in seen_codes:
            course_pool.append(c)
            seen_codes.add(c["code"])

    # 전체 수강 가능 과목도 추가 (선호에 없지만 넓은 탐색을 위해)
    for c in available:
        if c["code"] not in seen_codes:
            course_pool.append(c)
            seen_codes.add(c["code"])

    # 필수 과목 세트
    required_codes = {c["code"] for c in required_remaining}

    # 조합 생성 (3~5과목)
    candidates = []
    for size in range(3, min(6, len(course_pool) + 1)):
        for combo in combinations(course_pool, size):
            combo_list = list(combo)

            # 시간 충돌 체크
            has_conflict = False
            for i in range(len(combo_list)):
                for j in range(i + 1, len(combo_list)):
                    if _time_to_conflict(combo_list[i], combo_list[j]):
                        has_conflict = True
                        break
                if has_conflict:
                    break
            if has_conflict:
                continue

            # 학점 합계 체크 (최대 21학점)
            total_credits = sum(c["credits"] for c in combo_list)
            if total_credits > 21 or total_credits < 9:
                continue

            # 필수 과목 포함 여부 기록
            included_required = [c["code"] for c in combo_list if c["code"] in required_codes]

            schedule = {
                "courses": combo_list,
                "total_credits": total_credits,
                "included_required": included_required,
                "missing_required": list(required_codes - set(included_required)),
            }
            candidates.append(schedule)

            if len(candidates) >= max_candidates * 10:
                break

    # 점수 기반 정렬
    candidates.sort(key=lambda s: _score_schedule(s["courses"], student), reverse=True)

    # 중복 제거 (과목 구성이 같은 시간표 제거)
    unique = []
    seen_combos = set()
    for c in candidates:
        combo_key = frozenset(co["code"] for co in c["courses"])
        if combo_key not in seen_combos:
            seen_combos.add(combo_key)
            unique.append(c)
        if len(unique) >= max_schedules:
            break

    return unique


def _time_to_conflict(course_a: dict, course_b: dict) -> bool:
    """시간 충돌 확인 ( Alias )"""
    return _has_time_conflict(course_a, course_b)
