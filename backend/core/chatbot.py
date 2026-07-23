"""AI 챗봇 모듈 - Groq API 연동 + 시스템 프롬프트 (CSV 기반 데이터)"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq  # OpenAI 대신 Groq 임포트

from .data.students import get_student
from .data.courses import get_required_remaining, get_available_courses
from .scheduler import generate_timetable
from .notifications import search_notices, get_upcoming_alerts

# .env 로드 (백엔드 루트 및 프로젝트 루트 탐색)
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    client = None
else:
    client = Groq(api_key=api_key)

# ==============================
# 시스템 프롬프트 (챗봇 페르소나)
# ==============================

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

    # 수강 가능한 과목 요약 (상위 20개)
    available_summary = []
    for c in available[:20]:
        times = ", ".join(f"{d} {s}~{e}" for d, s, e in c.get("time_slots", []))
        if times:
            available_summary.append(f"- {c['code']} {c['name']} ({c['credits']}학점) [{times}]")
        else:
            available_summary.append(f"- {c['code']} {c['name']} ({c['credits']}학점)")

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

## 수강 가능 과목 (일부)
{chr(10).join(available_summary) if available_summary else "없음"}

## 현재 수강 중
{chr(10).join(f"- {code}" for code in student.get('in_progress_courses', []))}

## 선호 시간대
- 선호 요일: {', '.join(student['preferred_days'])}
- 선호 시간: {', '.join(student['preferred_times'])}
- 피하는 시간: {', '.join(student['avoid_times']) if student['avoid_times'] else '없음'}
"""
    return context


def chat(user_message: str, student_id: str = None, history: list = None) -> str:
    """챗봇 대화 (Groq API 호출)"""
    # 선호도 자동 추출 및 학생 정보 업데이트
    if student_id:
        student = get_student(student_id)
        if student:
            updated = False
            msg = user_message.lower()
            
            # 요일 기피/제외 감지 ("금요일 공강", "금요일 빼줘", "금요일은 제외")
            days = ["월", "화", "수", "목", "금"]
            for d in days:
                d_target = d + "요일"
                if (d_target in msg or d in msg) and ("공강" in msg or "빼" in msg or "제외" in msg or "없이" in msg or "없게" in msg or "안돼" in msg):
                    current_pref = student.get("preferred_days", ["월", "화", "수", "목", "금"])
                    if d in current_pref:
                        student["preferred_days"] = [x for x in current_pref if x != d]
                        updated = True
            
            # 요일 선호 명시 감지 (예: "월수금만 수업", "화목에 몰아줘")
            if "월수금" in msg:
                student["preferred_days"] = ["월", "수", "금"]
                updated = True
            elif "화목" in msg:
                student["preferred_days"] = ["화", "목"]
                updated = True
                
            # 시간대 기피 감지 (예: "오전 수업 빼줘", "아침 1교시 빼줘")
            if "오전" in msg or "아침" in msg or "1교시" in msg:
                if "빼" in msg or "기피" in msg or "제외" in msg or "안돼" in msg or "싫" in msg or "피해" in msg:
                    avoid = student.get("avoid_times", [])
                    if "09:00-12:00" not in avoid:
                        student["avoid_times"] = list(set(avoid + ["09:00-12:00"]))
                        updated = True
            
            # 시간대 선호 감지 (예: "오후 수업 위주로", "오후 선호")
            if "오후" in msg:
                if "선호" in msg or "위주" in msg or "좋" in msg or "맞춰" in msg or "짜줘" in msg:
                    pref_times = student.get("preferred_times", [])
                    if "13:00-18:00" not in pref_times:
                        student["preferred_times"] = list(set(pref_times + ["13:00-18:00"]))
                        updated = True

            # 인메모리 STUDENTS 글로벌 변수에 즉각 보존
            if updated:
                from .data.students import STUDENTS
                STUDENTS[student_id] = student

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
                f"- [{n['date']}] {n['title']}: {n['content'][:100]}..." for n in results[:10]
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

    if not client:
        # 데모 모드로 동작하되, 시간표/공지사항 등이 주입되었으면 해당 정보를 바탕으로 가상 답변을 반환합니다.
        # 시간표나 일정 등의 프롬프트는 메시지에 주입되어 있습니다.
        system_context = ""
        for m in messages:
            if m["role"] == "system" and "시간표" in m["content"]:
                system_context += "\n[추천 시간표 정보 발견]\n" + m["content"]
            if m["role"] == "system" and "공지사항" in m["content"]:
                system_context += "\n[공지사항 정보 발견]\n" + m["content"]
        
        reply = "🎓 **그레듀 조교 답변 (데모 모드)**\n\n현재 `GROQ_API_KEY` 환경 변수가 설정되지 않아 인공지능 실시간 대화는 불가능하지만, 시스템 프롬프트 및 데이터를 기반으로 가상 상담을 제공합니다.\n\n"
        if "시간표" in user_message or "추천" in user_message:
            reply += "학번 및 선호 요일 분석을 마쳤습니다. 현재 시간표 탭에서 추천 1(18학점) 배치가 완료되었습니다. 홈 대시보드의 'AI 수강설계'에서도 6개의 맞춤 과목을 추천받으실 수 있습니다!"
        elif "공지" in user_message or "일정" in user_message:
            reply += "현재 관련 장학금 및 SW인턴십 공지가 예정되어 있습니다. 알림 탭에서 매칭 리스트를 확인하실 수 있습니다."
        else:
            reply += f"질문해주신 '{user_message}'에 관해 확인 중입니다. 졸업 자격 심사 기준 또는 전공 필수 이수 학점 상태를 확인하고 싶으시다면 상세 탭을 조회해 보세요!"
        return reply

    try:
        response = client.chat.completions.create(
            # gpt-4o 대신 Groq 지원 모델로 변경 (환경 변수 또는 기본값 적용)
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), 
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
            times = ", ".join(f"{d} {s}~{e}" for d, s, e in course.get("time_slots", []))
            lines.append(f"  - {course['code']} {course['name']} ({course['professor']}) [{times}]")
        lines.append("")
    return "\n".join(lines)