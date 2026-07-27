"""시간표 시뮬레이션 모듈 - 선호 시간대 기반 조합 알고리즘 (대용량 데이터 최적화)"""

from itertools import combinations

from .data.courses import get_required_remaining, get_available_courses, get_course


def _time_to_minutes(time_str: str) -> int:
    """HH:MM 또는 HH:MM:SS 형식을 분으로 변환"""
    try:
        parts = time_str.strip().split(":")
        if len(parts) >= 2:
            return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        pass
    return 0



def _has_time_conflict(course_a: dict, course_b: dict) -> bool:
    """두 과목이 시간이 겹치는지 확인"""
    for day_a, start_a, end_a in course_a.get("time_slots", []):
        for day_b, start_b, end_b in course_b.get("time_slots", []):
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
    time_slots = course.get("time_slots", [])
    if not time_slots:
        return False

    for day, start, end in time_slots:
        if day not in preferred_days:
            return False

        start_min = _time_to_minutes(start)
        end_min = _time_to_minutes(end)

        # 피하는 시간대 체크
        for avoid in avoid_times:
            sep = "~" if "~" in avoid else "-"
            if sep in avoid:
                avoid_start_str, avoid_end_str = avoid.split(sep)
                avoid_start = _time_to_minutes(avoid_start_str)
                avoid_end = _time_to_minutes(avoid_end_str)
                if start_min < avoid_end and avoid_start < end_min:
                    return False

        # 선호 시간대 체크 (하나라도 겹치면 OK)
        if preferred_times:
            in_preferred = False
            for pref in preferred_times:
                sep = "~" if "~" in pref else "-"
                if sep in pref:
                    pref_start_str, pref_end_str = pref.split(sep)
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

    # 미이수 필수(교양필수, 계열공통, 전공필수) 과목 포함 시 파격 보너스
    target_semester = student.get("target_semester")
    required = set()
    try:
        from .data.courses import get_all_remaining_required_for_semester
        sem_req = get_all_remaining_required_for_semester(student, target_semester)
        for cat, info in sem_req.items():
            for c in info.get("available_now", []):
                required.add(c["code"])
    except Exception:
        pass
        
    for c in get_required_remaining(student):
        required.add(c["code"])

    for course in schedule:
        if course["code"] in required:
            # 특히 계열공통 과목인 경우 추가 보너스 점수를 부여하여 우선 순위 랭킹업
            if course.get("type") == "계열공통" or "계공" in course.get("type", ""):
                score += 25.0
            else:
                score += 15.0

    # 수강 가능한 과목 보너스
    available = {c["code"] for c in get_available_courses(student)}
    for course in schedule:
        if course["code"] in available:
            score += 5.0

    # 융합전공 및 특화트랙 매칭 보너스
    conv = student.get("convergence_major")
    spec = student.get("specialized_track")
    if conv or spec:
        for course in schedule:
            course_name = course.get("name", "")
            course_desc = course.get("description", "")
            
            # 특화트랙 매칭
            if spec == "데이터 사이언스 트랙":
                keywords = ["데이터", "분석", "통계", "머신러닝", "딥러닝", "인공지능", "AI", "Data"]
                if any(kw in course_name or kw in course_desc for kw in keywords):
                    score += 8.0
            elif spec == "인지 감성 특화 트랙":
                keywords = ["인지", "감성", "인간", "HCI", "심리", "UX", "디자인"]
                if any(kw in course_name or kw in course_desc for kw in keywords):
                    score += 8.0
            elif spec == "지능형 IoT 소프트웨어 트랙":
                keywords = ["IoT", "임베디드", "네트워크", "센서", "통신", "시스템"]
                if any(kw in course_name or kw in course_desc for kw in keywords):
                    score += 8.0
            elif spec == "풀스택 웹/모바일 소프트웨어 트랙":
                keywords = ["웹", "모바일", "앱", "안드로이드", "iOS", "프론트", "백엔드", "네트워크", "서버"]
                if any(kw in course_name or kw in course_desc for kw in keywords):
                    score += 8.0
                    
            # 융합전공 매칭
            if conv:
                conv_clean = conv.replace("융합전공", "")
                match_terms = [conv_clean, "융합", "문화", "콘텐츠", "경영", "스마트", "공공", "서비스"]
                if any(term in course_name or term in course_desc for term in match_terms):
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

    대용량 데이터(765과목) 최적화:
    1. 시간표가 있는 과목만 필터링
    2. 선호 요일/시간대 기반 사전 필터링
    3. 탐색 풀 제한 (최대 60과목)
    4. 조기 종료

    반환 형식:
    - list[dict]: 시간표 조합 리스트
    - 각 dict에 "preference_applied", "fallback_reason" 플래그 포함
    """
    required_remaining = get_required_remaining(student)
    available = get_available_courses(student)

    preferred_days = student.get("preferred_days", ["월", "화", "수", "목", "금"])
    preferred_times = student.get("preferred_times", [])
    avoid_times = student.get("avoid_times", [])

    # 1차 시도: 사용자 선호 요일 적용
    results = _generate_timetable_with_preferences(
        student, required_remaining, available,
        preferred_days, preferred_times, avoid_times,
        max_schedules, max_candidates
    )

    # 유효한 결과가 있으면 선호 적용된 결과 반환
    if results:
        for r in results:
            r["preference_applied"] = True
            r["fallback_reason"] = None
        return results

    # 2차 시도 (Fallback): 선호 요일 무시하고 전공 필수 우선 배치
    all_days = ["월", "화", "수", "목", "금"]
    fallback_results = _generate_timetable_with_preferences(
        student, required_remaining, available,
        all_days, preferred_times, avoid_times,
        max_schedules, max_candidates
    )

    # fallback 결과도 없으면 빈 리스트 반환
    if not fallback_results:
        return []

    # fallback 결과에 플래그 추가
    removed_days = [d for d in all_days if d not in preferred_days]
    if removed_days:
        fallback_reason = (
            f"{', '.join(removed_days)}요일 공강을 맞추면 필수 과목을 배치할 수 없어 "
            f"부득이하게 모든 요일을 포함하여 추천했습니다."
        )
    else:
        fallback_reason = None

    for r in fallback_results:
        r["preference_applied"] = False
        r["fallback_reason"] = fallback_reason

    return fallback_results


def _generate_timetable_with_preferences(
    student: dict,
    required_remaining: list,
    available: list,
    preferred_days: list[str],
    preferred_times: list[str],
    avoid_times: list[str],
    max_schedules: int,
    max_candidates: int,
) -> list[dict]:
    """지정된 선호 요일/시간대로 시간표 조합을 생성합니다."""

    # 1단계: 시간표가 있는 과목만 필터링
    available_with_schedule = [c for c in available if c.get("time_slots")]

    # 2단계: 선호 시간대에 맞는 과목만 필터링
    preferred_available = [
        c for c in available_with_schedule
        if _fits_preferences(c, preferred_days, preferred_times, avoid_times)
    ]

    # 3단계: 탐색 풀 구성 (필수 + 선호 + 나머지)
    course_pool = []
    seen_codes = set()

    # 필수 및 계열공통/교양필수 미이수 과목 수집 (최우선 순위)
    target_semester = student.get("target_semester") or "2026-2학기"
    try:
        from .data.courses import get_all_remaining_required_for_semester
        sem_req = get_all_remaining_required_for_semester(student, target_semester)
        for cat, info in sem_req.items():
            for c in info.get("available_now", []):
                full_course = get_course(c["code"])
                if full_course and full_course["code"] not in seen_codes and full_course.get("time_slots"):
                    course_pool.append(full_course)
                    seen_codes.add(full_course["code"])
    except Exception as e:
        print(f"Error loading semester required courses for scheduler: {e}")

    # 필수 과목 먼저 (항상 포함)
    for c in required_remaining:
        if c["code"] not in seen_codes and c.get("time_slots"):
            course_pool.append(c)
            seen_codes.add(c["code"])

    # 융합/특화전공 관련 과목 우선 탐색 풀 배치
    conv = student.get("convergence_major")
    spec = student.get("specialized_track")
    if conv or spec:
        for c in available_with_schedule:
            if c["code"] not in seen_codes:
                course_name = c.get("name", "")
                course_desc = c.get("description", "")
                is_match = False
                
                # 특화트랙 매칭
                if spec == "데이터 사이언스 트랙":
                    keywords = ["데이터", "분석", "통계", "머신러닝", "딥러닝", "인공지능", "AI", "Data"]
                    if any(kw in course_name or kw in course_desc for kw in keywords):
                        is_match = True
                elif spec == "인지 감성 특화 트랙":
                    keywords = ["인지", "감성", "인간", "HCI", "심리", "UX", "디자인"]
                    if any(kw in course_name or kw in course_desc for kw in keywords):
                        is_match = True
                elif spec == "지능형 IoT 소프트웨어 트랙":
                    keywords = ["IoT", "임베디드", "네트워크", "센서", "통신", "시스템"]
                    if any(kw in course_name or kw in course_desc for kw in keywords):
                        is_match = True
                elif spec == "풀스택 웹/모바일 소프트웨어 트랙":
                    keywords = ["웹", "모바일", "앱", "안드로이드", "iOS", "프론트", "백엔드", "네트워크", "서버"]
                    if any(kw in course_name or kw in course_desc for kw in keywords):
                        is_match = True
                        
                # 융합전공 매칭
                if conv:
                    conv_clean = conv.replace("융합전공", "")
                    match_terms = [conv_clean, "융합", "문화", "콘텐츠", "경영", "스마트", "공공", "서비스"]
                    if any(term in course_name or term in course_desc for term in match_terms):
                        is_match = True
                        
                if is_match:
                    course_pool.append(c)
                    seen_codes.add(c["code"])

    # 선호 과목 추가
    for c in preferred_available:
        if c["code"] not in seen_codes:
            course_pool.append(c)
            seen_codes.add(c["code"])

    # 전체 수강 가능 과목도 추가 (선호에 없지만 넓은 탐색을 위해)
    for c in available_with_schedule:
        if c["code"] not in seen_codes:
            course_pool.append(c)
            seen_codes.add(c["code"])

    # 탐색 풀 제한 (765과목 중 효율적 탐색)
    MAX_POOL = 60
    if len(course_pool) > MAX_POOL:
        course_pool = course_pool[:MAX_POOL]

    # 필수 과목 세트
    required_codes = {c["code"] for c in required_remaining}

    # 4단계: 조합 생성 (3~5과목)
    candidates = []
    max_combo_size = min(6, len(course_pool) + 1)

    for size in range(3, max_combo_size):
        for combo in combinations(course_pool, size):
            combo_list = list(combo)

            # 사용자가 지정한 기피 요일 및 시간대 엄격 체크
            strict_conflict = False
            for course in combo_list:
                time_slots = course.get("time_slots", [])
                for day, start, end in time_slots:
                    # 1) 요일 기피 체크
                    if day not in preferred_days:
                        strict_conflict = True
                        break
                    # 2) 기피 시간대 체크
                    start_min = _time_to_minutes(start)
                    end_min = _time_to_minutes(end)
                    for avoid in avoid_times:
                        sep = "~" if "~" in avoid else "-"
                        if sep in avoid:
                            avoid_start_str, avoid_end_str = avoid.split(sep)
                            avoid_start = _time_to_minutes(avoid_start_str)
                            avoid_end = _time_to_minutes(avoid_end_str)
                            if start_min < avoid_end and avoid_start < end_min:
                                strict_conflict = True
                                break
                    if strict_conflict:
                        break
                if strict_conflict:
                    break
            if strict_conflict:
                continue

            # 시간 충돌 체크
            has_conflict = False
            for i in range(len(combo_list)):
                for j in range(i + 1, len(combo_list)):
                    if _has_time_conflict(combo_list[i], combo_list[j]):
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

        # 조합 크기별로 충분한 후보가 있으면 종료
        if len(candidates) >= max_candidates:
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
