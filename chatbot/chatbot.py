"""
Groq API 연동 챗봇 모듈

사용자 메시지를 받아 시스템 프롬프트와 함께 Groq API에 전달하고,
챗봇 응답을 반환
"""

import os
from dotenv import load_dotenv
from groq import Groq
from .persona import SYSTEM_PROMPT

# .env 파일 로드
load_dotenv()

class GradChatBot:
    """졸업을 부탁해 AI 챗봇"""

    def __init__(self, api_key: str = None, model: str = None):
        # config 모듈 대신 os.environ.get으로 .env 파일의 값을 직접 가져옴
        self.client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))
        # 환경 변수에 모델이 없으면 기본값으로 'llama3-70b-8192' 사용
        self.model = model or os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")        self.system_prompt = SYSTEM_PROMPT
        self.conversation_history: list[dict] = []

    def reset(self):
        """대화 초기화"""
        self.conversation_history = []

    def chat(self, user_message: str, context: str = "") -> str:
        """
        사용자 메시지를 받아 AI 응답을 생성합니다.

        Args:
            user_message: 사용자의 입력 메시지
            context: 챗봇에 주입할 컨텍스트 정보 (졸업 요건, 시간표 등)

        Returns:
            AI 응답 텍스트
        """
        system_content = self.system_prompt
        if context:
            system_content += f"\n\n## 현재 학생 정보 및 컨텍스트\n{context}"

        messages = [{"role": "system", "content": system_content}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            )
            assistant_message = response.choices[0].message.content

            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )

            return assistant_message

        except Exception as e:
            return f"죄송합니다. 일시적인 오류가 발생했어요. 다시 시도해 주세요. (오류: {str(e)})"


def build_student_context(student: dict, courses: list[dict]) -> str:
    """
    학생 정보와 수강 이력을 기반으로 챗봇 컨텍스트 문자열을 생성합니다.
    나중에 실제 DB 연결 시 이 함수의 데이터 소스만 교체하면 됩니다.
    """
    req = student["graduation_requirements"]
    lines = [
        f"학번: {student['student_id']}",
        f"이름: {student['name']}",
        f"학과: {student['department']}",
        f"현재 학기: {student['current_semester']}학기",
        f"이수 학점: {student['completed_credits']}/{req['total_credits']}",
        f"마일리지: {student['mileage']}",
        "",
        "=== 졸업 요건 충족 현황 ===",
    ]

    category_names = {
        "general_education": "교양",
        "major_required": "전공필수",
        "major_elective": "전공선택",
        "specialization": "특화/융합",
        "free_elective": "자유선택",
    }

    for key, label in category_names.items():
        info = req[key]
        remaining = info["required"] - info["completed"]
        status = "충족 완료" if remaining <= 0 else f"부족: {remaining}학점"
        lines.append(f"- {label}: {info['completed']}/{info['required']} ({status})")

    lines.append("")
    lines.append(f"=== 수강 중인 과목 ===")
    if courses:
        for c in courses:
            sched = ", ".join(
                [f"{s['day']} {s['start']}-{s['end']}" for s in c["schedule"]]
            )
            lines.append(f"- {c['name']} ({c['category']}, {sched})")
    else:
        lines.append("(수강 중인 과목 없음)")

    return "\n".join(lines)