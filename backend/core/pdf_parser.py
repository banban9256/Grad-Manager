"""PDF 성적확인서 파서 - pdfplumber + Google Gemini AI 기반 과목 추출"""

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

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional


class StudentInfo(BaseModel):
    name: Optional[str] = None
    student_id: Optional[str] = None
    department: Optional[str] = None


class CourseEntry(BaseModel):
    course_name: str
    course_code: Optional[str] = None
    course_type: str = Field(description="전공필수, 전공선택, 교양필수, 교양선택, 일반선택, 계열공통 중 하나")
    credits: float
    grade: str = Field(description="A+, A0, B+, B0, C+, C0, D+, D0, F, P, NP 중 하나")
    semester: str = Field(description="YYYY-N학기 형식 (예: 2021-1학기)")


class TranscriptSchema(BaseModel):
    student_info: StudentInfo
    courses: List[CourseEntry]


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
    Google Gemini API를 사용하여 추출된 PDF 텍스트를 구조화된 과목 데이터로 변환합니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_parse(pdf_text)

    try:
        client = genai.Client(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash")
        
        prompt = f"""당신은 한국 대학 성적확인서를 분석하는 전문가입니다.
아래 PDF에서 추출한 텍스트를 분석하여 학생 정보와 수강 과목들의 정보를 JSON 구조로 정리해주세요.

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

## PDF 텍스트
---
{pdf_text[:8000]}
---
"""
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TranscriptSchema,
                temperature=0.1
            ),
        )
        
        result = json.loads(response.text)
        if "courses" in result:
            return result

        return _fallback_parse(pdf_text)

    except Exception as e:
        print(f"Gemini AI 파싱 오류: {e}")
        return _fallback_parse(pdf_text)


def _fallback_parse(pdf_text: str) -> dict:
    """AI 파싱 실패 시 규칙 및 정규식 기반 폴백 파싱"""
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

    type_map = {
        "전공필수": "전공필수", "전필": "전공필수",
        "전공선택": "전공선택", "전선": "전공선택",
        "교양필수": "교양필수", "교필": "교양필수",
        "교양선택": "교양선택", "교선": "교양선택",
        "일반선택": "일반선택", "일선": "일반선택",
        "계열공통": "계열공통", "계공": "계열공통",
    }

    # 정규식 패턴: 과목코드(옵션), 과목명, 학점(숫자), 성적(A~F, P, NP)
    course_pattern = re.compile(
        r'(?P<type>전필|전선|교필|교선|일선|계공|전공필수|전공선택|교양필수|교양선택|일반선택|계열공통)?\s*'
        r'(?P<code>[A-Z]{2,4}-\d{3}|[A-Z]{2,5}\d{3})?\s*'
        r'(?P<name>[가-힣A-Za-z0-9_\s\-\&\(\)]+?)\s+'
        r'(?P<credits>\d+(?:\.\d+)?)\s+'
        r'(?P<grade>[A-F][\+\-]?0?|P|NP)\b'
    )

    lines = pdf_text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 1. 파이프 기호 기반 파싱 시도
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                course_type_raw = parts[0]
                course_type = type_map.get(course_type_raw, "일반선택")

                remaining_parts = parts[1:]
                credits = None
                grade = None
                course_name = None
                course_code = None

                for p in remaining_parts:
                    if re.match(r'^\d+(\.\d+)?$', p):
                        credits = float(p)
                    elif re.match(r'^[A-F][+-]?0?$|^P$|^NP$', p):
                        grade = p
                    elif re.match(r'^[A-Z]{2,4}-\d{3}$|^[A-Z]{2,5}\d{3}$', p):
                        course_code = p
                    elif not course_name:
                        course_name = p

                if course_name and credits is not None and grade:
                    courses.append({
                        "course_name": course_name,
                        "course_code": course_code,
                        "course_type": course_type,
                        "credits": credits,
                        "grade": grade,
                        "semester": ""
                    })
                    continue

        # 2. 파이프가 없거나 파이프 파싱 실패 시 정규식 기반 매칭 시도
        match = course_pattern.search(line)
        if match:
            raw_type = match.group("type")
            course_type = type_map.get(raw_type, "일반선택") if raw_type else "일반선택"
            course_code = match.group("code")
            course_name = match.group("name").strip()
            credits = float(match.group("credits"))
            grade = match.group("grade")

            if course_name and len(course_name) >= 2:
                courses.append({
                    "course_name": course_name,
                    "course_code": course_code,
                    "course_type": course_type,
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
