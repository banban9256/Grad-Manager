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
import google.generativeai as genai

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
if api_key:
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(
        model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        generation_config=genai.GenerationConfig(
            temperature=0.4,
            max_output_tokens=1500,
        ),
    )
else:
    gemini_model = None

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

# 추천 관련 키워드 (컨텍스트 풀 주입 트리거)
_RECOMMEND_KEYWORDS = {"추천", "들을까", "들어", "수강", "신청", "시간표", "짜줘", "짜자", "추천해"}
_SCHEDULE_KEYWORDS = {"시간표", "스케줄", "공강", "연강"}


# ==============================
# 채플 관련
# ==============================

def _count_chapel_completed(student: dict) -> dict:
    """채플 이수 현황을 계산합니다.

    채플은 AISW 학과 수업이 아니어도 필수 횟수만 채우면 인정됩니다.
    따라서 KY100/KY101/KY201/KY304 등 모든 채플 과목을 이수 횟수에 포함합니다.
    """
    completed = set(student.get("completed_courses", []))
    chapel_done = completed & _ALL_CHAPEL_CODES

    return {
        "completed_count": len(chapel_done),
        "required_count": _CHAPEL_REQUIRED_COUNT,
        "is_satisfied": len(chapel_done) >= _CHAPEL_REQUIRED_COUNT,
        "completed_codes": list(chapel_done),
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
                            lines.append(f"  - {c['code']} {c['name']} ({c['credits']}학점){time_str} [{cat}]")
        except Exception:
            pass

    return "\n".join(lines)


def _build_available_courses_summary(available: list, limit: int = 15) -> str:
    """수강 가능 과목 요약을 생성합니다."""
    lines = []
    for c in available[:limit]:
        times = ", ".join(f"{d} {s}~{e}" for d, s, e in c.get("time_slots", []))
        time_str = f" [{times}]" if times else ""
        lines.append(f"- {c['code']} {c['name']} ({c['credits']}학점){time_str}")

    if not lines:
        return "수강 가능 과목 없음"
    return "\n".join(lines)


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
    if full:
        available = get_available_courses(student)
        completed_summary = _build_completed_history_text(student)

        context += f"""
## 이수 완료 과목 요약
{completed_summary}

## 수강 가능 과목 (일부, 총 {len(available)}개 중 상위 15개)
{_build_available_courses_summary(available)}

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
    ("자연과학", ["자연과학", "물리", "화학", "생물"]),
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


def _has_recommend_keyword(msg: str) -> bool:
    """메시지에 추천/시간표 관련 키워드가 포함되어 있는지 확인합니다."""
    all_keywords = _RECOMMEND_KEYWORDS | _SCHEDULE_KEYWORDS
    return any(kw in msg for kw in all_keywords)


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

def chat(user_message: str, student_id: str = None, history: list = None, target_semester: str = None) -> str:
    """챗봇 대화를 처리합니다."""
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
                # TODO: 추후 DB 저장 필요 (현재 in-memory SQLite 연동)
                from .data.students import STUDENTS
                STUDENTS[student_id] = student

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
    is_asking_about_interests = any(w in lower_msg for w in ["관심", "관심사", "뭐 듣", "추천해", "추천해줘", "들어볼까", "좋은 과목"])
    if interest_kws and student_id and not is_asking_about_interests:
        student_obj = get_student(student_id)
        if student_obj:
            for kw in interest_kws:
                try:
                    interest_results = get_interest_matching_courses(student_obj, [kw])
                    if interest_results:
                        lines = []
                        for item in interest_results[:8]:
                            c = item["course"]
                            lines.append(
                                f"- {c['code']} {c['name']} ({c['credits']}학점) "
                                f"[{item['category']}] - {item['reason']}"
                            )
                        messages.append({
                            "role": "system",
                            "content": f"## '{kw}' 관심 과목 추천 결과\n{chr(10).join(lines)}",
                        })
                except Exception:
                    pass

    messages.append({"role": "user", "content": user_message})

    # 데모 모드 (API 키 없음)
    if not gemini_model:
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
        return reply

    # Gemini API 호출: 시스템 프롬프트 + 히스토리 + 사용자 메시지를 contents로 결합
    try:
        # Gemini는 contents 배열에 system instruction과 대화를 결합
        contents = []
        
        # 시스템 프롬프트와 컨텍스트를 하나의 텍스트로 결합
        system_parts = []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
        
        # 대화 히스토리 (user/assistant)
        chat_history = []
        for m in messages:
            if m["role"] == "user":
                chat_history.append({"role": "user", "parts": [m["content"]]})
            elif m["role"] == "assistant":
                chat_history.append({"role": "model", "parts": [m["content"]]})
        
        # 시스템 컨텍스트를 첫 번째 user 메시지 앞에 추가
        system_text = "\n\n".join(system_parts) if system_parts else ""
        
        # Gemini chat 세션 생성
        chat = gemini_model.start_chat(history=chat_history)
        
        # 시스템 프롬프트 + 컨텍스트 + 사용자 메시지 결합
        full_prompt = system_text + "\n\n[사용자 질문]\n" + user_message
        
        response = chat.send_message(full_prompt)
        return hanja_to_hangul(response.text)
    except Exception as e:
        return f"API 호출 중 오류가 발생했습니다: {str(e)}"
