# -*- coding: utf-8 -*-
"""
GradManager - MySQL 덤프 파일 생성
DDL + CSV 데이터를 하나의 .sql 덤프 파일로 통합
"""
import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "data", "output")
DUMP_PATH = os.path.join(BASE_DIR, "..", "database", "gradmanager_dump.sql")

# CSV 파일 읽기
def read_csv(name):
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames

# SQL 이스케이프
def esc(val):
    if val is None or val == "":
        return "NULL"
    s = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"

def esc_bool(val):
    if val is None or val == "":
        return "NULL"
    v = str(val).strip().lower()
    if v in ("true", "1", "yes"):
        return "TRUE"
    return "FALSE"

def esc_int(val):
    if val is None or val == "":
        return "NULL"
    return str(int(float(val)))

def esc_decimal(val):
    if val is None or val == "":
        return "NULL"
    return str(float(val))

def esc_date(val):
    if val is None or val == "":
        return "NULL"
    return f"'{val}'"

# 테이블별 컬럼 타입 매핑 (DDL 기반)
TABLE_TYPES = {
    "programs": {
        "program_id": "int", "program_name": "str", "program_type": "str",
        "required_credits": "decimal", "effective_from_year": "int",
        "effective_to_year": "int_nullable", "source_url": "str",
    },
    "students": {
        "student_id": "int", "user_id": "int", "student_number": "str",
        "admission_year": "int", "current_grade": "int",
    },
    "courses": {
        "course_id": "int", "course_code": "str", "course_name": "str",
        "credit": "decimal", "theory_hours": "decimal_nullable",
        "practice_hours": "decimal_nullable", "course_description": "str_nullable",
        "source_url": "str",
    },
    "curriculum_courses": {
        "curriculum_course_id": "int", "curriculum_year": "int",
        "course_id": "int", "recommended_grade": "int_nullable",
        "semester": "str_nullable", "completion_type": "str",
        "is_required": "bool", "note": "str_nullable",
        "program_id": "int_nullable",
    },
    "graduation_requirements": {
        "requirement_id": "int", "admission_year": "int",
        "program_id": "int_nullable", "requirement_category": "str",
        "required_credits": "decimal_nullable", "requirement_text": "str_nullable",
        "source_url": "str",
    },
    "program_courses": {
        "program_course_id": "int", "program_id": "int", "course_id": "int",
        "effective_year": "int", "recognition_credit": "decimal_nullable",
        "is_required": "bool_nullable", "note": "str_nullable",
    },
    "course_offerings": {
        "offering_id": "int", "course_id": "int", "academic_year": "int",
        "semester": "str", "section": "str", "professor_name": "str_nullable",
        "syllabus_url": "str_nullable",
    },
    "course_schedules": {
        "schedule_id": "int", "offering_id": "int", "day_of_week": "str",
        "start_time": "time", "end_time": "time", "classroom": "str_nullable",
    },
    "course_keywords": {
        "keyword_id": "int", "offering_id": "int", "keyword": "str",
        "keyword_source": "str", "confidence_score": "decimal_nullable",
        "keyword_category": "str_nullable", "weight": "decimal_nullable",
        "source_text": "str_nullable",
    },
    "student_course_history": {
        "history_id": "int", "student_id": "int", "course_id": "int",
        "academic_year": "int_nullable", "semester": "str_nullable",
        "earned_credit": "decimal", "completion_status": "str",
        "is_retake": "bool", "attempt_no": "int",
        "original_history_id": "int_nullable", "credit_counted": "bool",
    },
    "academic_events": {
        "event_id": "int", "academic_year": "int", "semester": "str_nullable",
        "event_name": "str", "event_type": "str", "start_date": "date",
        "end_date": "date_nullable", "is_mandatory": "bool_nullable",
        "description": "str_nullable", "source_url": "str",
    },
    "notices": {
        "notice_id": "int", "source_board": "str", "title": "str",
        "category": "str_nullable", "posted_date": "date", "notice_url": "str",
        "content": "str_nullable",
    },
    "users": {
        "user_id": "int", "login_id": "str", "password_hash": "str", "role": "str",
    },
    "student_programs": {
        "student_program_id": "int", "student_id": "int", "program_id": "int",
        "program_role": "str", "selected_year": "int_nullable",
        "completion_status": "str_nullable", "created_at": "datetime",
    },
    "user_interests": {
        "user_interest_id": "int", "user_id": "int", "interest_type": "str",
        "keyword": "str", "created_at": "datetime",
    },
    "course_recommendations": {
        "recommendation_id": "int", "student_id": "int", "offering_id": "int",
        "match_score": "decimal", "reason": "str_nullable", "generated_at": "datetime",
    },
    "chat_sessions": {
        "session_id": "int", "user_id": "int", "created_at": "datetime",
        "updated_at": "datetime",
    },
    "chat_messages": {
        "message_id": "int", "session_id": "int", "sender_type": "str",
        "message_text": "str", "created_at": "datetime",
    },
    "program_policies": {
        "policy_id": "int", "program_id": "int", "policy_name": "str",
        "policy_text": "str", "effective_year": "int_nullable",
    },
    "program_scholarships": {
        "scholarship_id": "int", "program_id": "int", "scholarship_name": "str",
        "description": "str_nullable", "amount": "str_nullable", "criteria": "str_nullable",
    },
    "course_equivalencies": {
        "equivalence_id": "int", "primary_course_id": "int",
        "equivalent_course_id": "int", "program_id": "int_nullable", "note": "str_nullable",
    },
    "course_relationships": {
        "relationship_id": "int", "from_course_id": "int", "to_course_id": "int",
        "relationship_type": "str", "program_id": "int_nullable", "note": "str_nullable",
    },
}

# 삽입 순서 (FK 의존성 고려)
INSERT_ORDER = [
    "programs", "users", "students", "courses",
    "curriculum_courses", "graduation_requirements", "program_courses",
    "course_offerings", "course_schedules", "course_keywords",
    "student_course_history", "academic_events", "notices",
    "student_programs", "user_interests", "course_recommendations",
    "chat_sessions", "chat_messages",
    "program_policies", "program_scholarships",
    "course_equivalencies", "course_relationships",
]

# 테이블명 매핑
TABLE_NAMES = {
    "programs": "programs",
    "students": "students",
    "courses": "courses",
    "curriculum_courses": "curriculum_courses",
    "graduation_requirements": "graduation_requirements",
    "program_courses": "program_courses",
    "course_offerings": "course_offerings",
    "course_schedules": "course_schedules",
    "course_keywords": "course_keywords",
    "student_course_history": "student_course_history",
    "academic_events": "academic_events",
    "notices": "notices",
    "users": "users",
    "student_programs": "student_programs",
    "user_interests": "user_interests",
    "course_recommendations": "course_recommendations",
    "chat_sessions": "chat_sessions",
    "chat_messages": "chat_messages",
    "program_policies": "program_policies",
    "program_scholarships": "program_scholarships",
    "course_equivalencies": "course_equivalencies",
    "course_relationships": "course_relationships",
}


def escape_value(val, col_type):
    if val is None or str(val).strip() == "":
        if "nullable" in col_type:
            return "NULL"
        if col_type == "int":
            return "0"
        if col_type == "decimal":
            return "0.0"
        if col_type == "bool":
            return "FALSE"
        return "NULL"

    s = str(val).strip()

    if col_type in ("int", "int_nullable"):
        try:
            return str(int(float(s)))
        except:
            return "NULL"
    elif col_type in ("decimal", "decimal_nullable"):
        try:
            return str(float(s))
        except:
            return "NULL"
    elif col_type == "bool":
        return "TRUE" if s.lower() in ("true", "1", "yes") else "FALSE"
    elif col_type == "bool_nullable":
        if s.lower() in ("true", "1", "yes"):
            return "TRUE"
        elif s.lower() in ("false", "0", "no"):
            return "FALSE"
        return "NULL"
    elif col_type == "time":
        # 이미 HH:MM:SS 형태
        return f"'{s}'"
    elif col_type in ("date", "datetime"):
        if s:
            return f"'{s}'"
        return "NULL"
    elif col_type in ("str", "str_nullable"):
        escaped = s.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    return f"'{s}'"


# ============================================================
# Read DDL
# ============================================================
with open(os.path.join(BASE_DIR, "..", "database", "gradmanager_schema.sql"), "r", encoding="utf-8") as f:
    ddl_content = f.read()

# ============================================================
# Build dump
# ============================================================
lines = []
lines.append("-- ============================================================")
lines.append("-- GradManager (졸업을 부탁해) - MySQL 덤프 파일")
lines.append("-- Generated: 2026-07-19")
lines.append("-- Target: AISW학과 23~24학번 + 특화/융합전공")
lines.append("-- ============================================================")
lines.append("")
lines.append("SET NAMES utf8mb4;")
lines.append("SET FOREIGN_KEY_CHECKS = 0;")
lines.append("SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';")
lines.append("")
lines.append("-- -----------------------------------------------------------")
lines.append("-- 스키마 (DDL)")
lines.append("-- -----------------------------------------------------------")
lines.append("")
lines.append(ddl_content)
lines.append("")
lines.append("-- -----------------------------------------------------------")
lines.append("-- 데이터 (DML)")
lines.append("-- -----------------------------------------------------------")
lines.append("")

for table_name in INSERT_ORDER:
    types = TABLE_TYPES[table_name]
    rows, fields = read_csv(f"{table_name}.csv")

    if not rows:
        lines.append(f"-- {table_name}: (데이터 없음)")
        lines.append("")
        continue

    col_names = ", ".join(f"`{f}`" for f in fields)
    lines.append(f"-- {table_name} ({len(rows)}행)")
    lines.append(f"LOCK TABLES `{table_name}` WRITE;")

    CHUNK_SIZE = 100
    for chunk_start in range(0, len(rows), CHUNK_SIZE):
        chunk_rows = rows[chunk_start:chunk_start + CHUNK_SIZE]
        value_lines = []
        for row in chunk_rows:
            vals = []
            for f in fields:
                t = types.get(f, "str")
                vals.append(escape_value(row.get(f, ""), t))
            value_lines.append(f"({', '.join(vals)})")
        
        lines.append(f"INSERT INTO `{table_name}` ({col_names}) VALUES")
        lines.append(",\n".join(value_lines) + ";")

    lines.append(f"UNLOCK TABLES;")
    lines.append("")

lines.append("SET FOREIGN_KEY_CHECKS = 1;")
lines.append("")
lines.append("-- ============================================================")
lines.append("-- 덤프 완료")
lines.append("-- ============================================================")

# Write
with open(DUMP_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"MySQL 덤프 파일 생성 완료: {DUMP_PATH}")
print(f"파일 크기: {os.path.getsize(DUMP_PATH):,} bytes")
