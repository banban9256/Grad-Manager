"""시간표 시뮬레이션 모듈 - 선호 시간대 기반 조합 알고리즘 (대용량 데이터 최적화)"""

from itertools import combinations

from .data.courses import get_required_remaining, get_available_courses, get_course
from .data.csv_loader import _normalize_completion_type


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


def _find_compatible_offering(course: dict, preferred_days: list[str], preferred_times: list[str], avoid_times: list[str]) -> dict:
    """
    과목의 모든 분반(offerings)을 순회하며 사용자의 공강 제약 조건을 만족하는 첫 번째 분반을 선택합니다.
    공강 조건을 만족하는 분반이 없다면 첫 번째 분반을 Fallback으로 강제 선택하여 과목이 시간표에서 누락되는 것을 방지합니다.
    """
    import copy
    course_copy = copy.deepcopy(course)
    offerings = course_copy.get("offerings", [])
    if not offerings:
        return course_copy

    best_offering = None
    for o in offerings:
        o_time_slots = o.get("time_slots", [])
        if not o_time_slots:
            # 진로와상담(KY410)처럼 시간표가 비어있는 분반에 대한 예외 처리
            fav_day = preferred_days[0] if preferred_days else "월"
            o_time_slots = [(fav_day, "18:00", "19:00")]

        # 가상으로 time_slots를 씌워서 _fits_preferences 평가
        temp_c = dict(course_copy)
        temp_c["time_slots"] = o_time_slots
        if _fits_preferences(temp_c, preferred_days, preferred_times, avoid_times):
            best_offering = o
            break

    # 공강 조건을 충족하는 분반이 없다면 첫 번째 분반을 fallback으로 지정
    if not best_offering:
        best_offering = offerings[0]

    # 선택된 분반의 데이터로 최종 매핑
    course_copy["professor"] = (best_offering.get("professor") or course_copy.get("professor") or "미정").strip() or "미정"
    first_classroom = best_offering.get("classrooms")[0] if best_offering.get("classrooms") else None
    course_copy["room"] = (first_classroom or course_copy.get("room") or "미정").strip() or "mijeong" # 영어 '미정' 방지용으로 안전하게
    course_copy["room"] = "미정" if course_copy["room"] == "mijeong" else course_copy["room"]
    
    o_time_slots = best_offering.get("time_slots", [])
    if not o_time_slots:
        fav_day = preferred_days[0] if preferred_days else "월"
        o_time_slots = [(fav_day, "18:00", "19:00")]
    course_copy["time_slots"] = o_time_slots
    
    if "section" in best_offering:
        course_copy["section"] = best_offering["section"]
    else:
        course_copy["section"] = ""

    return course_copy


def _is_track_course(course: dict, spec: str) -> bool:
    """학생의 특화트랙 키워드와 과목명/설명이 매칭되는지 확인합니다."""
    if not spec:
        return False
    course_name = course.get("name", "")
    course_desc = course.get("description", "") or ""
    
    # 트랙별 키워드 매핑
    keywords = []
    if "데이터" in spec:
        keywords = ["데이터", "분석", "통계", "머신러닝", "딥러닝", "인공지능", "AI", "Data"]
    elif "인지" in spec or "감성" in spec:
        keywords = ["인지", "감성", "인간", "HCI", "심리", "UX", "디자인"]
    elif "지능형" in spec or "iot" in spec.lower():
        keywords = ["IoT", "임베디드", "네트워크", "센서", "통신", "시스템"]
    elif "풀스택" in spec or "웹" in spec or "모바일" in spec:
        keywords = ["웹", "모바일", "앱", "안드로이드", "iOS", "프론트", "백엔드", "네트워크", "서버"]
        
    if not keywords:
        return False
        
    return any(kw in course_name or kw in course_desc for kw in keywords)


def _sort_courses_by_priority(courses: list, student: dict) -> list:
    """시간표 내의 과목 리스트를 1순위(교필/계공 AISW)->2순위(특화 트랙 전공)->3순위(나머지 AISW 전공)->4순위(타학과 및 일선) 순으로 정렬합니다."""
    spec = student.get("specialized_track")
    
    # 계열공통 학점 부족 여부 파악
    try:
        from .data.courses import get_graduation_credit_summary
        summary = get_graduation_credit_summary(student)
        gy_remaining = summary.get("categories", {}).get("계열공통", {}).get("remaining", 0)
    except Exception:
        gy_remaining = 0

    def get_course_priority(c):
        name = c.get("name", "")
        ctype = c.get("type", "")
        code = c.get("code", "")
        prefix = "".join(ch for ch in code if ch.isalpha())
        
        # 1순위: 교필/계공(AISW)
        is_exception = "채플" in name or "진로와상담" in name or "사회생활길잡이" in name or "대학생활길잡이" in name
        if is_exception or ctype == "교양필수":
            return 1
            
        is_aisw_common = (ctype == "계열공통" and (prefix == "AS" or code.startswith("AS") or "AISW" in str(c.get("department", ""))))
        if is_aisw_common:
            return 1
            
        # 2순위: 특화 트랙 전공
        if spec and _is_track_course(c, spec) and ctype == "전공선택":
            return 2
            
        # 3순위: 나머지 AISW 전공
        is_aisw_major = prefix in {"SH", "DS", "AI"} and ctype in {"전공선택", "전공필수"}
        if is_aisw_major:
            return 3
            
        # 4순위: 타 학과 과목 및 일반선택 등 그 외 모든 과목
        return 4

    return sorted(courses, key=get_course_priority)


def _score_schedule(schedule: list[dict], student: dict) -> float:
    """시간표 점수 계산 (높을수록 좋음)"""
    score = 0.0

    # 1. 미이수 계열공통, 교양필수, 전공선택, 전공필수 과목에 가중치 부여
    required_remain_codes = set()
    elective_remain_codes = set()
    try:
        from .data.courses import get_required_remaining, get_track_elective_remaining
        required_remain = get_required_remaining(student)
        required_remain_codes = {c["code"] for c in required_remain}
        electives_remain = get_track_elective_remaining(student)
        elective_remain_codes = {c["code"] for c in electives_remain}
    except Exception:
        pass

    # 계공 부족 확인
    try:
        from .data.courses import get_graduation_credit_summary
        summary = get_graduation_credit_summary(student)
        gy_remaining = summary.get("categories", {}).get("계열공통", {}).get("remaining", 0)
    except Exception:
        gy_remaining = 0

    spec = student.get("specialized_track")

    for course in schedule:
        code = course["code"]
        course_name = course.get("name", "")
        ctype = course.get("type", "")
        prefix = "".join(ch for ch in code if ch.isalpha())
        
        # 1순위: 교필 / 계공(AISW) 및 예외 필수과목 -> 대폭 상향 (+1000.0)
        is_exception_course = "채플" in course_name or "진로와상담" in course_name or "사회생활길잡이" in course_name or "대학생활길잡이" in course_name
        is_aisw_common = (ctype == "계열공통" and (prefix == "AS" or code.startswith("AS") or "AISW" in str(course.get("department", ""))))
        if is_exception_course or ctype == "교양필수" or code in required_remain_codes or is_aisw_common:
            score += 1000.0
            
        # 2순위: 특화 트랙 전공 과목 -> (+800.0)
        elif spec and _is_track_course(course, spec) and ctype == "전공선택":
            score += 800.0
            
        # 3순위: 나머지 AISW 전공 과목 -> (+500.0)
        elif prefix in {"SH", "DS", "AI"} and ctype in {"전공선택", "전공필수"}:
            score += 500.0
            
        # 4순위: 타 학과 과목 및 일반선택 등 그 외 모든 과목 -> (+100.0)
        else:
            score += 100.0

    # 대화 추천 과목 보너스 (과목당 +200.0점)
    rec_codes = student.get("chatbot_recommended_courses", [])
    if rec_codes:
        for course in schedule:
            if course["code"] in rec_codes:
                score += 200.0

    # 학생 관심사 매칭 보너스 (+30.0)
    interests = student.get("interests", [])
    if interests:
        for course in schedule:
            course_text = (course.get("name", "") + " " + course.get("description", "")).lower()
            if any(interest.lower() in course_text for interest in interests):
                score += 30.0

    # 융합전공 매칭 보너스 (+20.0)
    conv = student.get("convergence_major")
    if conv:
        for course in schedule:
            course_name = course.get("name", "")
            course_desc = course.get("description", "") or ""
            conv_clean = conv.replace("융합전공", "")
            match_terms = [conv_clean, "융합", "문화", "콘텐츠", "경영", "스마트", "공공", "서비스"]
            if any(term in course_name or term in course_desc for term in match_terms):
                score += 20.0

    # 5. 선호 시간대 매칭 보너스 (+5.0)
    for course in schedule:
        if _fits_preferences(course, student["preferred_days"], student["preferred_times"], student.get("avoid_times", [])):
            score += 5.0

    # 6. 일반 수강 가능 과목 기본 점수 (+2.0)
    score += len(schedule) * 2.0

    # 학점 수 보너스 (많을수록 좋지만, 21학점 이상이면 감점)
    total_credits = sum(c["credits"] for c in schedule)
    score += total_credits * 1.0
    if total_credits > 21:
        score -= (total_credits - 21) * 2.0

    return score


def generate_timetable(student: dict, max_schedules: int = 3, max_candidates: int = 50, target_credits: int = 18) -> list[dict]:
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
        max_schedules, max_candidates, target_credits
    )

    # 유효한 결과가 있으면 선호 적용된 결과 반환
    if results:
        for r in results:
            r["preference_applied"] = True
            r["fallback_reason"] = None
        return results

    # 2차 시도 (Fallback): 선호 요일 제약을 전체 요일로 완화하여 재탐색
    fallback_days = ["월", "화", "수", "목", "금"]
    results = _generate_timetable_with_preferences(
        student, required_remaining, available,
        fallback_days, preferred_times, avoid_times,
        max_schedules, max_candidates, target_credits
    )
    if results:
        for r in results:
            r["preference_applied"] = False
            r["fallback_reason"] = "선호하시는 공강 요일 조건으로는 학점 요건을 충족하는 시간표를 구성할 수 없어, 공강 요일을 조정하여 시간표를 구성했습니다."
        return results

    return []


def _generate_timetable_with_preferences(
    student: dict,
    required_remaining: list,
    available: list,
    preferred_days: list[str],
    preferred_times: list[str],
    avoid_times: list[str],
    max_schedules: int,
    max_candidates: int,
    target_credits: int,
) -> list[dict]:
    """지정된 선호 요일/시간대로 시간표 조합을 생성합니다."""

    # 0단계: AISW 소속 교수진 동적 수집 및 KY410(진로와상담) 분반 필터링, 가상 시간표 할당
    try:
        from .data.csv_loader import load_courses
        courses_db = load_courses()
    except Exception:
        courses_db = {}

    aisw_profs = set()
    for c_code, c_info in courses_db.items():
        if any(c_code.startswith(p) for p in ["AS", "SH", "DS", "AI"]):
            for o in c_info.get("offerings", []):
                prof = o.get("professor")
                if prof and prof != "미정" and "신규" not in prof:
                    aisw_profs.add(prof)
    # 기본 예비 교수 리스트 추가
    aisw_profs.update(["이양선", "손승일", "백수진", "안현", "조성호", "이용걸", "이형우", "임익수", "홍승필", "성낙준", "고병수", "강영경"])

    for c in available:
        if c.get("code") == "KY410":
            aisw_offerings = [o for o in c.get("offerings", []) if o.get("professor") in aisw_profs]
            if aisw_offerings:
                c["offerings"] = aisw_offerings
                primary = aisw_offerings[0]
                c["professor"] = primary.get("professor", "미정")
                c["room"] = primary.get("classrooms")[0] if primary.get("classrooms") else "미정"
                if not primary.get("time_slots"):
                    fav_day = preferred_days[0] if preferred_days else "월"
                    primary["time_slots"] = [(fav_day, "18:00", "19:00")]
                c["time_slots"] = primary["time_slots"]

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

    # 대화 추천 과목 (Must-Have) 최우선 배치
    rec_codes = student.get("chatbot_recommended_courses", [])
    if rec_codes:
        for code in rec_codes:
            full_c = get_course(code)
            if full_c and full_c.get("time_slots") and code not in seen_codes:
                from .data.courses import _is_course_already_taken
                if not _is_course_already_taken(full_c, student):
                    course_pool.append(full_c)
                    seen_codes.add(code)

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

    # 미이수 트랙 전공선택 과목 우선 탐색 풀 배치
    try:
        from .data.courses import get_track_elective_remaining
        electives = get_track_elective_remaining(student, target_semester)
        for c in electives:
            if c["code"] not in seen_codes and c.get("time_slots"):
                course_pool.append(c)
                seen_codes.add(c["code"])
    except Exception as e:
        print(f"Error loading track electives for scheduler: {e}")

    # 필수 과목 먼저 (항상 포함)
    for c in required_remaining:
        if c["code"] not in seen_codes and c.get("time_slots"):
            course_pool.append(c)
            seen_codes.add(c["code"])

    # 사용자 관심사(interests) 매칭 과목 우선 탐색 풀 배치
    interests = student.get("interests", [])
    if interests:
        for c in available_with_schedule:
            if c["code"] not in seen_codes:
                course_text = (c.get("name", "") + " " + c.get("description", "")).lower()
                if any(interest.lower() in course_text for interest in interests):
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

    # 필수/우선 추천 과목 강제 배정 처리 준비 (교필/계공/전필 필수 과목 자동 수집)
    hard_core_courses = []
    seen_hard_codes = set()

    # 1) 챗봇 추천 과목 (Must-Have) 중 교필/계공/전필 수집
    rec_codes = student.get("chatbot_recommended_courses", [])
    for code in rec_codes:
        matched_c = next((c for c in available if c.get("code") == code), None)
        if matched_c and code not in seen_hard_codes:
            c_type = _normalize_completion_type(matched_c.get("type", ""))
            if c_type in ["교양필수", "계열공통", "전공필수"]:
                # 다중 분반 탐색 (Iterative Section Search) 및 Fallback 매핑
                resolved_c = _find_compatible_offering(matched_c, preferred_days, preferred_times, avoid_times)
                hard_core_courses.append(resolved_c)
                seen_hard_codes.add(code)

    # 2) 핵심 필수과목 (KY410, AS004, KYC56) 자동 포함
    for hc_code in ["KY410", "AS004", "KYC56"]:
        if hc_code not in seen_hard_codes:
            matched_c = next((c for c in available if c.get("code") == hc_code), None)
            if matched_c:
                # 다중 분반 탐색 (Iterative Section Search) 및 Fallback 매핑
                resolved_c = _find_compatible_offering(matched_c, preferred_days, preferred_times, avoid_times)
                hard_core_courses.append(resolved_c)
                seen_hard_codes.add(hc_code)

    # 강제 배정 과목은 탐색 풀에서 제외하여 백트래킹 시 중복 선택 방지
    course_pool = [c for c in course_pool if c["code"] not in seen_hard_codes]

    # 필수 과목 세트
    required_codes = {c["code"] for c in required_remaining}

    # 4단계: 백트래킹(DFS)을 이용한 조합 생성 (3~7과목)
    candidates = []
    
    # 탐색 횟수를 제한하여 최악의 경우에도 무한 루프에 빠지지 않도록 안전장치 설정
    search_count = 0
    MAX_SEARCH = 1000

    def backtrack(start_idx, current_schedule, current_credits):
        nonlocal search_count
        if search_count >= MAX_SEARCH:
            return
        search_count += 1

        # 학점 초과 시 즉시 가지치기(Pruning)
        if current_credits > (target_credits + 0.1):
            return

        # 기지 조건: 3과목 이상이고, 학점이 target_credits 와 정확히 일치할 때
        if len(current_schedule) >= 3:
            # target_credits가 지정된 경우 정확히 일치하도록 제한 (0학점 과목은 제외한 시간표 블록 총합)
            if abs(current_credits - target_credits) < 0.1:
                # 3순위 (특화과목) 강제: 특화 트랙이 지정되어 있고, 탐색 풀에 해당 트랙 과목이 2개 이상 있는 경우
                # 후보 시간표에는 반드시 이 트랙 관련 특화 과목이 최소 2개(6학점) 이상 포함되어야 함
                if spec:
                    track_courses_in_pool = sum(1 for c in course_pool if _is_track_course(c, spec))
                    if track_courses_in_pool >= 2:
                        track_courses_in_schedule = sum(1 for c in current_schedule if _is_track_course(c, spec))
                        if track_courses_in_schedule < 2:
                            return  # 트랙 과목 최소 2개 요건 미달 시 조합 탈락

                included_required = [c["code"] for c in current_schedule if c["code"] in required_codes]
                candidates.append({
                    "courses": list(current_schedule),
                    "total_credits": current_credits,
                    "included_required": included_required,
                    "missing_required": list(required_codes - set(included_required)),
                })
                # 충분한 후보군이 쌓였으면 전체 탐색을 즉시 강제 종료시킴
                if len(candidates) >= max_candidates * 2:
                    search_count = MAX_SEARCH
                    return

        # 최대 7과목까지만 탐색
        if len(current_schedule) >= 7:
            return

        for i in range(start_idx, len(course_pool)):
            if search_count >= MAX_SEARCH:
                break
            course = course_pool[i]
            credits = course.get("credits", 0)

            # 학점 상한 체크
            if current_credits + credits > (target_credits + 1):
                continue

            # 사용자가 지정한 기피 요일 및 시간대 엄격 체크
            strict_conflict = False
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
                continue

            # 시간 충돌 체크 (가지치기)
            has_conflict = False
            for exist_course in current_schedule:
                if _has_time_conflict(exist_course, course):
                    has_conflict = True
                    break
            if has_conflict:
                continue

            # 재귀 탐색
            current_schedule.append(course)
            backtrack(i + 1, current_schedule, current_credits + credits)
            current_schedule.pop()

    # 백트래킹 탐색 수행
    initial_credits = sum(c.get("credits", 0) for c in hard_core_courses)
    backtrack(0, list(hard_core_courses), initial_credits)

    # 점수 기반 정렬
    candidates.sort(key=lambda s: _score_schedule(s["courses"], student), reverse=True)

    # 중복 제거 (과목 구성이 같은 시간표 제거)
    unique = []
    seen_combos = set()
    for c in candidates:
        combo_key = frozenset(co["code"] for co in c["courses"])
        if combo_key not in seen_combos:
            seen_combos.add(combo_key)
            # 최종 정렬 보정: 개별 시간표 과목 순서도 1->2->3->4순위로 정렬하여 삽입
            c["courses"] = _sort_courses_by_priority(c["courses"], student)
            unique.append(c)
        if len(unique) >= max_schedules:
            break

    return unique
