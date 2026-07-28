"""AI 챗봇 모듈 - Google Gemini API 연동 + 시스템 프롬프트 (CSV 기반 데이터)

개선 사항:
- LLM API: Groq → Google Gemini (gemini-1.5-flash) 교체
- 채플 로직: 고정 필요 횟수(8회), AISW 전용 코드(KY101) 사용
- 관심사 추천 필터: 키워드 확장, 부정 표현 제외, 미관심시 안전한 추천
- 컨텍스트 절약: 추천/시간표 키워드 없으면 최소 컨텍스트만 주입
- 토큰 절약: 대화 히스토리 8턴 제한, 이수 과목 요약만 주입
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .persona import SYSTEM_PROMPT
from .data.csv_loader import hanja_to_hangul
from .data.students import get_student
from .data.courses import (
    get_required_remaining,
    get_available_courses,
    get_required_remaining_by_track,
    get_graduation_credit_summary,
    validate_completed_categories,
    get_interest_matching_courses,
    recommend_by_interest_with_graduation,
    get_track_curriculum,
    get_all_remaining_required_for_semester,
)
from .scheduler import generate_timetable
from .notifications import search_notices, get_upcoming_alerts, filter_notices_by_keywords

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

api_key = os.getenv("GEMINI_API_KEY")
_model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if api_key:
    gemini_client = genai.Client(api_key=api_key)
else:
    gemini_client = None

# ==============================
# 채플 설정
# ==============================

# AISW 학생의 채플 과목 코드 (KY101: AI SW계열 전용, 0.5학점)
_AISW_CHAPEL_CODE = "KY101"

# 전체 채플 과목 코드 (다른 학과 학생도 확인용)
_ALL_CHAPEL_CODES = {"KY100", "KY101", "KY201", "KY304", "KY509"}

# 채플 필수 이수 횟수 (졸업요건 고정값 - 수정 시 업데이트 필요)
_CHAPEL_REQUIRED_COUNT = 8

# 대화 히스토리 최대 턴 수 (user+assistant 쌍 기준)
_MAX_HISTORY_TURNS = 8

# ==============================
# 계열 공통 과목 (AISW 필수)
# ==============================

# AS0xx 시리즈: AISW 계열 공통 과목 코드 -> 과목명
_TRACK_COMMON_COURSES = {
    "AS001": "AI.SW개론",
    "AS002": "C언어",
    "AS003": "공학설계입문",
    "AS004": "AI·SW수학",
    "AS005": "문제해결형프로그래밍",
    "AS006": "웹프로그래밍",
    "AS007": "자료구조",
    "AS008": "자바프로그래밍",
    "AS009": "논리회로",
    "AS010": "데이터통신",
    "AS011": "운영체제",
    "AS012": "데이터베이스",
}

# 1학기 개설: AS001, AS002, AS003, AS007, AS008, AS010
_TRACK_COMMON_1ST_SEMESTER = {"AS001", "AS002", "AS003", "AS007", "AS008", "AS010"}
# 2학기 개설: AS004, AS005, AS006, AS009, AS011, AS012
_TRACK_COMMON_2ND_SEMESTER = {"AS004", "AS005", "AS006", "AS009", "AS011", "AS012"}


def _get_unfinished_track_common(student: dict, target_semester: str = None) -> dict:
    """학생이 아직 이수하지 않은 계열 공통 과목을 반환합니다.

    Returns:
        {"all_unfinished": [...], "semester_match": [...], "other": [...]}
    """
    from .data.courses import _get_taken_course_filter, _normalize_course_name
    taken_codes, taken_names = _get_taken_course_filter(student)

    all_unfinished = []
    for code, name in _TRACK_COMMON_COURSES.items():
        normalized_name = _normalize_course_name(name)
        is_taken = code in taken_codes or (normalized_name and normalized_name in taken_names)
        if not is_taken:
            semester_tag = "1학기" if code in _TRACK_COMMON_1ST_SEMESTER else "2학기"
            all_unfinished.append({"code": code, "name": name, "semester": semester_tag})

    if not all_unfinished:
        return {"all_unfinished": [], "semester_match": [], "other": []}

    # 목표 학기에 개설된 과목 분리
    semester_match = []
    other = []
    if target_semester:
        is_2nd = "2학기" in target_semester
        for c in all_unfinished:
            if is_2nd and c["code"] in _TRACK_COMMON_2ND_SEMESTER:
                semester_match.append(c)
            elif not is_2nd and c["code"] in _TRACK_COMMON_1ST_SEMESTER:
                semester_match.append(c)
            else:
                other.append(c)
    else:
        other = all_unfinished

    return {"all_unfinished": all_unfinished, "semester_match": semester_match, "other": other}


def _build_track_common_context(student: dict, target_semester: str = None) -> str:
    """계열 공통 과목 미이수 현황을 텍스트로 구성합니다."""
    result = _get_unfinished_track_common(student, target_semester)
    all_unfinished = result["all_unfinished"]

    if not all_unfinished:
        return "계열 공통 과목 12개를 모두 이수 완료했습니다."

    lines = [f"## 미이수 계열 공통 과목 ({len(all_unfinished)}개 부족)"]

    if result["semester_match"]:
        lines.append("")
        lines.append(f"### 이번 학기({target_semester}) 개설 가능 과목 (최우선 추천)")
        for c in result["semester_match"]:
            lines.append(f"- **{c['code']}** {c['name']} [{c['semester']}] ← 반드시 추천하세요")

    if result["other"]:
        lines.append("")
        lines.append("### 다른 학기 개설 과목")
        for c in result["other"]:
            lines.append(f"- {c['code']} {c['name']} [{c['semester']}]")

    lines.append("")
    lines.append("**규칙: 계열 공통 과목은 AISW 졸업 필수입니다. 미이수 과목이 있다면 반드시 우선 추천하세요.**")

    return "\n".join(lines)


# 추천 관련 키워드 (컨텍스트 풀 주입 트리거)
_RECOMMEND_KEYWORDS = {"추천", "들을까", "들어", "수강", "신청", "시간표", "짜줘", "짜자", "추천해"}
_SCHEDULE_KEYWORDS = {"시간표", "스케줄", "공강", "연강"}


# ==============================
# 채플 관련
# ==============================

def _count_chapel_completed(student: dict) -> dict:
    """채플 이수 현황을 계산합니다.

    채플은 AISW 학과 수업이 아니어도 필수 횟수만 채우면 인정됩니다.
    학수번호에 상관없이 이름에 '채플'이 포함된 횟수를 기준으로 합산합니다.
    """
    from .data.courses import _get_chapel_completed_count
    completed_count = _get_chapel_completed_count(student)

    # 채플 코드를 구하기 위해 상세 정보나 이름 목록과 매핑
    completed_codes = []
    completed_details = student.get("completed_courses_detail", [])
    if completed_details:
        for detail in completed_details:
            name = detail.get("name", "")
            code = detail.get("code", "")
            if name and "채플" in name:
                completed_codes.append(code)
    else:
        completed_names = student.get("completed_course_names", [])
        completed_list = student.get("completed_courses", [])
        for idx, name in enumerate(completed_names):
            if "채플" in name and idx < len(completed_list):
                completed_codes.append(completed_list[idx])

    return {
        "completed_count": completed_count,
        "required_count": _CHAPEL_REQUIRED_COUNT,
        "is_satisfied": completed_count >= _CHAPEL_REQUIRED_COUNT,
        "completed_codes": completed_codes,
    }


# ==============================
# 컨텍스트 빌더
# ==============================

def _build_completed_history_text(student: dict) -> str:
    """학생의 이수 완료 과목 요약을 텍스트로 구성합니다 (토큰 절약)."""
    courses_db = None
    history_records = []

    try:
        from .data.csv_loader import load_courses
        courses_db = load_courses()
    except Exception:
        pass

    try:
        from app.database import SessionLocal
        from app import models as db_models

        db = SessionLocal()
        try:
            sid_int = int(student["student_id"])
            histories = db.query(db_models.StudentCourseHistory).filter(
                db_models.StudentCourseHistory.student_id == sid_int
            ).all()
            for h in histories:
                try:
                    c_rec = db.query(db_models.Course).filter(
                        db_models.Course.course_id == h.course_id
                    ).first()
                    code = c_rec.course_code if c_rec else f"UNKNOWN-{h.course_id}"
                    name = c_rec.course_name if c_rec else "과목명 미정"
                except Exception:
                    code = f"UNKNOWN-{h.course_id}"
                    name = "과목명 미정"

                cat = getattr(h, 'course_type', None) or ""
                if not cat.strip() and courses_db:
                    course_info = courses_db.get(code, {})
                    cat = course_info.get("type", "일반선택")
                elif not cat.strip():
                    cat = "일반선택"

                history_records.append({
                    "code": code,
                    "name": name,
                    "semester": h.semester_taken or "",
                    "grade": h.grade or "",
                    "credit": float(h.earned_credit) if h.earned_credit else 0,
                    "category": cat,
                    "is_retake": h.is_retake or False,
                    "history_id": h.history_id,
                })
        finally:
            db.close()
    except Exception:
        pass

    if not history_records:
        completed_codes = student.get("completed_courses", [])
        if not completed_codes:
            return "이수 완료 과목이 없습니다."
        if courses_db:
            cat_counts = defaultdict(int)
            for code in completed_codes:
                course = courses_db.get(code)
                if course:
                    cat_counts[course.get("type", "일반선택")] += 1
                else:
                    cat_counts["기타"] += 1
            lines = [f"- {cat}: {cnt}과목" for cat, cnt in sorted(cat_counts.items())]
            lines.append(f"- 합계: {len(completed_codes)}과목")
            return "\n".join(lines)
        return f"이수 완료 과목: {len(completed_codes)}개"

    # 재수강 포기(Forfeited) 규칙 적용
    n = len(history_records)
    parent = list(range(n))

    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            ci, cj = history_records[i]["code"], history_records[j]["code"]
            ni, nj = history_records[i]["name"], history_records[j]["name"]
            if (ci and cj and ci == cj) or (ni and nj and ni == nj):
                union(i, j)
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(history_records[i])

    forfeited_ids = set()
    for root, instances in groups.items():
        has_retake = any(inst["is_retake"] for inst in instances)
        if has_retake and len(instances) > 1:
            def sem_score(s, _re=re):
                m = _re.match(r'(\d+)-(\d)', s)
                return int(m.group(1)) * 10 + int(m.group(2)) if m else 0
            sorted_inst = sorted(instances, key=lambda x: sem_score(x["semester"]))
            for inst in sorted_inst[:-1]:
                forfeited_ids.add(inst["history_id"])

    category_stats = defaultdict(lambda: {"count": 0, "credits": 0})
    for rec in history_records:
        if rec["history_id"] in forfeited_ids:
            continue
        if rec["grade"].upper() == "F":
            continue
        cat = rec["category"]
        category_stats[cat]["count"] += 1
        category_stats[cat]["credits"] += rec["credit"]

    if not category_stats:
        return "이수 완료 과목이 없습니다."

    lines = []
    for cat, stats in sorted(category_stats.items()):
        lines.append(f"- {cat}: {stats['count']}과목, {stats['credits']}학점")

    total_count = sum(s["count"] for s in category_stats.values())
    total_credits = sum(s["credits"] for s in category_stats.values())
    lines.append(f"- 합계: {total_count}과목, {total_credits}학점")

    return "\n".join(lines)


def _build_category_requirements_text(student: dict) -> str:
    """카테고리별 졸업요건 이수/필요/잔여 현황을 텍스트로 구성합니다."""
    grad_summary = get_graduation_credit_summary(student)
    lines = []
    for cat, info in grad_summary.items():
        req = info.get("required", 0)
        comp = info.get("completed", 0)
        remain = info.get("remaining", 0)
        if req > 0:
            status = "충족" if remain == 0 else f"{remain}학점 부족"
            lines.append(f"- {cat}: {comp}/{req}학점 (잔여 {remain}학점) {chr(8594)} {status}")
        elif comp > 0:
            lines.append(f"- {cat}: {comp}학점 이수 (요건 없음)")

    spec_track = student.get("specialized_track", "")
    conv_major = student.get("convergence_major", "")
    if spec_track:
        lines.append(f"- 특화전공({spec_track}): 약 21학점 필요")
    if conv_major:
        lines.append(f"- 융합전공({conv_major}): 약 21학점 필요")

    return "\n".join(lines) if lines else "졸업요건 데이터 없음"


def _build_unfilled_required_summary(student: dict, target_semester: str = None) -> str:
    """미이수 필수 과목 요약을 생성합니다."""
    grad_summary = get_graduation_credit_summary(student)

    unfilled = []
    for cat, info in grad_summary.items():
        remain = info.get("remaining", 0)
        if remain > 0:
            unfilled.append((cat, remain))

    if not unfilled:
        return "모든 필수 요건이 충족되었습니다!"

    unfilled.sort(key=lambda x: x[1], reverse=True)

    lines = ["아래 카테고리의 필수 학수가 부족합니다:"]
    for cat, remain in unfilled:
        lines.append(f"- **{cat}**: {remain}학점 부족")

    if target_semester:
        try:
            semester_required = get_all_remaining_required_for_semester(student, target_semester)
            if semester_required:
                lines.append("")
                lines.append("이번 학기 수강 가능한 미이수 필수 과목:")
                for cat, info in semester_required.items():
                    avail = info.get("available_now", [])
                    if avail:
                        for c in avail[:5]:
                            times = ", ".join(f"{d} {s}~{e}" for d, s, e in c.get("time_slots", []))
                            time_str = f" [{times}]" if times else ""
                            prof = c.get("professor") or "미정"
                            lines.append(f"  - {c['code']} {c['name']} ({c['credits']}학점) (담당교수: {prof}){time_str} [{cat}]")
        except Exception:
            pass

    return "\n".join(lines)


def _build_available_courses_summary(available: list, limit: int = 40) -> str:
    """수강 가능 과목 요약을 생성합니다. (담당교수 및 시간표 포함)"""
    lines = []
    for c in available[:limit]:
        times = ", ".join(f"{d} {s}~{e}" for d, s, e in c.get("time_slots", []))
        time_str = f" [{times}]" if times else ""
        prof = c.get("professor") or "미정"
        lines.append(f"- {c['code']} {c['name']} ({c['credits']}학점) (담당교수: {prof}){time_str}")

    if not lines:
        return "수강 가능 과목 없음"
    return "\n".join(lines)


def _build_strict_available_courses_json(student: dict, limit: int = 60) -> str:
    """원칙 1: 백엔드 사전 필터링 완료된 수강 가능 과목을 JSON 형태로 구성합니다.

    - get_available_courses()가 이미 기수강 과목, 채플 완료 과목, 타학과 과목을 100% 필터링함
    - LLM에게 텍스트가 아닌 정형화된 JSON만 전달하여 환각 원천 차단
    - 과목 수 제한으로 토큰 사용량 최적화
    """
    available = get_available_courses(student)

    if not available:
        return "[]"

    courses_json = []
    for c in available[:limit]:
        course_entry = {
            "code": c.get("code", ""),
            "name": c.get("name", ""),
            "credits": c.get("credits", 3),
            "type": c.get("type", "일반선택"),
            "professor": c.get("professor") or "미정",
            "time_slots": c.get("time_slots", []),
            "classroom": c.get("room", "미정"),
        }
        courses_json.append(course_entry)

    return json.dumps(courses_json, ensure_ascii=False, indent=1)


def _parse_structured_output(llm_response: str) -> tuple[str, dict | None]:
    """원칙 4: LLM 응답에서 ```json 코드 블록을 파싱하여 (텍스트, 구조화데이터) 튜플로 반환합니다.

    Returns:
        (text_response, structured_data) - structured_data가 None이면 일반 대화
    """
    json_block_pattern = re.compile(r'```json\s*\n(.*?)\n\s*```', re.DOTALL)
    match = json_block_pattern.search(llm_response)

    if not match:
        return llm_response, None

    json_str = match.group(1).strip()
    try:
        parsed = json.loads(json_str)
        # JSON 블록 앞뒤의 텍스트만 추출
        text_before = llm_response[:match.start()].strip()
        text_after = llm_response[match.end():].strip()
        clean_text = (text_before + "\n\n" + text_after).strip() if text_before and text_after else (text_before or text_after)
        return clean_text, parsed
    except (json.JSONDecodeError, KeyError):
        return llm_response, None


# ==============================
# 학생 컨텍스트
# ==============================

def build_student_context(student_id: str, target_semester: str = None, full: bool = False) -> str:
    """학생 컨텍스트를 구성합니다.

    Args:
        student_id: 학번
        target_semester: 대상 학기
        full: True면 전체 컨텍스트(수강가능과목, 이수요약 포함),
              False면 최소 컨텍스트(필수 정보만)
    """
    student = get_student(student_id)
    if not student:
        return "등록된 학생 정보가 없습니다."

    if target_semester:
        student["target_semester"] = target_semester

    credits_needed = student["required_credits"] - student["completed_credits"]

    # 채플 이수 현황 (항상 포함)
    chapel_info = _count_chapel_completed(student)
    if chapel_info["is_satisfied"]:
        chapel_status = (
            f"채플: {chapel_info['completed_count']}회 이수 완료 "
            f"(필수 {chapel_info['required_count']}회 충족) "
            f"채플 필수 요건 충족. 절대로 채플 과목(KY101 등)을 추천하지 마세요."
        )
    else:
        remaining_chapel = chapel_info["required_count"] - chapel_info["completed_count"]
        chapel_status = (
            f"채플: {chapel_info['completed_count']}/{chapel_info['required_count']}회 이수 "
            f"(부족: {remaining_chapel}회 필요)"
        )

    # 미이수 필수 과목 요약 (항상 포함)
    unfilled_summary = _build_unfilled_required_summary(student, target_semester)

    # 관심사 (항상 포함)
    interests = student.get("interests", [])
    excluded = student.get("excluded_interests", [])
    interest_text = (
        f"관심 분야: {', '.join(interests)}"
        if interests
        else "관심 분야: 미설정 (관심사를 먼저 질문하세요)"
    )
    if excluded:
        interest_text += f"\n- 제외 분야: {', '.join(excluded)} (이 분야 과목 추천 금지)"

    # 필수 컨텍스트 (항상 주입)
    track_common_ctx = _build_track_common_context(student, target_semester)
    context = f"""## 현재 학생 정보
- 이름: {student['name']}
- 학번: {student['student_id']}
- 학과: {student['department']}
- 주전공: {', '.join(student['major_tracks'])}
- 현재 학기: {student['current_semester']}학기
- 이수 학점: {student['completed_credits']}/{student['required_credits']} (부족: {credits_needed}학점)
- GPA: {student['gpa']}

## 채플 이수 현황
{chapel_status}

{track_common_ctx}

## 카테고리별 졸업요건 현황
{_build_category_requirements_text(student)}

## 현재 수강 중
{chr(10).join(f'- {code}' for code in student.get('in_progress_courses', [])) or '없음'}

## 지금 당장 추천해야 할 과목 (미이수 필수)
{unfilled_summary}

## 선호 시간대
- 선호 요일: {', '.join(student['preferred_days'])}
- 선호 시간: {', '.join(student['preferred_times'])}
- 피하는 시간: {', '.join(student['avoid_times']) if student['avoid_times'] else '없음'}

## 학생 관심사
{interest_text}
"""

    # 확장 컨텍스트 (추천/시간표 키워드가 있을 때만)
    # 주의: 수강 가능 과목은 _build_strict_available_courses_json()로 별도 주입되므로
    # 여기서는 텍스트 요약만 포함 (LLM은 JSON 데이터를 우선 사용)
    if full:
        completed_summary = _build_completed_history_text(student)

        context += f"""
## 이수 완료 과목 요약
{completed_summary}

## 융합전공/특화트랙
- 융합전공: {student.get('convergence_major', '설정 안 함')}
- 특화트랙: {student.get('specialized_track', '설정 안 함')}
"""
    return context


def build_curriculum_context(student: dict, target_semester: str = None, full: bool = False) -> str:
    """교육과정, 이수구분 검증 등 추가 컨텍스트를 생성합니다.

    full=False일 때는 트랙별 필수 과목만 간결하게 반환합니다.
    """
    parts = []

    try:
        track_remaining = get_required_remaining_by_track(student, target_semester)
        if track_remaining:
            lines = []
            for c in track_remaining[:10]:
                times = ", ".join(f"{d} {s}~{e}" for d, s, e in c.get("time_slots", []))
                time_str = f" [{times}]" if times else ""
                lines.append(f"- {c['code']} {c['name']} ({c['credits']}학점){time_str}")
            parts.append(f"## 트랙별 미이수 필수 과목\n{chr(10).join(lines)}")
        else:
            parts.append("## 트랙별 미이수 필수 과목\n없음 (모든 필수 과목 이수 완료)")
    except Exception:
        parts.append("## 트랙별 미이수 필수 과목\n데이터 로딩 실패")

    if full:
        try:
            validation = validate_completed_categories(student)
            mismatched = validation["mismatched_courses"]
            if mismatched:
                mismatch_lines = []
                for m in mismatched[:5]:
                    mismatch_lines.append(
                        f"- {m['code']} {m['name']}: 시스템 기준 '{m['curriculum_type']}' "
                        f"(코드 기준 '{m['inferred_type']}')"
                    )
                parts.append(f"## 이수구분 검증 결과 (확인 필요)\n{chr(10).join(mismatch_lines)}")
        except Exception:
            pass

    return "\n\n".join(parts) if parts else ""


# ==============================
# 관심사 추출
# ==============================

# 사용자가 싫어하는/제외하는 분야 패턴
_NEGATIVE_PATTERNS = [
    ("법률", ["법률", "법", "법학"]),
    ("정치", ["정치", "정치학"]),
    ("사회", ["사회", "사회학"]),
    ("인문", ["인문", "인문학"]),
    ("자연과학", ["자연과학", "물리", "화학", "생물"]),
    ("신학", ["신학", "신학과"]),
    ("의학", ["의학", "의대"]),
]


def _detect_negative_interests(user_message: str) -> list[str]:
    """사용자 메시지에서 싫어하는/제외하는 분야를 감지합니다."""
    msg_lower = user_message.lower()
    negatives = []

    neg_words = ["싫어", "빼", "제외", "안 좋아", "관심 없", "듣기 싫", "원하지 않", "말고", "빼고"]
    has_negation = any(nw in msg_lower for nw in neg_words)
    if not has_negation:
        return []

    for label, keywords in _NEGATIVE_PATTERNS:
        for kw in keywords:
            if kw in msg_lower:
                negatives.append(label)
                break

    return negatives


_INTEREST_PATTERNS = [
    ("AI", ["ai", "인공지능"]),
    ("프로그래밍", ["프로그래밍", "코딩", "파이썬", "python"]),
    ("데이터", ["데이터", "분석", "빅데이터"]),
    ("운동", ["운동", "스포츠", "체육", "축구", "농구", "테니스", "등산", "트래킹"]),
    ("음악", ["음악", "악기", "보컬"]),
    ("영어", ["영어", "어학"]),
    ("심리", ["심리", "심리학"]),
    ("철학", ["철학"]),
    ("경제", ["경제", "경영"]),
    ("보안", ["보안", "해킹", "사이버"]),
    ("웹개발", ["웹", "프론트엔드", "백엔드"]),
    ("게임", ["게임"]),
    ("로봇", ["로봇"]),
    ("IoT", ["iot", "임베디드", "센서"]),
    ("XR", ["xr", "vr", "ar", "메타버스", "가상현실"]),
    ("디자인", ["디자인", "ui", "ux"]),
    ("글쓰기", ["글쓰기", "에세이", "논문"]),
    ("커뮤니케이션", ["커뮤니케이션", "발표", "면접"]),
    ("리더십", ["리더십", "팀워크"]),
    ("봉사", ["봉사", "사회봉사"]),
    ("기독교", ["기독교", "성서", "교회"]),
    ("수리", ["수리", "수학", "통계"]),
    ("반도체", ["반도체", "칩"]),
    ("클라우드", ["클라우드", "aws", "cloud"]),
    ("법률", ["법률", "법학", "법"]),
    ("정치", ["정치", "정책"]),
    ("사회", ["사회", "복지"]),
    ("인문", ["인문", "역사", "문화"]),
    ("과학", ["과학", "물리", "화학", "생물", "천문", "지구과학", "자연과학"]),
    ("언론", ["언론", "미디어", "방송"]),
]


def detect_interest_keywords(user_message: str) -> tuple:
    """사용자 메시지에서 관심 키워드와 제외 키워드를 추출합니다.

    Returns:
        (positive_interests, negative_interests) 튜플
    """
    negatives = _detect_negative_interests(user_message)

    msg_lower = user_message.lower()
    positives = []
    for label, keywords in _INTEREST_PATTERNS:
        for kw in keywords:
            if kw in msg_lower:
                positives.append(label)
                break

    if negatives:
        positives = [p for p in positives if p not in negatives]

    return positives, negatives


# ==============================
# 선호 추출
# ==============================

def _extract_preference_from_message(user_message: str) -> dict:
    """사용자 메시지에서 선호 시간대 정보를 추출합니다."""
    msg = user_message.lower()
    preferences = {}

    days = ["월", "화", "수", "목", "금"]
    for d in days:
        d_target = d + "요일"
        if (d_target in msg or d in msg) and (
            "공강" in msg or "빼" in msg or "제외" in msg
            or "없이" in msg or "없게" in msg or "안돼" in msg
        ):
            preferences.setdefault("remove_days", []).append(d)

    if "월수금" in msg:
        preferences["set_days"] = ["월", "수", "금"]
    elif "화목" in msg:
        preferences["set_days"] = ["화", "목"]

    if ("오전" in msg or "아침" in msg or "1교시" in msg) and (
        "빼" in msg or "기피" in msg or "제외" in msg
        or "안돼" in msg or "싫" in msg or "피해" in msg
    ):
        preferences["avoid_morning"] = True

    if "오후" in msg and (
        "선호" in msg or "위주" in msg or "좋" in msg
        or "맞춰" in msg or "짜줘" in msg
    ):
        preferences["prefer_afternoon"] = True

    return preferences


def _extract_and_save_recommended_courses(ai_response: str, student_id: str):
    """챗봇 답변 텍스트에서 과목 코드를 추출하여 학생 프로필에 추천 과목으로 실시간 반영 및 DB 동기화"""
    if not student_id:
        return
        
    student = get_student(student_id)
    if not student:
        return
        
    # 과목 코드 정규식 (예: SH319, KYC54, FLOW-050 등)
    code_pattern = re.compile(r'\b([A-Z]{2,4}-\d{3}|[A-Z]{2,5}\d{3})\b')
    mentioned_codes = code_pattern.findall(ai_response)
    
    from .data.courses import _get_taken_course_filter, _is_course_already_taken, get_course
    taken_codes, taken_names = _get_taken_course_filter(student)
    
    recommended_codes = []
    for code in mentioned_codes:
        full_c = get_course(code)
        if full_c and code not in recommended_codes:
            # 과거 이수 과목 및 채플 이수 완료 시 추가 제외
            if not _is_course_already_taken(full_c, taken_codes, taken_names):
                recommended_codes.append(code)
                
    student["chatbot_recommended_courses"] = recommended_codes
    from .data.students import save_student
    save_student(student_id, student)


def _validate_recommendation_against_data(ai_response: str, context_courses: list[dict]) -> str:
    """LLM 응답에서 컨텍스트에 없는 과목 코드를 감지하고, 해당 코드를 응답에서 침묵적으로 제거합니다.

    - 유효하지 않은 과목 코드는 응답 텍스트에서 제거되며, 사용자에게 경고를 노출하지 않습니다.
    - 제거된 과목은 대체 유효 과목으로 자동 대체되도록 처리됩니다.
    """
    if not context_courses:
        return ai_response

    # 컨텍스트에 있는 실제 과목 코드集合
    valid_codes = {c.get("code", "") for c in context_courses if c.get("code")}

    # 응답에서 과목 코드 추출
    code_pattern = re.compile(r'\b([A-Z]{2,4}-\d{3}|[A-Z]{2,5}\d{3})\b')
    mentioned_codes = code_pattern.findall(ai_response)

    hallucinated = [code for code in mentioned_codes if code not in valid_codes]

    if not hallucinated:
        return ai_response

    # DB에 없는 과목 코드를 침묵적으로 응답 텍스트에서 제거
    cleaned_response = ai_response
    for code in hallucinated:
        # 과목 코드 참조 패턴 제거 (예: "AS004", "AS004 (AI·SW수학)" 등)
        # 코드만 단독으로 등장하는 경우 코드명만 제거
        cleaned_response = re.sub(
            rf'\b{re.escape(code)}\b(?:\s*\([^)]*\))?',
            '',
            cleaned_response
        )

    # 중복 공백 정리
    cleaned_response = re.sub(r'  +', ' ', cleaned_response).strip()

    return cleaned_response


def _has_recommend_keyword(msg: str) -> bool:
    """메시지에 추천/시간표 관련 키워드가 포함되어 있는지 확인합니다."""
    all_keywords = _RECOMMEND_KEYWORDS | _SCHEDULE_KEYWORDS
    return any(kw in msg for kw in all_keywords)


def _is_liberal_arts_only_request(msg: str) -> bool:
    """사용자가 교양 과목만 추천 요청했는지 확인합니다."""
    patterns = [
        "교양만", "교양 추천", "교양 과목", "教養",
        "교양 듣고 싶", "교양 들어볼", "교양 수업",
        "general only", "liberal only",
    ]
    return any(p in msg for p in patterns)


def _is_major_only_request(msg: str) -> bool:
    """사용자가 전공 과목만 추천 요청했는지 확인합니다."""
    patterns = [
        "전공만", "전공 추천", "전공 과목", "전공 수업",
        "전필", "전선", "전공 필수만", "전공 선택만",
    ]
    return any(p in msg for p in patterns)


# ==============================
# 히스토리 관리
# ==============================

def _trim_history(history: list, max_turns: int = _MAX_HISTORY_TURNS) -> list:
    """대화 히스토리를 최근 N턴만 유지하도록 잘라냅니다."""
    if not history or len(history) <= max_turns:
        return history
    return history[-max_turns:]


def _format_schedules(schedules: list) -> str:
    """시간표 추천 결과를 포맷합니다."""
    if not schedules:
        return "추천 가능한 시간표가 없습니다."

    lines = []
    for i, schedule in enumerate(schedules, 1):
        lines.append(f"### 추천 {i} (총 {schedule['total_credits']}학점)")
        for course in schedule["courses"]:
            times = ", ".join(f"{d} {s}~{e}" for d, s, e in course.get("time_slots", []))
            lines.append(f"  - {course['code']} {course['name']} ({course.get('professor', '')}) [{times}]")
        lines.append("")
    return "\n".join(lines)


# ==============================
# 메인 챗봇 함수
# ==============================

def chat(user_message: str, student_id: str = None, history: list = None, target_semester: str = None) -> dict:
    """챗봇 대화를 처리합니다.

    Returns:
        dict with keys:
            - message: AI 응답 텍스트
            - structured_data: JSON 구조화 데이터 (recommendations 등) 또는 None
    """
    interest_kws, negative_kws = detect_interest_keywords(user_message)
    lower_msg = user_message.lower()
    is_full_context = _has_recommend_keyword(lower_msg)

    # 학생 정보 업데이트 (선호 시간대, 관심사)
    if student_id:
        student = get_student(student_id)
        if student:
            if target_semester:
                student["target_semester"] = target_semester

            prefs = _extract_preference_from_message(user_message)
            updated = False

            if "remove_days" in prefs:
                current_pref = student.get("preferred_days", ["월", "화", "수", "목", "금"])
                for d in prefs["remove_days"]:
                    if d in current_pref:
                        current_pref.remove(d)
                student["preferred_days"] = current_pref
                updated = True

            if "set_days" in prefs:
                student["preferred_days"] = prefs["set_days"]
                updated = True

            if prefs.get("avoid_morning"):
                avoid = student.get("avoid_times", [])
                if "09:00-12:00" not in avoid:
                    student["avoid_times"] = list(set(avoid + ["09:00-12:00"]))
                    updated = True

            if prefs.get("prefer_afternoon"):
                pref_times = student.get("preferred_times", [])
                if "13:00-18:00" not in pref_times:
                    student["preferred_times"] = list(set(pref_times + ["13:00-18:00"]))
                    updated = True

            # 관심사 저장 (누적)
            if interest_kws:
                current_interests = student.get("interests", [])
                for kw in interest_kws:
                    if kw not in current_interests:
                        current_interests.append(kw)
                student["interests"] = current_interests
                updated = True

            # 제외 분야 저장
            if negative_kws:
                excluded = student.get("excluded_interests", [])
                for kw in negative_kws:
                    if kw not in excluded:
                        excluded.append(kw)
                student["excluded_interests"] = excluded
                updated = True

            if updated:
                from .data.students import save_student
                save_student(student_id, student)

    # 시스템 프롬프트 + 히스토리
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        trimmed = _trim_history(history)
        messages.extend(trimmed)

    # 학생 컨텍스트 (full vs minimal)
    if student_id:
        student_context = build_student_context(student_id, target_semester, full=is_full_context)
        messages.append({"role": "system", "content": student_context})

        curriculum_ctx = build_curriculum_context(
            get_student(student_id) or {},
            target_semester,
            full=is_full_context,
        )
        if curriculum_ctx:
            messages.append({"role": "system", "content": curriculum_ctx})

        # 원칙 1: 추천 요청 시 수강 가능 과목을 JSON 형태로 시스템에 주입
        # 백엔드 사전 필터링이 완료된 과목만 LLM에 전달
        if is_full_context:
            student_obj = get_student(student_id)
            if student_obj:
                if target_semester:
                    student_obj["target_semester"] = target_semester
                available_json = _build_strict_available_courses_json(student_obj, limit=60)
                messages.append({
                    "role": "system",
                    "content": (
                        f"## 수강 가능 과목 JSON 데이터 (반드시 이 목록 내에서만 추천하라)\n"
                        f"아래 JSON은 시스템이 사전 필터링(기수강 제거, 채플 완료 제거, 학과 필터링)을 완료한 "
                        f"실제 수강 가능한 과목 목록입니다. 이 목록에 없는 과목/교수/시간을 절대 지어내지 마라.\n\n"
                        f"```json\n{available_json}\n```"
                    ),
                })

    # 시간표 추천
    if "시간표" in lower_msg and student_id:
        student = get_student(student_id)
        if student:
            if target_semester:
                student["target_semester"] = target_semester
            schedules = generate_timetable(student, max_schedules=3)
            schedule_text = _format_schedules(schedules)

            # 스케줄러 fallback 플래그 확인 및 LLM 컨텍스트에 반영
            fallback_msg = ""
            if schedules and schedules[0].get("fallback_reason"):
                fallback_msg = (
                    f"\n\n⚠️ **중요**: 사용자가 선호하는 요일 공강 조건을 요청했으나, "
                    f"해당 조건을 적용하면 필수 과목을 배치할 수 없었습니다. "
                    f"따라서 부득이하게 모든 요일을 포함하여 시간표를 생성했습니다. "
                    f"이 점을 사용자에게 반드시 설명해주세요: "
                    f"\"{schedules[0]['fallback_reason']}\""
                )

            messages.append({
                "role": "system",
                "content": (
                    f"## 시간표 추천 결과\n{schedule_text}\n\n"
                    f"위 시간표를 바탕으로 사용자에게 추천해주세요. "
                    f"반드시 {target_semester or '지정 학기'}에 개설된 과목들이 맞는지 다시 확인하세요."
                    f"{fallback_msg}"
                ),
            })

    # 공지사항
    if "공지" in lower_msg or "알림" in lower_msg:
        student_obj = get_student(student_id) if student_id else None
        keyword_prefs = student_obj.get("keyword_preferences", []) if student_obj else []
        keyword_alerts = student_obj.get("keyword_alerts", []) if student_obj else []
        all_keywords = list(set(keyword_prefs + keyword_alerts))

        if all_keywords:
            keyword_results = filter_notices_by_keywords(all_keywords)
            if keyword_results:
                notice_text = "\n".join(
                    f"- [{n['date']}] {n['title']}: {n.get('content', '')[:80]}"
                    for n in keyword_results[:10]
                )
                messages.append({
                    "role": "system",
                    "content": f"## 키워드 매칭 공지사항 ({', '.join(all_keywords[:5])})\n{notice_text}",
                })

        results = search_notices(user_message)
        if results:
            notice_text = "\n".join(
                f"- [{n['date']}] {n['title']}: {n['content'][:100]}"
                for n in results[:10]
            )
            messages.append({
                "role": "system",
                "content": f"## 관련 공지사항\n{notice_text}",
            })

    # 학사일정
    if "일정" in lower_msg or "스케줄" in lower_msg:
        alerts = get_upcoming_alerts(30)
        if alerts:
            alert_text = "\n".join(
                f"- [{a['start_date']}~{a['end_date']}] {a['title']}: {a['description']}"
                for a in alerts
            )
            messages.append({
                "role": "system",
                "content": f"## 향후 학사일정\n{alert_text}",
            })

    # 관심 과목 추천 (관심사가 있고, 관심사 질문이 아닌 경우에만)
    # "교양만 추천해줘", "전공만 추천해줘" 등 구체적 유형 지정 시에는 항상 실행
    liberal_only = _is_liberal_arts_only_request(lower_msg)
    major_only = _is_major_only_request(lower_msg)
    # "관심사가 뭐야?", "관심 뭐 있어?" 등 순수 관심사 문의일 때만 스킵
    # "추천해줘", "교양만 추천" 등 추천 요청 시에는 항상 실행
    is_pure_interest_question = any(w in lower_msg for w in ["관심사", "관심 뭐", "뭐가 관심"])
    has_type_specifier = liberal_only or major_only
    skip_interest = is_pure_interest_question and not has_type_specifier

    if interest_kws and student_id and not skip_interest:
        student_obj = get_student(student_id)
        if student_obj:
            for kw in interest_kws:
                try:
                    interest_results = get_interest_matching_courses(student_obj, [kw])

                    # 교양만 요청 시 교양 과목만 필터링
                    if liberal_only:
                        interest_results = [
                            r for r in interest_results
                            if r["category"] in ("교양선택", "교양필수")
                        ]
                    # 전공만 요청 시 전공/계열공통만 필터링
                    elif major_only:
                        interest_results = [
                            r for r in interest_results
                            if r["category"] in ("전공필수", "전공선택", "계열공통")
                        ]
                    else:
                        # 기본: 교양 + 전공 모두 포함 (교양 우선순위 약간 높임)
                        liberal = [r for r in interest_results if r["category"] in ("교양선택", "교양필수")]
                        major = [r for r in interest_results if r["category"] in ("전공필수", "전공선택", "계열공통")]
                        # 교양 4개 + 전공 4개로 혼합 구성
                        interest_results = liberal[:4] + major[:4]

                    if interest_results:
                        lines = []
                        for item in interest_results[:8]:
                            c = item["course"]
                            prof = c.get("professor") or "미정"
                            lines.append(
                                f"- {c['code']} {c['name']} ({c['credits']}학점) (담당교수: {prof}) "
                                f"[{item['category']}] - {item['reason']}"
                            )
                        label = f"'{kw}' 교양 추천" if liberal_only else f"'{kw}' 관심 과목 추천"
                        messages.append({
                            "role": "system",
                            "content": f"## {label} 결과\n{chr(10).join(lines)}",
                        })
                except Exception:
                    pass

    messages.append({"role": "user", "content": user_message})

    # 데모 모드 (API 키 없음)
    if not gemini_client:
        system_context = ""
        for m in messages:
            if m["role"] == "system" and "시간표" in m["content"]:
                system_context += "\n[추천 시간표 정보 발견]\n" + m["content"]
            if m["role"] == "system" and "공지사항" in m["content"]:
                system_context += "\n[공지사항 정보 발견]\n" + m["content"]
            if m["role"] == "system" and "트랙별" in m["content"]:
                system_context += "\n[트랙별 필수과목 정보 발견]\n" + m["content"]
            if m["role"] == "system" and "이수구분" in m["content"]:
                system_context += "\n[이수구분 검증 정보 발견]\n" + m["content"]
            if m["role"] == "system" and "관심 과목" in m["content"]:
                system_context += "\n[관심 과목 추천 정보 발견]\n" + m["content"]

        reply = (
            "🎓 **그레듀 조교 답변 (데모 모드)**\n\n"
            "현재 `GEMINI_API_KEY` 환경 변수가 설정되지 않아 인공지능 실시간 대화는 불가능하지만, "
            "시스템 프롬프트 및 데이터를 기반으로 가상 상담을 제공합니다.\n\n"
        )
        if "시간표" in user_message or "추천" in user_message:
            reply += f"학번 및 선호 요일 분석을 마쳤습니다. 선택하신 학기({target_semester or '2026-2학기'})의 시간표 탭에서 추천 배치가 완료되었습니다."
        elif "공지" in user_message or "일정" in user_message:
            reply += "현재 관련 공지사항이 확인됩니다. 알림 탭에서 매칭 리스트를 확인하실 수 있습니다."
        elif interest_kws:
            reply += f"'{', '.join(interest_kws)}' 관련 과목을 추천 목록에 포함하였습니다."
        else:
            reply += (
                f"질문해주신 '{user_message}'에 관해 확인 중입니다. "
                "졸업 자격 심사 기준 또는 전공 필수 이수 학점 상태를 확인하고 싶으시다면 "
                "상세 탭을 조회해 보세요!"
            )
        if system_context:
            reply += f"\n\n[시스템 데이터]\n{system_context[:500]}"
        reply_with_hanja = hanja_to_hangul(reply)
        _extract_and_save_recommended_courses(reply_with_hanja, student_id)
        return {"message": reply_with_hanja, "structured_data": None}

    # Gemini API 호출: 시스템 프롬프트 + 히스토리 + 사용자 메시지를 contents로 결합
    try:
        system_parts = []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])

        chat_history = []
        for m in messages:
            if m["role"] == "user":
                chat_history.append({"role": "user", "parts": [{"text": m["content"]}]})
            elif m["role"] == "assistant":
                chat_history.append({"role": "model", "parts": [{"text": m["content"]}]})

        system_text = "\n\n".join(system_parts) if system_parts else ""

        # 원칙 3: Temperature를 0.0으로 고정 (시간표 추천은 창의성보다 정확성)
        chat = gemini_client.chats.create(
            model=_model_name,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=2000,
            ),
            history=chat_history,
        )

        full_prompt = system_text + "\n\n[사용자 질문]\n" + user_message

        response = chat.send_message(full_prompt)
        reply_with_hanja = hanja_to_hangul(response.text)

        # 추천된 과목이 컨텍스트에 존재하는지 검증
        if student_id and _has_recommend_keyword(lower_msg):
            try:
                student_obj = get_student(student_id)
                if student_obj:
                    available = get_available_courses(student_obj)
                    reply_with_hanja = _validate_recommendation_against_data(reply_with_hanja, available)
            except Exception:
                pass

        # 원칙 4: Structured Output 파싱
        clean_text, structured_data = _parse_structured_output(reply_with_hanja)

        _extract_and_save_recommended_courses(reply_with_hanja, student_id)
        return {"message": clean_text, "structured_data": structured_data}
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "limit" in error_msg.lower():
            return {
                "message": (
                    "⚠️ **Gemini API 호출 제한(Quota Exceeded) 초과 안내**\n\n"
                    "현재 설정된 Gemini API 키의 무료 호출 한도를 초과하였거나, 한도가 0으로 제한되어 있습니다.\n\n"
                    "**해결 방법:**\n"
                    "1. **데모 모드 사용:** 프로젝트 루트의 `.env` 파일에서 `GEMINI_API_KEY` 값을 비우거나 삭제하면 로컬 시뮬레이션 기반의 데모 조교 모드로 정상 작동합니다.\n"
                    "2. **API 키 갱신:** [Google AI Studio](https://aistudio.google.com/)에서 새 API 키를 발급받아 `.env` 파일의 `GEMINI_API_KEY`에 등록해 주세요.\n"
                    "3. **모델 변경:** `.env` 파일의 `GEMINI_MODEL`을 `gemini-1.5-flash` 등으로 변경하여 다른 쿼터 한도가 적용되는지 시도할 수 있습니다."
                ),
                "structured_data": None,
            }
        elif "api_key" in error_msg.lower() or "invalid" in error_msg.lower():
            return {
                "message": (
                    "⚠️ **Gemini API 키 오류 안내**\n\n"
                    "설정된 API 키가 유효하지 않거나 잘못되었습니다. 프로젝트 루트의 `.env` 파일에 유효한 `GEMINI_API_KEY`가 올바르게 입력되어 있는지 확인해 주세요."
                ),
                "structured_data": None,
            }
        return {"message": f"API 호출 중 오류가 발생했습니다: {error_msg}", "structured_data": None}
