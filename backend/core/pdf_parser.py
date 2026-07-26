"""PDF 성적확인서 파서 - pdfplumber + Groq AI 기반 과목 추출"""

import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from groq import Groq
except ImportError:
    Groq = None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """PDF 바이트에서 텍스트를 추출합니다 (pdfplumber 사용)"""
    if pdfplumber is None:
        raise RuntimeError("pdfplumber가 설치되어 있지 않습니다. pip install pdfplumber")

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    full_text = ""
    try:
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            cleaned = [str(cell).strip() if cell else "" for cell in row]
                            full_text += " | ".join(cleaned) + "\n"
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return full_text.strip()


def parse_transcript_with_ai(pdf_text: str) -> dict:
    """
    Groq AI를 사용하여 추출된 PDF 텍스트를 구조화된 과목 데이터로 변환합니다.

    Returns:
        {
            "student_info": {"name": str, "student_id": str, "department": str},
            "courses": [
                {
                    "course_name": str,
                    "course_code": str | None,
                    "course_type": str,  # 전공필수, 전공선택, 교양필수, 교양선택, 일반선택, 계열공통
                    "credits": float,
                    "grade": str,  # A+, A0, B+, B0, ...
                    "semester": str  # 2021-1학기
                }
            ]
        }
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or Groq is None:
        return _fallback_parse(pdf_text)

    client = Groq(api_key=api_key)

    prompt = f"""당신은 한국 대학 성적확인서를 분석하는 전문가입니다.
아래 PDF에서 추출한 텍스트를 분석하여 각 수강 과목의 정보를 JSON 배열로 정리해주세요.

## 추출 규칙
1. 과목명(course_name): 반드시 포함
2. 학수번호(course_code): 있으면 포함, 없으면 null
3. 이수구분(course_type): 다음 중 하나로 정규화
   - 전공필수, 전공선택, 교양필수, 교양선택, 일반선택, 계열공통
   - "전필" → 전공필수, "전선" → 전공선택, "교필" → 교양필수, "교선" → 교양선택
   - "일선" → 일반선택, "계공" → 계열공통
4. 학점(credits): 숫자로 변환 (예: "3" → 3.0)
5. 성적(grade): A+, A0, B+, B0, C+, C0, D+, D0, F, P, NP 중 하나
6. 학기(semester): "YYYY-N학기" 형식 (예: "2021-1학기")
   - 학기 정보가 없으면 가장 최근 학기부터 역순으로 추정

## 학생 정보
- 이름, 학번, 학과가 있으면 포함

## 출력 형식
반드시 다음 JSON 형식으로만 출력하세요. 다른 텍스트를 포함하지 마세요.
```json
{{
  "student_info": {{
    "name": "홍길동",
    "student_id": "20210001",
    "department": "AISW"
  }},
  "courses": [
    {{
      "course_name": "프로그래밍기초",
      "course_code": null,
      "course_type": "전공필수",
      "credits": 3.0,
      "grade": "A+",
      "semester": "2021-1학기"
    }}
  ]
}}
```

## PDF 텍스트
---
{pdf_text[:8000]}
---

위 텍스트를 분석하여 JSON으로 출력해주세요."""

    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
        )
        raw_response = response.choices[0].message.content

        json_match = re.search(r'\{[\s\S]*\}', raw_response)
        if json_match:
            result = json.loads(json_match.group())
            if "courses" in result:
                return result

        return _fallback_parse(pdf_text)

    except Exception as e:
        print(f"AI 파싱 오류: {e}")
        return _fallback_parse(pdf_text)


def _fallback_parse(pdf_text: str) -> dict:
    """AI 파싱 실패 시 정규식 기반 폴백 파싱"""
    courses = []
    student_info = {"name": "", "student_id": "", "department": ""}

    name_match = re.search(r'이름[：:\s]*(\S+)', pdf_text)
    if name_match:
        student_info["name"] = name_match.group(1)

    sid_match = re.search(r'학번[：:\s]*(\d{8})', pdf_text)
    if sid_match:
        student_info["student_id"] = sid_match.group(1)

    dept_match = re.search(r'학과[：:\s]*(\S+)', pdf_text)
    if dept_match:
        student_info["department"] = dept_match.group(1)

    grade_pattern = re.compile(
        r'(\S+?)(?:\s+\S+?)?\s+(\d+(?:\.\d+)?)\s+([A-F][\+\-]?0?|P|NP)',
        re.MULTILINE
    )

    type_map = {
        "전공필수": "전공필수", "전필": "전공필수",
        "전공선택": "전공선택", "전선": "전공선택",
        "교양필수": "교양필수", "교필": "교양필수",
        "교양선택": "교양선택", "교선": "교양선택",
        "일반선택": "일반선택", "일선": "일반선택",
        "계열공통": "계열공통", "계공": "계열공통",
    }

    lines = pdf_text.split("\n")
    for line in lines:
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 3:
            course_type_raw = parts[0]
            course_type = type_map.get(course_type_raw, course_type_raw)

            remaining_parts = parts[1:]
            credits = None
            grade = None
            course_name = None

            for p in remaining_parts:
                if re.match(r'^\d+(\.\d+)?$', p):
                    credits = float(p)
                elif re.match(r'^[A-F][+-]?0?$|^P$|^NP$', p):
                    grade = p
                elif not course_name:
                    course_name = p

            if course_name and credits and grade:
                courses.append({
                    "course_name": course_name,
                    "course_code": None,
                    "course_type": course_type if course_type in type_map.values() else "일반선택",
                    "credits": credits,
                    "grade": grade,
                    "semester": ""
                })

    return {
        "student_info": student_info,
        "courses": courses
    }


def match_courses_to_db(parsed_courses: list[dict], courses_db: dict) -> list[dict]:
    """
    파싱된 과목 목록을 DB의 기존 과목과 매칭합니다.

    매칭 우선순위:
    1. course_code로 정확 매칭
    2. 과목명으로 정확 매칭
    3. 과목명으로 부분 매칭 (containing)

    Returns:
        [{"parsed": dict, "matched_code": str|None, "matched_course": dict|None, "confidence": str}]
    """
    results = []

    code_to_course = {}
    name_to_course = {}
    for code, course in courses_db.items():
        code_to_course[code.upper()] = course
        name_to_course[course.get("name", "").strip()] = course

    for parsed in parsed_courses:
        course_name = parsed.get("course_name", "").strip()
        course_code = (parsed.get("course_code") or "").strip().upper()

        matched_code = None
        matched_course = None
        confidence = "none"

        if course_code and course_code in code_to_course:
            matched_code = course_code
            matched_course = code_to_course[course_code]
            confidence = "exact_code"
        elif course_name in name_to_course:
            matched_course = name_to_course[course_name]
            matched_code = matched_course.get("code", "")
            confidence = "exact_name"
        else:
            for code, course in courses_db.items():
                db_name = course.get("name", "")
                if course_name and (course_name in db_name or db_name in course_name):
                    matched_course = course
                    matched_code = code
                    confidence = "partial_name"
                    break

        results.append({
            "parsed": parsed,
            "matched_code": matched_code,
            "matched_course": matched_course,
            "confidence": confidence,
        })

    return results
