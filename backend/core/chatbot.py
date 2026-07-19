"""AI 챗봇 모듈 - OpenAI API 연동 + 시스템 프롬프트"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from .data.students import get_student
from .data.courses import get_required_remaining, get_available_courses
from .scheduler import generate_timetable
from .notifications import search_notices, get_upcoming_alerts

# .env 로드
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==============================
# 시스템 프롬프트 (챗봇 페르소나)
# ==============================

SYSTEM_PROMPT = """당신은 '졸업을 부탁해' 서비스의 AI 졸업 도우미 조교입니다.
이름은 '그레듀(Gradu)'이며, 학생들의 원활한 졸업을 돕는 친절하고 전문적인 AI 어시스턴트입니다.

## 핵심 규칙
1. 당신은 AISW(인공지능소프트웨어학부) 학생들의 졸업 요건, 수강신청, 시간표 설계를 돕습니다.
2. 사용자가 학번을 제공하면, 해당学生的 이수 현황을 분석하고 부족한 부분을 안내합니다.
3. 시간표 추천 시 사용자의 선호 요일/시간대를 반드시 고려합니다.
4. 답변은 한국어로 작성하며, 친근하고 존댓말을 사용합니다.
5. 확실하지 않은 정보는 추측하지 말고 "정확한 확인이 필요합니다"라고 안내합니다.
6. 학사일정 관련 질문은 현재 날짜 기준으로 임박한 일정을 우선 안내합니다.
7. 공지사항 키워드 검색 기능을 제공할 수 있습니다.

## 답변 톤
- 친근하면서도 전문적인 어조
- 이모지를 적절히 활용하여 가독성 높이기
- 중요한 정보는 **볼드** 또는 목록 형태로 강조
- 불필요한 장황한 설명보다 간결하고 핵심적인 답변 선호

## 제공 가능한 기능 안내
- 학생 이수 현황 분석 (학번 입력 시)
- 임박한 학사일정 알림
- 시간표 추천 (선호 시간대 기반)
- 공지사항 키워드 검색
- 졸업 요건 체크"""


def build_student_context(student_id: str) -> str:
    """학생 정보를 콘텍스트 문자열로 변환"""
    student = get_student(student_id)
    if not student:
        return "등록된 학생 정보가 없습니다."

    remaining_required = get_required_remaining(student)
    available = get_available_courses(student)
    credits_needed = student["required_credits"] - student["completed_credits"]

    context = f"""
## 현재 학생 정보
- 이름: {student['name']}
- 학번: {student['student_id']}
- 학과: {student['department']}
- 주전공: {', '.join(student['major_tracks'])}
- 현재 학기: {student['current_semester']}학기
- 이수 학점: {student['completed_credits']}/{student['required_credits']} (부족: {credits_needed}학점)
- GPA: {student['gpa']}
- 마일리지: {student['mileage']}

## 미이수 전공 필수 과목
{chr(10).join(f"- {c['code']} {c['name']} ({c['credits']}학점)" for c in remaining_required) if remaining_required else "없음"}

## 수강 가능한 과목 수: {len(available)}개

## 현재 수강 중
{chr(10).join(f"- {code}" for code in student.get('in_progress_courses', []))}

## 선호 시간대
- 선호 요일: {', '.join(student['preferred_days'])}
- 선호 시간: {', '.join(student['preferred_times'])}
- 피하는 시간: {', '.join(student['avoid_times']) if student['avoid_times'] else '없음'}
"""
    return context


def chat(user_message: str, student_id: str = None, history: list = None) -> str:
    """챗봇 대화 (OpenAI API 호출)"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 이전 대화 기록 추가
    if history:
        messages.extend(history)

    # 학생 컨텍스트 주입
    if student_id:
        student_context = build_student_context(student_id)
        messages.append({"role": "system", "content": student_context})

    # 특수 명령어 처리
    lower_msg = user_message.lower()

    if "시간표" in lower_msg and student_id:
        student = get_student(student_id)
        if student:
            schedules = generate_timetable(student, max_schedules=3)
            schedule_text = _format_schedules(schedules)
            messages.append({
                "role": "system",
                "content": f"## 시간표 추천 결과\n{schedule_text}\n\n위 시간표를 바탕으로 사용자에게 추천해주세요.",
            })

    if "공지" in lower_msg or "알림" in lower_msg:
        results = search_notices(user_message)
        if results:
            notice_text = "\n".join(
                f"- [{n['date']}] {n['title']}: {n['content'][:100]}..." for n in results
            )
            messages.append({
                "role": "system",
                "content": f"## 관련 공지사항\n{notice_text}",
            })

    if "일정" in lower_msg or "스케줄" in lower_msg:
        alerts = get_upcoming_alerts(30)
        if alerts:
            alert_text = "\n".join(
                f"- [{a['start_date']}~{a['end_date']}] {a['title']}: {a['description']}" for a in alerts
            )
            messages.append({
                "role": "system",
                "content": f"## 향후 학사일정\n{alert_text}",
            })

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"API 호출 중 오류가 발생했습니다: {str(e)}"


def _format_schedules(schedules: list[dict]) -> str:
    """시간표 결과를 텍스트로 포맷"""
    if not schedules:
        return "추천 가능한 시간표가 없습니다."

    lines = []
    for i, schedule in enumerate(schedules, 1):
        lines.append(f"### 추천 {i} (총 {schedule['total_credits']}학점)")
        for course in schedule["courses"]:
            times = ", ".join(f"{d} {s}~{e}" for d, s, e in course["time_slots"])
            lines.append(f"  - {course['code']} {course['name']} ({course['professor']}) [{times}]")
        lines.append("")
    return "\n".join(lines)
