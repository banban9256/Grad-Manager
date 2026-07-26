"""AI 챗봇 모듈 - Groq API 연동 + 시스템 프롬프트 (CSV 기반 데이터)"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

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

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

SYSTEM_PROMPT = """당신은 '졸업을 부탁해' 서비스의 AI 졸업 도우미 조교입니다.
이름은 '그레듀(Gradu)'이며, 학생들의 원활한 졸업을 돕는 친절하고 전문적인 AI 어시스턴트입니다.

## 핵심 규칙
1. 당신은 AISW(인공지능소프트웨어학부) 학생들의 졸업 요건, 수강신청, 시간표 설계를 돕습니다.
2. 사용자가 학번을 제공하면, 해당 학생의 이수 현황을 분석하고 부족한 부분을 안내합니다.
3. 시간표 추천 시 사용자의 선호 요일/시간대를 반드시 고려합니다.
4. 답변은 한국어로 작성하며, 친근하고 존댓말을 사용합니다.
5. 확실하지 않은 정보는 추측하지 말고 "정확한 확인이 필요합니다"라고 안내합니다.
6. 학사일정 관련 질문은 현재 날짜 기준으로 임박한 일정을 우선 안내합니다.
7. 공지사항 키워드 검색 기능을 제공할 수 있습니다.
8. **한자(漢字) 사용 금지**: 답변에 한자가 포함되지 않도록 합니다. 모든 한자는 한글로 변환하여 자연스럽게 출력합니다. 예: 寫作 → 사작, 深化 → 심화
9. **AISW 학과 졸업 요건 (전필 없음)**: AISW 학과(인공지능소프트웨어학부)는 졸업 요건에 **전공 필수 과목이 존재하지 않습니다**. 따라서 졸업 요건을 진단하거나 안내할 때 "AISW 학과는 전공 필수 과목이 없으므로 전공 필수 0학점이 졸업 요건 기준입니다" 또는 "전공 필수 과목은 이수할 필요가 없으며, 졸업에 필요한 전공 학점(예: 주전공 24학점)은 모두 전공 선택 과목으로 채우면 됩니다"라고 명확하고 정확하게 안내해야 합니다.

## 데이터 정확성 규칙 (최우선)
- **컨텍스트에 없는 과목/학점을 절대 지어내지 마세요.** 제공된 컨텍스트에 없는 과목명, 학수코드, 학점 등을 임의로 생성하면 안 됩니다.
- **이미 이수 완료 목록에 있는 과목은 추천 금지.** "## 이수 완료 과목 목록"에 있는 과목은 재수강을 명시한 경우만 예외적으로 추천할 수 있습니다.
- **학점 숫자를 틀리게 말하지 마세요.** 컨텍스트의 "## 카테고리별 졸업요건 현황"에 기재된 이수/필요/잔여 학점을 그대로 인용해야 합니다. 임의로 숫자를 바꾸면 안 됩니다.
- **과목 학점 조작 금지:** 과목명, 학점, 학수코드, 이수구분은 전부 백엔드 DB에 저장된 실제 값입니다. 사용자가 "10학점짜리 AI 수업 추천해줘"라고 해도, DB에 존재하는 과목의 학점 그대로만 추천하세요.

## 질문 유형별 응답 규칙
- **"지금 꼭 들어야 하는 과목"**: "## 카테고리별 졸업요건 현황"에서 잔여 학점이 있는 카테고리를 우선순위로 정렬하고, "## 이번 학기 미이수 필수 과목"에서 해당 카테고리의 개설 과목을 추천하세요.
- **"과거 이수 기준으로 졸업요건 맞게 들었어?"**: "## 카테고리별 졸업요건 현황"에서 각 카테고리의 이수/필요/잔여를 숫자로 명시하고, 충족(잔여 0)과 부족(잔여 > 0)을 구분하여 답변하세요. 특화전공/융합전공 요건도 포함하세요.
- **일반 추천**: 컨텍스트의 이력·요건·필터된 개설만 사용하여 추천하세요.

## 과목 추천 규칙 (매우 중요)
- **이번 학기 미이수 필수 과목 최우선 추천**: "## 이번 학기 미이수 필수 과목 (우선 추천 대상)" 데이터가 제공되면, 해당 과목(교양필수, 전공필수 등)을 반드시 우선적으로 추천하세요.
- **AISW 학생 전공필수 배제**: 사용자가 AISW 학과 학생인 경우, 전공 필수 과목을 추천의 필수 조건으로 삼지 마세요. AISW 학과는 전필이 없으므로 전선(전공선택)이나 계열공통 과목 위주로 추천해야 합니다.
- **부족 카테고리 우선**: "## 카테고리별 졸업요건 현황"에서 잔여 학점이 많은 카테고리의 과목을 우선 추천하세요.
- **이수구분별 우선순위**: 추천 시 다음 순서대로 우선합니다:
  1. 부족 학점이 많은 카테고리의 미이수 과목
  2. 이번 학기에 개설된 미이수 교양필수 과목
  3. 이번 학기에 개설된 미이수 전공필수 과목
  4. 계열공통 과목
  5. 트랙별 미이수 필수 과목
  6. 기타 수강 가능 과목
- **트랙별 필수 과목 추천**: 사용자가 트랙에 맞는 과목 추천을 요청하면, 반드시 "## 트랙별 미이수 필수 과목" 데이터를 참고하여 해당 트랙의 필수 과목을 우선 추천하세요.
- **이수구분 검증**: 사용자가 기수강 과목의 이수구분이 맞는지 확인 요청하면, "## 이수구분 검증 결과" 데이터를 참고하세요.
- **관심 과목 추천**: 사용자가 관심 분야를 언급하면, "## 관심 키워드 매칭 과목" 데이터를 참고하여 해당 관심사에 맞는 과목을 추천하세요. 반드시 사용자의 졸업요건에 해당하는 과목만 추천하세요.
- **트랙 관련 과목만 추천**: 사용자의 전공/트랙에 해당하는 과목만 추천하세요. 타 학과 전공필수 과목을 추천하지 마세요.
- **채플(Chapel) 안내**: 채플(KY101, KY201 등)은 매 학기 0.5학점 이상 이수하는 출석 이수 과목입니다. 정규 과목 수강과는 별도로 처리되며, 특별히 추천할 필요가 없습니다.

## 답변 톤
- 친근하면서도 전문적인 어조
- 이모지를 적절히 활용하여 가독성 높이기
- 중요한 정보는 **볼드** 또는 목록 형태로 강조
- 불필요한 장황한 설명보다 간결하고 핵심적인 답변 선호
- 모든 한자는 반드시 한글로 변환하여 출력

## 제공 가능한 기능 안내
- 학생 이수 현황 분석 (학번 입력 시)
- 임박한 학사일정 알림
- 시간표 추천 (선호 시간대 기반)
- 공지사항 키워드 검색
- 졸업 요건 체크
- 트랙별 필수 과목 추천
- 기수강 과목 이수구분 검증
- 관심 분야 기반 과목 추천
- 성적확인서 PDF 업로드 및 자동 기수강 과목 추출"""


def _build_completed_history_text(student: dict) -> str:
    """학생의 이수 완료 과목 전체 이력을 텍스트로 구성합니다."""
    from .data.csv_loader import load_courses
    from app.database import SessionLocal
    from app import models as db_models

    courses_db = load_courses()
    completed_codes = student.get("completed_courses", [])

    # SQLite DB에서 실제 수강 이력 조회
    history_records = []
    try:
        db = SessionLocal()
        sid_int = int(student["student_id"])
        histories = db.query(db_models.StudentCourseHistory).filter(
            db_models.StudentCourseHistory.student_id == sid_int
        ).all()
        for h in histories:
            c_rec = db.query(db_models.Course).filter(
                db_models.Course.course_id == h.course_id
            ).first()
            code = c_rec.course_code if c_rec else f"UNKNOWN-{h.course_id}"
            name = c_rec.course_name if c_rec else "과목명 미정"
            cat = getattr(h, 'course_type', None) or ""
            if not cat.strip():
                course_info = courses_db.get(code, {})
                cat = course_info.get("type", "일반선택")
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
        db.close()
    except Exception:
        pass

    # 재수강 포기(Forfeited) 규칙 적용
    from collections import defaultdict
    import re
    n = len(history_records)
    parent = list(range(n))
    def find(i):
        if parent[i] == i: return i
        parent[i] = find(parent[i])
        return parent[i]
    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj: parent[ri] = rj

    for i in range(n):
        for j in range(i+1, n):
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
            def sem_score(s):
                m = re.match(r'(\d+)-(\d)', s)
                return int(m.group(1))*10 + int(m.group(2)) if m else 0
            sorted_inst = sorted(instances, key=lambda x: sem_score(x["semester"]))
            for inst in sorted_inst[:-1]:
                forfeited_ids.add(inst["history_id"])

    # 필터링된 이력 텍스트 구성
    lines = []
    for rec in history_records:
        if rec["history_id"] in forfeited_ids:
            continue
        if rec["grade"].upper() == "F":
            continue
        retake_tag = " (재수강)" if rec["is_retake"] else ""
        lines.append(
            f"- [{rec['semester']}] {rec['code']} {rec['name']} "
            f"| {rec['category']} | {rec['credit']}학점 | 성적: {rec['grade']}{retake_tag}"
        )

    if not lines:
        return "이수 완료 과목이 없습니다."
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
            lines.append(f"- {cat}: {comp}/{req}학점 이수 (잔여 {remain}학점) → {status}")
        elif comp > 0:
            lines.append(f"- {cat}: {comp}학점 이수 (요건 없음)")

    # 특화전공/융합전공 요건 (약 21학점 기준, 프로젝트 실제 수치)
    spec_track = student.get("specialized_track", "")
    conv_major = student.get("convergence_major", "")
    if spec_track:
        lines.append(f"- 특화전공({spec_track}): 약 21학점 필요 (백엔드 기준 확인 필요)")
    if conv_major:
        lines.append(f"- 융합전공({conv_major}): 약 21학점 필요 (백엔드 기준 확인 필요)")

    return "\n".join(lines) if lines else "졸업요건 데이터 없음"


def build_student_context(student_id: str, target_semester: str = None) -> str:
    student = get_student(student_id)
    if not student:
        return "등록된 학생 정보가 없습니다."

    if target_semester:
        student["target_semester"] = target_semester

    remaining_required = get_required_remaining(student)
    available = get_available_courses(student)
    credits_needed = student["required_credits"] - student["completed_credits"]

    # 이수 완료 과목 전체 이력
    completed_history_text = _build_completed_history_text(student)

    # 카테고리별 졸업요건 현황
    category_req_text = _build_category_requirements_text(student)

    # 수강 가능 과목 (상위 N개, 이미 이수한 학수번호 제외)
    completed_set = set(student.get("completed_courses", []))
    in_progress_set = set(student.get("in_progress_courses", []))
    available_summary = []
    count = 0
    for c in available:
        if count >= 25:
            break
        times = ", ".join(f"{d} {s}~{e}" for d, s, e in c.get("time_slots", []))
        time_str = f" [{times}]" if times else ""
        available_summary.append(f"- {c['code']} {c['name']} ({c['credits']}학점){time_str}")
        count += 1

    # 이번 학기 미이수 필수 과목
    semester_info = ""
    if target_semester:
        try:
            semester_required = get_all_remaining_required_for_semester(student, target_semester)
            if semester_required:
                sem_lines = []
                for cat, info in semester_required.items():
                    avail = info.get("available_now", [])
                    not_avail = info.get("not_available_now", [])
                    if avail:
                        sem_lines.append(f"### {cat} ({target_semester} 개설: {len(avail)}과목)")
                        for c in avail[:10]:
                            sem_lines.append(f"  - {c['code']} {c['name']} ({c['credits']}학점)")
                    if not_avail:
                        sem_lines.append(f"### {cat} (다른 학기 개설: {len(not_avail)}과목)")
                        for c in not_avail[:5]:
                            sem_lines.append(f"  - {c['code']} {c['name']} ({c['credits']}학점)")
                semester_info = f"\n## 이번 학기 미이수 필수 과목 (우선 추천 대상)\n{chr(10).join(sem_lines)}\n"
        except Exception:
            pass

    # 졸업논문/캡스톤 대체 관계 안내
    thesis_capstone_info = """
## 졸업논문/캡스톤 대체 안내
- AISW 학생은 졸업논문(SH519) 대신 AISW캡스톤설계I(SH402, 3학점), AISW캡스톤설계II(SH403, 3학점)를 이수할 수 있습니다.
- 캡스톤 과목은 졸업논문과 동일하게 6학점으로 인정됩니다.
- 캡스톤을 이수하면 졸업논문을 대체할 수 있습니다."""

    context = f"""
## 현재 학생 정보
- 이름: {student['name']}
- 학번: {student['student_id']}
- 학과: {student['department']}
- 주전공: {', '.join(student['major_tracks'])}
- 융합전공: {student.get('convergence_major', '설정 안 함')}
- 특화트랙: {student.get('specialized_track', '설정 안 함')}
- 현재 학기: {student['current_semester']}학기
- 이수 학점: {student['completed_credits']}/{student['required_credits']} (부족: {credits_needed}학점)
- GPA: {student['gpa']}
- 마일리지: {student['mileage']}

## 카테고리별 졸업요건 현황
{category_req_text}

## 이수 완료 과목 목록
{completed_history_text}

## 현재 수강 중
{chr(10).join(f"- {code}" for code in student.get('in_progress_courses', [])) or "없음"}
{semester_info}
## 미이수 전공 필수 과목
{chr(10).join(f"- {c['code']} {c['name']} ({c['credits']}학점)" for c in remaining_required) if remaining_required else "없음"}

## 수강 가능 과목 (일부, 총 {len(available)}개 중 상위 25개)
{chr(10).join(available_summary) if available_summary else "없음"}

## 선호 시간대
- 선호 요일: {', '.join(student['preferred_days'])}
- 선호 시간: {', '.join(student['preferred_times'])}
- 피하는 시간: {', '.join(student['avoid_times']) if student['avoid_times'] else '없음'}
{thesis_capstone_info}
"""
    return context


def build_curriculum_context(student: dict, target_semester: str = None) -> str:
    """교육과정, 이수구분 검증, 관심 과목 등 추가 컨텍스트를 생성합니다."""
    parts = []

    try:
        track_remaining = get_required_remaining_by_track(student, target_semester)
        if track_remaining:
            lines = []
            for c in track_remaining[:15]:
                times = ", ".join(f"{d} {s}~{e}" for d, s, e in c.get("time_slots", []))
                time_str = f" [{times}]" if times else ""
                lines.append(f"- {c['code']} {c['name']} ({c['credits']}학점){time_str}")
            parts.append(f"## 트랙별 미이수 필수 과목\n{chr(10).join(lines)}")
        else:
            parts.append("## 트랙별 미이수 필수 과목\n없음 (모든 필수 과목 이수 완료)")
    except Exception:
        parts.append("## 트랙별 미이수 필수 과목\n데이터 로딩 실패")

    try:
        semester_required = get_all_remaining_required_for_semester(student, target_semester)
        if semester_required:
            sem_lines = []
            for cat, info in semester_required.items():
                avail = info.get("available_now", [])
                not_avail = info.get("not_available_now", [])
                if avail:
                    sem_lines.append(f"### {cat} (이번 학기 개설: {len(avail)}과목)")
                    for c in avail[:8]:
                        sem_lines.append(f"  - {c['code']} {c['name']} ({c['credits']}학점)")
                if not_avail:
                    sem_lines.append(f"### {cat} (다른 학기 개설: {len(not_avail)}과목)")
                    for c in not_avail[:5]:
                        sem_lines.append(f"  - {c['code']} {c['name']} ({c['credits']}학점)")
            if sem_lines:
                parts.append(f"## 이번 학기 미이수 필수 과목 (우선 추천 대상)\n{chr(10).join(sem_lines)}")
    except Exception:
        pass

    try:
        validation = validate_completed_categories(student)
        summary = validation["category_summary"]
        mismatched = validation["mismatched_courses"]

        summary_lines = [f"- {cat}: {credits}학점" for cat, credits in summary.items() if credits > 0]
        parts.append(f"## 이수구분별 학점 현황\n{chr(10).join(summary_lines)}")

        if mismatched:
            mismatch_lines = []
            for m in mismatched[:10]:
                mismatch_lines.append(
                    f"- {m['code']} {m['name']}: 시스템 기준 '{m['curriculum_type']}' "
                    f"(코드 기준 '{m['inferred_type']}')"
                )
            parts.append(f"## 이수구분 검증 결과 (확인 필요)\n{chr(10).join(mismatch_lines)}")
    except Exception:
        pass

    try:
        grad_summary = get_graduation_credit_summary(student)
        lines = []
        for cat, info in grad_summary.items():
            if info["required"] > 0:
                status = "충족" if info["remaining"] == 0 else f"{info['remaining']}학점 부족"
                lines.append(f"- {cat}: {info['completed']}/{info['required']}학점 ({status})")
            elif info["completed"] > 0:
                lines.append(f"- {cat}: {info['completed']}학점 이수 (요건 없음)")
        if lines:
            parts.append(f"## 이수구분별 졸업요건 현황\n{chr(10).join(lines)}")
    except Exception:
        pass

    return "\n\n".join(parts) if parts else ""


def detect_interest_keywords(user_message: str) -> list[str]:
    """사용자 메시지에서 관심 키워드를 추출합니다."""
    interest_patterns = [
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
    ]

    msg_lower = user_message.lower()
    found = []
    for label, keywords in interest_patterns:
        for kw in keywords:
            if kw in msg_lower:
                found.append(label)
                break
    return found


def chat(user_message: str, student_id: str = None, history: list = None, target_semester: str = None) -> str:
    if student_id:
        student = get_student(student_id)
        if student:
            if target_semester:
                student["target_semester"] = target_semester
            updated = False
            msg = user_message.lower()

            days = ["월", "화", "수", "목", "금"]
            for d in days:
                d_target = d + "요일"
                if (d_target in msg or d in msg) and ("공강" in msg or "빼" in msg or "제외" in msg or "없이" in msg or "없게" in msg or "안돼" in msg):
                    current_pref = student.get("preferred_days", ["월", "화", "수", "목", "금"])
                    if d in current_pref:
                        student["preferred_days"] = [x for x in current_pref if x != d]
                        updated = True

            if "월수금" in msg:
                student["preferred_days"] = ["월", "수", "금"]
                updated = True
            elif "화목" in msg:
                student["preferred_days"] = ["화", "목"]
                updated = True

            if "오전" in msg or "아침" in msg or "1교시" in msg:
                if "빼" in msg or "기피" in msg or "제외" in msg or "안돼" in msg or "싫" in msg or "피해" in msg:
                    avoid = student.get("avoid_times", [])
                    if "09:00-12:00" not in avoid:
                        student["avoid_times"] = list(set(avoid + ["09:00-12:00"]))
                        updated = True

            if "오후" in msg:
                if "선호" in msg or "위주" in msg or "좋" in msg or "맞춰" in msg or "짜줘" in msg:
                    pref_times = student.get("preferred_times", [])
                    if "13:00-18:00" not in pref_times:
                        student["preferred_times"] = list(set(pref_times + ["13:00-18:00"]))
                        updated = True

            if updated:
                from .data.students import STUDENTS
                STUDENTS[student_id] = student

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history)

    if student_id:
        student_context = build_student_context(student_id, target_semester)
        messages.append({"role": "system", "content": student_context})

        curriculum_ctx = build_curriculum_context(
            get_student(student_id) or {},
            target_semester,
        )
        if curriculum_ctx:
            messages.append({"role": "system", "content": curriculum_ctx})

    lower_msg = user_message.lower()

    if "시간표" in lower_msg and student_id:
        student = get_student(student_id)
        if student:
            if target_semester:
                student["target_semester"] = target_semester
            schedules = generate_timetable(student, max_schedules=3)
            schedule_text = _format_schedules(schedules)
            messages.append({
                "role": "system",
                "content": f"## 시간표 추천 결과\n{schedule_text}\n\n위 시간표를 바탕으로 사용자에게 추천해주세요. 반드시 {target_semester or '지정 학기'}에 개설된 과목들이 맞는지 다시 확인하세요.",
            })

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

    interest_kws = detect_interest_keywords(user_message)
    if interest_kws and student_id:
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

    if not client:
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

        reply = "🎓 **그레듀 조교 답변 (데모 모드)**\n\n현재 `GROQ_API_KEY` 환경 변수가 설정되지 않아 인공지능 실시간 대화는 불가능하지만, 시스템 프롬프트 및 데이터를 기반으로 가상 상담을 제공합니다.\n\n"
        if "시간표" in user_message or "추천" in user_message:
            reply += f"학번 및 선호 요일 분석을 마쳤습니다. 선택하신 학기({target_semester or '2026-1학기'})의 시간표 탭에서 추천 배치가 완료되었습니다."
        elif "공지" in user_message or "일정" in user_message:
            reply += "현재 관련 공지사항이 확인됩니다. 알림 탭에서 매칭 리스트를 확인하실 수 있습니다."
        elif interest_kws:
            reply += f"'{', '.join(interest_kws)}' 관련 과목을 추천 목록에 포함하였습니다."
        else:
            reply += f"질문해주신 '{user_message}'에 관해 확인 중입니다. 졸업 자격 심사 기준 또는 전공 필수 이수 학점 상태를 확인하고 싶으시다면 상세 탭을 조회해 보세요!"
        if system_context:
            reply += f"\n\n[시스템 데이터]\n{system_context[:500]}"
        return reply

    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=messages,
            temperature=0.4,
            max_tokens=1500,
        )
        return hanja_to_hangul(response.choices[0].message.content)
    except Exception as e:
        return f"API 호출 중 오류가 발생했습니다: {str(e)}"


def _format_schedules(schedules: list[dict]) -> str:
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
