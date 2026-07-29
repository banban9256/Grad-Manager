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
from pydantic import BaseModel, Field
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

# ==============================
# Gemini Structured Outputs 스키마 정의
# ==============================
class CourseSchedule(BaseModel):
    day: str = Field(description="요일 (예: '월', '화', '수')")
    start: str = Field(description="시작 시간 (예: '09:30')")
    end: str = Field(description="종료 시간 (예: '10:45')")

class TimetableCourse(BaseModel):
    course_name: str = Field(description="과목명")
    course_code: str = Field(description="과목 코드 (예: 'SH342')")
    type: str = Field(description="이수 구분 (예: '전공필수', '전공선택', '교양필수', '교양선택', '계열공통', '일반선택')")
    credits: float = Field(description="학점 수")
    professor: str = Field(description="교수명")
    schedule: List[CourseSchedule] = Field(description="요일별 강의 시간 정보 목록")
    reason: str = Field(description="이 과목을 추천하는 사유")

class TimetableData(BaseModel):
    total_credits: float = Field(description="추천된 시간표의 총 학점")
    total_courses: int = Field(description="추천된 총 과목 수")
    empty_days: List[str] = Field(description="공강 요일 목록 (예: ['화'])")
    courses: List[TimetableCourse] = Field(description="추천된 시간표 내 과목 리스트")

class GraduResponseSchema(BaseModel):
    chat_message: str = Field(description="사용자에게 보낼 친절한 설명 메시지 (추천 시간표에 대한 요약 및 조언 포함)")
    timetable_data: Optional[TimetableData] = Field(None, description="시간표를 새로 추천하는 경우에만 포함하며, 그 외 단순 질의응답 시에는 null로 설정합니다.")

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
_CHAPEL_REQUIRED_COUNT = 4

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


def _build_strict_available_courses_json(student: dict, limit: int = 150) -> str:
    """원칙 1: 백엔드 사전 필터링 완료된 수강 가능 과목을 5단계 우선순위별로 그룹핑하여 JSON으로 구성합니다.

    - 1순위: 진로와상담, 채플 등 필수 다회 이수 미달 과목
    - 2순위: AISW 계열공통 미이수 과목
    - 3순위: AISW 교양필수 미이수 과목
    - 4순위: 트랙/특화/융합전공 전공선택 과목 (사용자 선호 반영)
    - 5순위: 학년 맞춤 전공선택 과목 (학생 학년 일치)
    """
    available = get_available_courses(student)

    if not available:
        return json.dumps({"must_take_first": [], "electives": []}, ensure_ascii=False, indent=1)

    is_aisw = (
        student.get("department") in ["인공지능소프트웨어학부", "컴퓨터소프트웨어학과", "소프트웨어학과"]
        or "소프트웨어" in student.get("department", "")
        or "aisw" in student.get("department", "").lower()
    )

    # 1. SQLite DB 로드하여 과목 메타정보(권장 학년, 프로그램/트랙명) 조회 및 캐싱
    import sqlite3
    from pathlib import Path
    
    db_path = Path(__file__).resolve().parent.parent / "gradmanager.db"
    course_meta = {}
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.course_code, cc.recommended_grade, p.program_name
                FROM courses c
                LEFT JOIN curriculum_courses cc ON c.course_id = cc.course_id
                LEFT JOIN programs p ON cc.program_id = p.program_id
            """)
            for code, rec_grade, prog_name in cursor.fetchall():
                if code not in course_meta:
                    course_meta[code] = {"recommended_grade": None, "programs": set()}
                if rec_grade:
                    course_meta[code]["recommended_grade"] = int(rec_grade)
                if prog_name:
                    course_meta[code]["programs"].add(prog_name)
            conn.close()
        except Exception:
            pass

    # 2. 학생 학년 및 선호 트랙 정보 취득
    student_grade = 3
    try:
        student_grade = int(student.get("current_grade") or 3)
    except:
        pass

    preferred_tracks = set()
    for track in student.get("major_tracks", []):
        preferred_tracks.add(track)
    for interest in student.get("interests", []):
        preferred_tracks.add(interest)
    if student.get("specialized_track"):
        preferred_tracks.add(student.get("specialized_track"))
    if student.get("convergence_major"):
        preferred_tracks.add(student.get("convergence_major"))

    # 3. 5단계 우선순위 가중치 계산 및 정렬
    scored_courses = []
    for c in available:
        code = c.get("code", "")
        ctype = c.get("type", "일반선택")
        cname = c.get("name", "")
        prefix = "".join(ch for ch in code if ch.isalpha())

        # AISW 학생인 경우 타 학과 전공(접두사가 SH, DS, AI 가 아니고 교양/계공이 아닌 경우)은 배제
        if is_aisw:
            is_liberal = prefix in {"KY", "KYC", "KYA", "KYD"}
            is_common = prefix in {"FLOW"}
            is_aisw_major = prefix in {"SH", "DS", "AI"}
            if not (is_liberal or is_common or is_aisw_major) and ctype in ["전공선택", "전공필수"]:
                continue

        score = 0
        
        # 1순위: 진로와상담, 채플 등 필수 다회 이수 미달
        is_chapel = code in _ALL_CHAPEL_CODES or "채플" in cname
        is_jinsang = "진로와상담" in cname or code == "KY410"
        is_sahoegil = "사회생활길잡이" in cname
        is_daehakgil = "대학생활길잡이" in cname
        
        if is_chapel or is_jinsang or is_sahoegil or is_daehakgil:
            score += 5000
        # 2순위: AISW 계열공통 미이수
        elif ctype == "계열공통" and is_aisw:
            score += 4000
        # 3순위: AISW 교양필수 미이수
        elif ctype == "교양필수" and is_aisw:
            score += 3000
        # 4순위: 트랙/특화/융합전공 (선호하는 트랙 매칭)
        else:
            meta = course_meta.get(code, {"recommended_grade": None, "programs": set()})
            is_track_match = False
            for prog in meta["programs"]:
                if any(pt in prog for pt in preferred_tracks if pt):
                    is_track_match = True
                    break
            
            if is_track_match and ctype == "전공선택":
                score += 2000
            # 5순위: 학년 맞춤 전공 선택
            elif ctype == "전공선택" and is_aisw:
                rec_grade = meta["recommended_grade"]
                if rec_grade == student_grade:
                    score += 1000
                else:
                    score += 500
            else:
                score += 100

        course_entry = {
            "code": code,
            "name": cname,
            "credits": c.get("credits", 3),
            "type": ctype,
            "professor": c.get("professor") or "미정",
            "time_slots": c.get("time_slots", []),
            "classroom": c.get("room") or "미정",
            "score": score,
        }
        scored_courses.append(course_entry)

    # 4. Score 기준 내림차순 정렬 및 그룹 분할
    # Score 3000 이상 -> must_take_first (1~3순위)
    # Score 3000 미만 -> electives (4~5순위 및 기타)
    scored_courses.sort(key=lambda x: -x["score"])

    must_take_first = []
    electives = []

    for entry in scored_courses:
        # JSON 전송 시 score 필드는 제거
        score = entry.pop("score")
        if score >= 3000:
            must_take_first.append(entry)
        else:
            electives.append(entry)

    # limit 제한 적용
    total_must = len(must_take_first)
    if total_must >= limit:
        must_take_first = must_take_first[:limit]
        electives = []
    else:
        electives = electives[:(limit - total_must)]

    result = {
        "must_take_first": must_take_first,
        "electives": electives
    }

    return json.dumps(result, ensure_ascii=False, indent=1)


def _build_student_profile_json(student: dict) -> str:
    """학생 학번 및 미이수 데이터를 명확한 JSON 형태로 주입합니다."""
    profile = {
        "student_id": student.get("student_id"),
        "admission_year": student.get("enrolled_year"),
        "department": student.get("department"),
        "major_tracks": student.get("major_tracks", []),
        "current_semester": student.get("current_semester"),
        "completed_credits": student.get("completed_credits"),
        "required_credits": student.get("required_credits"),
        "target_semester": student.get("target_semester"),
        "specialized_track": student.get("specialized_track"),
        "convergence_major": student.get("convergence_major"),
        "interests": student.get("interests", []),
        "preferred_days": student.get("preferred_days", []),
        "preferred_times": student.get("preferred_times", []),
        "avoid_times": student.get("avoid_times", []),
        "in_progress_courses": student.get("in_progress_courses", []),
        "graduation_requirements": get_graduation_credit_summary(student),
        "remaining_required_this_semester": get_all_remaining_required_for_semester(student, student.get("target_semester")),
        "unfinished_track_common": _get_unfinished_track_common(student, student.get("target_semester")),
    }
    return json.dumps(profile, ensure_ascii=False, indent=2)


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
    msg_no_space = msg.replace(" ", "")
    preferences = {}

    days = ["월", "화", "수", "목", "금"]
    
    # 요일 오탐을 방지하기 위한 마스킹 단어 목록
    mask_words = [
        "수업", "수강", "수학", "필수", "이수", "교수", "소수", "복수", "연수", "일수", "횟수", "기수강",
        "목적", "과목", "항목", "주목", "목록", "골목",
        "장학금", "금지", "납부금", "세금", "지금", "예금", "요금", "입금",
        "화학", "문화", "특화", "변화", "소화", "대화", "시각화",
        "개월", "월말", "월별", "세월", "금요일", "목요일", "수요일", "화요일", "월요일"
    ]
    
    # 단, 'X요일' 패턴은 미리 요일로 인식하고 마스킹해야 함
    detected_days_from_yoil = set()
    for d in days:
        if d + "요일" in msg:
            detected_days_from_yoil.add(d)
            
    masked_msg = msg
    for word in mask_words:
        masked_msg = masked_msg.replace(word, "X" * len(word))
        
    # 최종 감지된 요일 목록
    detected_days = set(detected_days_from_yoil)
    for d in days:
        if d in masked_msg:
            detected_days.add(d)

    # 1. 요일별 개별 처리 (remove_days 및 set_days)
    remove_keywords = ["공강", "빼", "제외", "없이", "없게", "안돼", "싫", "피해", "피하", "x", "안들", "안듣", "않"]
    set_keywords = ["만", "위주", "선호", "들", "듣", "갈래", "가고", "짜줘", "듣기", "신청", "수업", "수강"]
    
    remove_days = []
    set_days = []
    
    # 각 요일별로 remove인지 set인지 컨텍스트 판단
    # masked_msg 기준으로 판단하여 오탐 방지
    for d in days:
        if d not in detected_days:
            continue
            
        is_remove = False
        is_set = False
        
        has_yoil = d + "요일" in msg
        search_target = d + "요일" if has_yoil else d
        idx = msg.find(search_target)
        
        while idx != -1:
            # 요일 뒤 15글자를 가져와서 공백을 제거한 뒤 검사
            context = msg[idx:idx+15].replace(" ", "")
            
            if any(rk in context for rk in remove_keywords):
                is_remove = True
            elif any(sk in context for sk in set_keywords):
                is_set = True
                
            idx = msg.find(search_target, idx + 1)
            
        if not is_remove and not is_set:
            if any(rk in msg_no_space for rk in remove_keywords):
                is_remove = True
            elif any(sk in msg_no_space for sk in set_keywords):
                is_set = True
            else:
                is_set = True
                
        if is_remove:
            remove_days.append(d)
        elif is_set:
            set_days.append(d)

    if remove_days:
        preferences["remove_days"] = remove_days
    if set_days:
        preferences["set_days"] = set_days

    # 2. 오전/오후 선호 및 기피 분석
    has_morning = "오전" in msg or "아침" in msg or "1교시" in msg
    has_afternoon = "오후" in msg

    prefer_keywords = ["선호", "위주", "좋", "맞춰", "짜줘", "원해", "원함", "하고싶", "듣고싶"]
    avoid_keywords = ["빼", "기피", "제외", "안돼", "싫", "피해", "피하", "없이", "없게", "안들", "안듣", "하지않", "않고싶"]

    has_prefer = any(pk in msg_no_space for pk in prefer_keywords)
    has_avoid = any(ak in msg_no_space for ak in avoid_keywords)

    if has_morning:
        if has_avoid:
            preferences["avoid_morning"] = True
        elif has_prefer:
            preferences["prefer_morning"] = True

    if has_afternoon:
        if has_avoid:
            preferences["avoid_afternoon"] = True
        elif has_prefer:
            preferences["prefer_afternoon"] = True

    # 3. 학점 요건 감지 (예: "18학점", "15학점" 등)
    credits_match = re.search(r'(\d+)\s*학점', msg)
    if credits_match:
        try:
            val = int(credits_match.group(1))
            if 6 <= val <= 24:
                preferences["target_credits"] = val
        except Exception:
            pass

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
    
    from .data.courses import _is_course_already_taken, get_course
    
    recommended_codes = []
    for code in mentioned_codes:
        full_c = get_course(code)
        if full_c and code not in recommended_codes:
            # 과거 이수 과목 및 채플 이수 완료 시 추가 제외
            if not _is_course_already_taken(full_c, student):
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

    # 컨텍스트에 있는 실제 과목 코드
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
    # 사용자의 대화 입력 텍스트에서 실제 개설 과목명 매칭 수집하여 선주입
    if student_id:
        student_temp = get_student(student_id)
        if student_temp:
            from .data.courses import load_courses, _is_course_already_taken
            courses_db = load_courses()
            matched_codes = []
            clean_msg = user_message.replace(" ", "").lower()
            
            for code, course in courses_db.items():
                name = course.get("name", "")
                clean_name = name.replace(" ", "").lower()
                
                # 과목명이 최소 3글자 이상이고 사용자 입력 텍스트에 포함되어 있다면
                if len(clean_name) >= 3 and clean_name in clean_msg:
                    if not _is_course_already_taken(course, student_temp):
                        matched_codes.append(code)
                # 예외 대응 (AISW수학, UIUX 등)
                elif "aisw수학" in clean_msg and clean_name == "ai·sw수학":
                    if not _is_course_already_taken(course, student_temp):
                        matched_codes.append(code)
                elif "uiux" in clean_msg and "ui" in clean_name and "ux" in clean_name:
                    if not _is_course_already_taken(course, student_temp):
                        matched_codes.append(code)
            
            # 기존 추천 과목 풀에 병합
            if matched_codes:
                current_recs = student_temp.get("chatbot_recommended_courses", [])
                for code in matched_codes:
                    if code not in current_recs:
                        current_recs.append(code)
                student_temp["chatbot_recommended_courses"] = current_recs
                from .data.students import save_student
                save_student(student_id, student_temp)

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

            if "target_credits" in prefs:
                student["target_credits"] = prefs["target_credits"]
                updated = True

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

            # 오전 기피
            if prefs.get("avoid_morning"):
                avoid = student.get("avoid_times", [])
                if "09:00-12:00" not in avoid:
                    student["avoid_times"] = list(set(avoid + ["09:00-12:00"]))
                # 선호 시간대에서 오전("09:00-12:00") 제거
                pref_times = student.get("preferred_times", [])
                if "09:00-12:00" in pref_times:
                    pref_times.remove("09:00-12:00")
                    student["preferred_times"] = pref_times
                updated = True

            # 오전 선호
            if prefs.get("prefer_morning"):
                pref_times = student.get("preferred_times", [])
                if "09:00-12:00" not in pref_times:
                    student["preferred_times"] = list(set(pref_times + ["09:00-12:00"]))
                # 피하는 시간대에서 오전("09:00-12:00") 제거
                avoid = student.get("avoid_times", [])
                if "09:00-12:00" in avoid:
                    avoid.remove("09:00-12:00")
                    student["avoid_times"] = avoid
                updated = True

            # 오후 선호
            if prefs.get("prefer_afternoon"):
                pref_times = student.get("preferred_times", [])
                if "13:00-18:00" not in pref_times:
                    student["preferred_times"] = list(set(pref_times + ["13:00-18:00"]))
                # 피하는 시간대에서 오후("13:00-18:00") 제거
                avoid = student.get("avoid_times", [])
                if "13:00-18:00" in avoid:
                    avoid.remove("13:00-18:00")
                    student["avoid_times"] = avoid
                updated = True

            # 오후 기피
            if prefs.get("avoid_afternoon"):
                avoid = student.get("avoid_times", [])
                if "13:00-18:00" not in avoid:
                    student["avoid_times"] = list(set(avoid + ["13:00-18:00"]))
                # 선호 시간대에서 오후("13:00-18:00") 제거
                pref_times = student.get("preferred_times", [])
                if "13:00-18:00" in pref_times:
                    pref_times.remove("13:00-18:00")
                    student["preferred_times"] = pref_times
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
                student_json = _build_student_profile_json(student_obj)
                messages.append({
                    "role": "system",
                    "content": (
                        "## 학생 학번 및 미이수 JSON 데이터\n"
                        "아래 JSON은 학생의 학번, 입학년도, 학과, 미이수 필수 과목 정보, 특화트랙, 관심사 등을 포함합니다. "
                        "이 JSON 데이터를 반드시 참조하여 추천하라. 데이터에 없는 정보는 사용하지 마라.\n\n"
                        f"```json\n{student_json}\n```"
                    ),
                })
                available_json = _build_strict_available_courses_json(student_obj, limit=150)
                messages.append({
                    "role": "system",
                    "content": (
                        "## 수강 가능 과목 JSON 데이터 (우선순위 그룹핑)\n"
                        "아래 JSON은 시스템이 사전 필터링 및 우선순위 그룹핑을 완료한 실제 수강 가능한 과목 목록입니다.\n"
                        "반드시 must_take_first 배열에 있는 과목부터 최우선으로 시간표에 욱여넣은 뒤, 남는 학점을 electives 배열에서 채워 시간표를 구성하십시오. "
                        "이 목록에 없는 과목/교수/시간을 절대 임의로 지어내지 마십시오.\n\n"
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

    # 학사일정 및 등록금, 수강신청 관련 질문 시 RAG 주입
    is_schedule_query = any(w in lower_msg for w in ["일정", "스케줄", "등록", "수강신청", "개강", "시험", "고사", "휴학", "복학", "졸업"])
    if is_schedule_query and student_id:
        from .data.academic_schedule import get_all_schedules
        all_schedules = get_all_schedules()
        matched_schedules = []
        
        # 사용자가 "등록"에 대해 묻는다면 반드시 "등록금 납부" 관련 일정을 매칭
        is_tuition_query = "등록" in lower_msg
        
        for s in all_schedules:
            name = s.get("event_name", "") or s.get("title", "")
            desc = s.get("description", "") or ""
            
            if is_tuition_query:
                # 등록기간 검색인 경우 '등록금 납부' 또는 '등록기간' 만 정확히 매칭 (수강신청과 구별)
                if "등록금" in name or "등록금" in desc or "등록기간" in name or "등록기간" in desc:
                    matched_schedules.append(s)
            else:
                # 일반 일정 검색
                keywords = ["일정", "스케줄", "등록", "수강신청", "개강", "시험", "고사", "휴학", "복학", "졸업"]
                if any(w in name or w in desc for w in keywords if w in user_message):
                    matched_schedules.append(s)
        
        # 30일 이내 다가오는 일정도 상시 추가
        alerts = get_upcoming_alerts(30)
        seen_events = {s.get("event_name") or s.get("title") for s in matched_schedules if s}
        for a in alerts:
            a_name = a.get("title") or a.get("event_name", "")
            if a_name not in seen_events:
                matched_schedules.append({
                    "event_name": a_name,
                    "start_date": a.get("start_date"),
                    "end_date": a.get("end_date"),
                    "description": a.get("description")
                })
                seen_events.add(a_name)
                
        if matched_schedules:
            alert_text = "\n".join(
                f"- [{s.get('start_date')}~{s.get('end_date')}] {s.get('event_name') or s.get('title')}: {s.get('description')}"
                for s in matched_schedules[:15]
            )
            messages.append({
                "role": "system",
                "content": (
                    "## 학사일정 데이터 (반드시 이 데이터에 있는 정보만 사용하여 대답하라)\n"
                    "아래는 2026학년도 한신대학교 공식 학사 일정 정보입니다.\n"
                    "이 목록에 기재된 일정과 날짜만 100% 신뢰하여 답변해야 하며, 목록에 없는 날짜나 일정은 임의로 지어내지 마십시오.\n\n"
                    f"{alert_text}"
                )
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
            timetable_data = {
                "total_credits": 18.0,
                "total_courses": 6,
                "empty_days": ["화"],
                "courses": [
                    {
                        "course_name": "앰비언트컴퓨팅기획",
                        "course_code": "SH342",
                        "type": "전공필수",
                        "credits": 3.0,
                        "professor": "노준성",
                        "schedule": [{"day": "월", "start": "09:30", "end": "10:45"}],
                        "reason": "주전공인 앰비언트 컴퓨팅 특화 트랙 필수 전공 과목입니다."
                    },
                    {
                        "course_name": "C언어",
                        "course_code": "AS002",
                        "type": "계열공통",
                        "credits": 3.0,
                        "professor": "이철수",
                        "schedule": [{"day": "수", "start": "13:00", "end": "15:45"}],
                        "reason": "기초 필수 계열공통 과목입니다."
                    }
                ]
            }
        elif "공지" in user_message or "일정" in user_message:
            reply += "현재 관련 공지사항이 확인됩니다. 알림 탭에서 매칭 리스트를 확인하실 수 있습니다."
            timetable_data = None
        elif interest_kws:
            reply += f"'{', '.join(interest_kws)}' 관련 과목을 추천 목록에 포함하였습니다."
            timetable_data = None
        else:
            reply += (
                f"질문해주신 '{user_message}'에 관해 확인 중입니다. "
                "졸업 자격 심사 기준 또는 전공 필수 이수 학점 상태를 확인하고 싶으시다면 "
                "상세 탭을 조회해 보세요!"
            )
            timetable_data = None
            
        if system_context:
            reply += f"\n\n[시스템 데이터]\n{system_context[:500]}"
            
        reply_with_hanja = hanja_to_hangul(reply)
        _extract_and_save_recommended_courses(reply_with_hanja, student_id)
        return {"message": reply_with_hanja, "structured_data": timetable_data}

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

        # Structured Outputs 및 JSON 모드 설정 강제
        chat = gemini_client.chats.create(
            model=_model_name,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=3000,
                response_mime_type="application/json",
                response_schema=GraduResponseSchema,
            ),
            history=chat_history,
        )

        full_prompt = system_text + "\n\n[사용자 질문]\n" + user_message

        response = chat.send_message(full_prompt)
        
        # JSON 스키마 파싱
        try:
            parsed_res = json.loads(response.text)
            chat_message = parsed_res.get("chat_message", "")
            timetable_data = parsed_res.get("timetable_data")
        except Exception:
            chat_message = response.text
            timetable_data = None
            
        chat_message_with_hanja = hanja_to_hangul(chat_message)

        # 추천된 과목이 컨텍스트에 존재하는지 검증
        if student_id and _has_recommend_keyword(lower_msg):
            try:
                student_obj = get_student(student_id)
                if student_obj:
                    available = get_available_courses(student_obj)
                    chat_message_with_hanja = _validate_recommendation_against_data(chat_message_with_hanja, available)
            except Exception:
                pass

        _extract_and_save_recommended_courses(chat_message_with_hanja, student_id)
        return {"message": chat_message_with_hanja, "structured_data": timetable_data}
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
