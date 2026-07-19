# -*- coding: utf-8 -*-
"""
GradManager (졸업을 부탁해) - CSV Generation Script
===================================================
Generates 22 CSV files from:
- sugang.hs.ac.kr 2026-1학기 수강신청 JSON (660 courses, 1098 offerings, 743 schedules)
- PDF-extracted curriculum data (22 files in input_data/pdf_curriculum/)
- Crawled notices (231 from SW중심대학사업단)
- Academic events (40)
"""
import csv
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
PDF_DIR = os.path.join(BASE_DIR, "input_data", "pdf_curriculum")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SOURCE_URL_SUGANG = "https://sugang.hs.ac.kr/course/subject/list"
SOURCE_URL_NOTICES = "https://swuniv.hs.ac.kr/07_01"
SOURCE_URL_COURSE = "https://www.hs.ac.kr/sce/11212/subview.do"
SOURCE_URL_CURRICULUM = "https://swuniv.hs.ac.kr/02/02.php"
SOURCE_URL_AISW = "https://swuniv.hs.ac.kr/02/02.php"


# ============================================================
# Helper: read PDF CSV
# ============================================================
def read_pdf_csv(filename):
    path = os.path.join(PDF_DIR, filename)
    if not os.path.exists(path):
        print(f"  [WARN] {filename} not found")
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ============================================================
# Step 1: Load courses from sugang JSON
# ============================================================
print("=" * 60)
print("Step 1: Loading sugang JSON...")
JSON_PATH = os.path.join(BASE_DIR, "input_data", "all_courses_26_1.json")
with open(JSON_PATH, "r", encoding="utf-8-sig") as f:
    data = json.load(f)

subjects = data["subjectList"]
print(f"  JSON entries: {len(subjects)}")


# ============================================================
# Step 2: Parse sugang courses (고유 과목)
# ============================================================
print("Step 2: Parsing sugang courses...")
DAY_MAP = {"월": "월", "화": "화", "수": "수", "목": "목", "금": "금", "토": "토"}

courses_map = {}
courses_order = []

for s in subjects:
    code = s["GAESUL_GWAMOK"]
    if code in courses_map:
        continue
    credit_str = s.get("HAKJUM", "0").strip().replace("(", "").replace(")", "")
    try:
        credit = float(credit_str)
    except ValueError:
        credit = 0.0
    courses_map[code] = {
        "course_code": code,
        "course_name": s.get("GWAMOK_KORNAME", ""),
        "credit": credit,
        "theory_hours": credit,
        "practice_hours": 0.0,
        "course_description": s.get("GAESUL_BIGO", ""),
        "source_url": SOURCE_URL_SUGANG,
    }
    courses_order.append(code)

print(f"  Unique sugang courses: {len(courses_map)}")


# ============================================================
# Step 3: Build course_id mapping (sugang base)
# ============================================================
print("Step 3: Building course ID mapping...")
course_code_to_id = {}
for i, code in enumerate(courses_order, 1):
    course_code_to_id[code] = i

next_course_id = len(courses_order) + 1

# ============================================================
# Step 4: Load PDF courses and merge into course list
# ============================================================
print("Step 4: Loading PDF course data and merging...")

pdf_course_files = [
    ("specialization_courses.csv", "specialization"),
    ("convergence_courses.csv", "convergence"),
    ("aisw_flow_courses.csv", "aisw"),
    ("intro_modular_courses.csv", "intro"),
]

# Track: source_name → {internal_id → course_code}
pdf_id_to_code = {}
# Track: source_name → {internal_id → merged_course_id}
pdf_id_to_merged = {}

for filename, source_name in pdf_course_files:
    rows = read_pdf_csv(filename)
    pdf_id_to_code[source_name] = {}
    pdf_id_to_merged[source_name] = {}

    for row in rows:
        internal_id = row["course_id"].strip()
        course_code = row["course_code"].strip()
        course_name = row.get("course_name", "").strip()
        credits = float(row.get("credits", "3").strip() or "3")
        department = row.get("department", "").strip()
        description = row.get("description", "").strip()

        # Map internal_id → course_code
        pdf_id_to_code[source_name][internal_id] = course_code

        # Check if course_code already exists in sugang
        if course_code in course_code_to_id:
            merged_id = course_code_to_id[course_code]
        else:
            # Add as new course
            merged_id = next_course_id
            next_course_id += 1
            course_code_to_id[course_code] = merged_id
            courses_order.append(course_code)
            courses_map[course_code] = {
                "course_code": course_code,
                "course_name": course_name,
                "credit": credits,
                "theory_hours": credits,
                "practice_hours": 0.0,
                "course_description": description,
                "source_url": SOURCE_URL_CURRICULUM,
            }

        pdf_id_to_merged[source_name][internal_id] = merged_id

    print(f"  {filename}: {len(rows)} courses ({source_name})")

print(f"  Total courses after merge: {len(courses_map)}")


# ============================================================
# Step 5: Parse course offerings & schedules from sugang
# ============================================================
print("Step 5: Parsing offerings & schedules...")

def parse_time(gyosi_str):
    if not gyosi_str or gyosi_str.strip() == "-":
        return []
    results = []
    for part in gyosi_str.split("/"):
        part = part.strip()
        m = re.match(r'([월화목금토])\((\d{1,2}:\d{2})~(\d{1,2}:\d{2})\)', part)
        if m:
            results.append((DAY_MAP.get(m.group(1), m.group(1)), m.group(2), m.group(3)))
    return results

offerings = []
offering_id = 1
offering_key_map = {}

for s in subjects:
    code = s["GAESUL_GWAMOK"]
    section = s.get("GAESUL_BUNBAN", "A")
    prof = s.get("GYOSU_NAME", "")
    offering_key = (code, 2026, "1학기", section)
    if offering_key in offering_key_map:
        oid = offering_key_map[offering_key]
    else:
        oid = offering_id
        offerings.append({
            "offering_id": oid,
            "course_id": course_code_to_id.get(code, 0),
            "academic_year": 2026,
            "semester": "1학기",
            "section": section,
            "professor_name": prof,
            "syllabus_url": "",
        })
        offering_key_map[offering_key] = oid
        offering_id += 1

schedules = []
schedule_id = 1
for s in subjects:
    code = s["GAESUL_GWAMOK"]
    section = s.get("GAESUL_BUNBAN", "A")
    oid = offering_key_map.get((code, 2026, "1학기", section))
    if not oid:
        continue
    for day, start, end in parse_time(s.get("GYOSI", "-")):
        schedules.append({
            "schedule_id": schedule_id,
            "offering_id": oid,
            "day_of_week": day,
            "start_time": start,
            "end_time": end,
            "classroom": s.get("HOSU", ""),
        })
        schedule_id += 1

print(f"  Offerings: {len(offerings)}, Schedules: {len(schedules)}")


# ============================================================
# Step 6: Programs (merge all sources)
# ============================================================
print("Step 6: Building programs list...")

# program_id → program info
# We merge programs from: existing (7), aisw (5), intro (10), specialization (2), convergence (2)
# Deduplicate by name similarity

programs = []
program_name_to_id = {}
next_program_id = 1

def add_program(name, ptype, department, required_credits, effective_from, source_url, description=""):
    global next_program_id
    # Check for duplicate by name
    if name in program_name_to_id:
        return program_name_to_id[name]
    pid = next_program_id
    next_program_id += 1
    programs.append({
        "program_id": pid,
        "program_name": name,
        "program_type": ptype,
        "required_credits": required_credits,
        "effective_from_year": effective_from,
        "effective_to_year": "",
        "source_url": source_url,
    })
    program_name_to_id[name] = pid
    return pid

# 1. Existing base programs (AISW majors)
p_sw = add_program("AI·SW학 전공", "MAJOR", "", 36, 2023, SOURCE_URL_CURRICULUM)
p_ce = add_program("컴퓨터공학부", "MAJOR", "", 36, 2023, SOURCE_URL_CURRICULUM)
p_swc = add_program("소프트웨어융합학부", "MAJOR", "", 36, 2023, SOURCE_URL_CURRICULUM)
p_vfx = add_program("IT영상콘텐츠학과", "MAJOR", "", 36, 2023, SOURCE_URL_CURRICULUM)
p_spec1 = add_program("인지감성컴퓨팅 특화전공", "SPECIALIZED", "", 21, 2025, SOURCE_URL_CURRICULUM)
p_spec2 = add_program("앰비언트컴퓨팅 특화전공", "SPECIALIZED", "", 21, 2025, SOURCE_URL_CURRICULUM)
p_conv = add_program("AI SW 융합 전공", "CONVERGENCE", "", 21, 2023, SOURCE_URL_CURRICULUM)

# 2. AISW 이수체계도 programs (5 전공)
aisw_prog_rows = read_pdf_csv("aisw_programs.csv")
aisw_program_ids = {}
for row in aisw_prog_rows:
    pid = add_program(row["program_name"], row["program_type"], row["department"],
                       float(row["required_credits"]), 2023, SOURCE_URL_CURRICULUM)
    aisw_program_ids[int(row["program_id"])] = pid

# 3. SW중심대학 소개 programs (10 programs)
intro_prog_rows = read_pdf_csv("intro_programs.csv")
intro_program_ids = {}
for row in intro_prog_rows:
    pid = add_program(row["program_name"], row["program_type"], row["department"],
                       float(row["required_credits"]), 2023, SOURCE_URL_CURRICULUM)
    intro_program_ids[int(row["program_id"])] = pid

# 4. Specialization programs (from PDF)
spec_prog_rows = read_pdf_csv("specialization_programs.csv")
spec_program_ids = {}
for row in spec_prog_rows:
    pid = add_program(row["program_name"], row["program_type"], row["department"],
                       float(row["required_credits"]), 2026, SOURCE_URL_CURRICULUM)
    spec_program_ids[int(row["program_id"])] = pid

# 5. Convergence programs (from PDF)
conv_prog_rows = read_pdf_csv("convergence_programs.csv")
conv_program_ids = {}
for row in conv_prog_rows:
    pid = add_program(row["program_name"], row["program_type"], row["department"],
                       float(row["required_credits"]), 2026, SOURCE_URL_CURRICULUM)
    conv_program_ids[int(row["program_id"])] = pid

print(f"  Total programs: {len(programs)}")


# ============================================================
# Step 7: Curriculum Courses (from all PDF sources)
# ============================================================
print("Step 7: Building curriculum_courses...")

curriculum_courses = []
cc_id = 1

# 7a. Specialization curriculum
spec_curr_rows = read_pdf_csv("specialization_curriculum.csv")
for row in spec_curr_rows:
    pdf_course_id = row["course_id"].strip()
    merged_course_id = pdf_id_to_merged["specialization"].get(pdf_course_id, 0)
    merged_prog_id = spec_program_ids.get(int(row["program_id"]), 0)
    if merged_course_id and merged_prog_id:
        recommended = row.get("recommended_grade_min", "")
        sem = row.get("semester", "")
        sem_str = f"{sem}학기" if sem and "학기" not in sem else sem
        curriculum_courses.append({
            "curriculum_course_id": cc_id,
            "curriculum_year": 2026,
            "course_id": merged_course_id,
            "recommended_grade": int(recommended) if recommended else None,
            "semester": sem_str if sem_str else None,
            "completion_type": row.get("completion_type", "전공선택"),
            "is_required": row.get("is_recommended", "FALSE").strip().upper() == "TRUE",
            "note": row.get("note", ""),
            "program_id": merged_prog_id,
        })
        cc_id += 1

print(f"  Specialization curriculum: {len(spec_curr_rows)} rows")

# 7b. Convergence curriculum
conv_curr_rows = read_pdf_csv("convergence_curriculum.csv")
for row in conv_curr_rows:
    pdf_course_id = row["course_id"].strip()
    merged_course_id = pdf_id_to_merged["convergence"].get(pdf_course_id, 0)
    merged_prog_id = conv_program_ids.get(int(row["program_id"]), 0)
    if merged_course_id and merged_prog_id:
        recommended = row.get("recommended_grade_min", "")
        sem = row.get("semester", "")
        sem_str = f"{sem}학기" if sem and "학기" not in sem else sem
        curriculum_courses.append({
            "curriculum_course_id": cc_id,
            "curriculum_year": 2026,
            "course_id": merged_course_id,
            "recommended_grade": int(recommended) if recommended else None,
            "semester": sem_str if sem_str else None,
            "completion_type": row.get("completion_type", "전공선택"),
            "is_required": row.get("is_recommended", "FALSE").strip().upper() == "TRUE",
            "note": row.get("note", ""),
            "program_id": merged_prog_id,
        })
        cc_id += 1

print(f"  Convergence curriculum: {len(conv_curr_rows)} rows")

# 7c. AISW 이수체계도 curriculum
aisw_curr_rows = read_pdf_csv("aisw_curriculum.csv")
for row in aisw_curr_rows:
    pdf_course_code = row["course_id"].strip()
    merged_course_id = course_code_to_id.get(pdf_course_code, 0)
    merged_prog_id = aisw_program_ids.get(int(row["program_id"]), 0)
    if merged_course_id and merged_prog_id:
        recommended = row.get("recommended_grade_min", "")
        sem = row.get("semester", "")
        sem_str = f"{sem}학기" if sem and "학기" not in sem else sem
        curriculum_courses.append({
            "curriculum_course_id": cc_id,
            "curriculum_year": 2026,
            "course_id": merged_course_id,
            "recommended_grade": int(recommended) if recommended else None,
            "semester": sem_str if sem_str else None,
            "completion_type": row.get("completion_type", "전공선택"),
            "is_required": row.get("is_recommended", "FALSE").strip().upper() == "TRUE",
            "note": row.get("note", ""),
            "program_id": merged_prog_id,
        })
        cc_id += 1

print(f"  AISW curriculum: {len(aisw_curr_rows)} rows")
print(f"  Total curriculum_courses: {len(curriculum_courses)}")


# ============================================================
# Step 8: Program Courses (from all PDF sources)
# ============================================================
print("Step 8: Building program_courses...")

program_courses = []
pc_id = 1

# 8a. Specialization program_courses
spec_pc_rows = read_pdf_csv("specialization_program_courses.csv")
for row in spec_pc_rows:
    pdf_course_id = row["course_id"].strip()
    merged_course_id = pdf_id_to_merged["specialization"].get(pdf_course_id, 0)
    merged_prog_id = spec_program_ids.get(int(row["program_id"]), 0)
    if merged_course_id and merged_prog_id:
        program_courses.append({
            "program_course_id": pc_id,
            "program_id": merged_prog_id,
            "course_id": merged_course_id,
            "effective_year": 2026,
            "recognition_credit": 3.0,
            "is_required": None,
            "note": row.get("note", ""),
        })
        pc_id += 1

print(f"  Specialization program_courses: {len(spec_pc_rows)} rows")

# 8b. Convergence program_courses
conv_pc_rows = read_pdf_csv("convergence_program_courses.csv")
for row in conv_pc_rows:
    pdf_course_id = row["course_id"].strip()
    merged_course_id = pdf_id_to_merged["convergence"].get(pdf_course_id, 0)
    merged_prog_id = conv_program_ids.get(int(row["program_id"]), 0)
    if merged_course_id and merged_prog_id:
        program_courses.append({
            "program_course_id": pc_id,
            "program_id": merged_prog_id,
            "course_id": merged_course_id,
            "effective_year": 2026,
            "recognition_credit": 3.0,
            "is_required": None,
            "note": row.get("note", ""),
        })
        pc_id += 1

print(f"  Convergence program_courses: {len(conv_pc_rows)} rows")

# 8c. AISW program_courses
aisw_pc_rows = read_pdf_csv("aisw_program_courses.csv")
for row in aisw_pc_rows:
    pdf_course_code = row["course_id"].strip()
    merged_course_id = course_code_to_id.get(pdf_course_code, 0)
    merged_prog_id = aisw_program_ids.get(int(row["program_id"]), 0)
    if merged_course_id and merged_prog_id:
        program_courses.append({
            "program_course_id": pc_id,
            "program_id": merged_prog_id,
            "course_id": merged_course_id,
            "effective_year": int(row.get("effective_year", "2026")),
            "recognition_credit": 3.0,
            "is_required": None,
            "note": row.get("note", ""),
        })
        pc_id += 1

print(f"  AISW program_courses: {len(aisw_pc_rows)} rows")

# 8d. Intro program_courses (career path mapping)
intro_pc_rows = read_pdf_csv("intro_program_courses.csv")
for row in intro_pc_rows:
    pdf_course_code = row["course_id"].strip()
    merged_course_id = course_code_to_id.get(pdf_course_code, 0)
    merged_prog_id = intro_program_ids.get(int(row["program_id"]), 0)
    if merged_course_id and merged_prog_id:
        note = row.get("note", "")
        career = row.get("career_path", "")
        if career:
            note = f"진로: {career}" + (f"; {note}" if note else "")
        program_courses.append({
            "program_course_id": pc_id,
            "program_id": merged_prog_id,
            "course_id": merged_course_id,
            "effective_year": 2026,
            "recognition_credit": 3.0,
            "is_required": None,
            "note": note,
        })
        pc_id += 1

print(f"  Intro program_courses: {len(intro_pc_rows)} rows")
print(f"  Total program_courses: {len(program_courses)}")


# ============================================================
# Step 9: Graduation Requirements (merge all sources)
# ============================================================
print("Step 9: Building graduation_requirements...")

grad_requirements = []
gr_id = 1

# 9a. Base graduation requirements (23/24학번)
base_reqs = [
    ("", "총 이수학점", 130, "교양+계열공통+전공+타전공 합계 130학점 이상", 2023),
    ("", "교양 최소학점", 35, "교양 최소 35학점 이상 이수 필요", 2023),
    ("", "교양 최대학점(인정한도)", 45, "교양 최대 45학점까지 인정", 2023),
    ("", "계열공통", 36, "AI SW 계열공통 36학점 이수 필요", 2023),
    (str(p_sw), "전공(전공필수+전공선택)", 24, "AI·SW학 전공 전필+전선 합계 최소 24학점 이상", 2023),
    (str(p_spec1), "특화전공", 21, "인지감성컴퓨팅 특화전공: 21학점 이상", 2023),
    (str(p_spec2), "특화전공", 21, "앰비언트컴퓨팅 특화전공: 21학점 이상", 2023),
    ("", "기독교 관련 교양필수", None, "기독교와문화(A) 또는 성서의세계(A) 1과목 이상 이수 필수", 2023),
    ("", "채플", None, "채플 매 학기 0.5학점 이상 이수", 2023),
    ("", "타전공", None, "타전공 이수는 필수사항이 아니나, 이수 시 추가 학점 인정 가능", 2023),
    ("", "총 이수학점", 130, "교양+계열공통+전공+타전공 합계 130학점 이상", 2024),
    ("", "교양 최소학점", 35, "교양 최소 35학점 이상 이수 필요", 2024),
    ("", "교양 최대학점(인정한도)", 45, "교양 최대 45학점까지 인정", 2024),
    ("", "계열공통", 36, "AI SW 계열공통 36학점 이수 필요", 2024),
    (str(p_sw), "전공(전공필수+전공선택)", 24, "AI·SW학 전공 전필+전선 합계 최소 24학점 이상", 2024),
    (str(p_spec1), "특화전공", 21, "인지감성컴퓨팅 특화전공: 21학점 이상", 2024),
    (str(p_spec2), "특화전공", 21, "앰비언트컴퓨팅 특화전공: 21학점 이상", 2024),
    ("", "기독교 관련 교양필수", None, "기독교와문화(A) 또는 성서의세계(A) 1과목 이상 이수 필수", 2024),
    ("", "채플", None, "채플 매 학기 0.5학점 이상 이수", 2024),
    ("", "타전공", None, "타전공 이수는 필수사항이 아니나, 이수 시 추가 학점 인정 가능", 2024),
]

for prog_id_str, cat, credits, text, year in base_reqs:
    pid = int(prog_id_str) if prog_id_str else None
    grad_requirements.append({
        "requirement_id": gr_id,
        "admission_year": year,
        "program_id": pid,
        "requirement_category": cat,
        "required_credits": credits,
        "requirement_text": text,
        "source_url": SOURCE_URL_COURSE,
    })
    gr_id += 1

# 9b. Intro graduation requirements
intro_gr_rows = read_pdf_csv("intro_grad_req.csv")
for row in intro_gr_rows:
    merged_prog_id = intro_program_ids.get(int(row["program_id"]), 0)
    credits_str = row.get("required_credits", "")
    credits_val = float(credits_str) if credits_str else None
    grad_requirements.append({
        "requirement_id": gr_id,
        "admission_year": 2023,
        "program_id": merged_prog_id,
        "requirement_category": row.get("requirement_category", ""),
        "required_credits": credits_val,
        "requirement_text": row.get("note", ""),
        "source_url": SOURCE_URL_CURRICULUM,
    })
    gr_id += 1

# 9c. Specialization graduation requirements
spec_gr_rows = read_pdf_csv("specialization_curriculum.csv")
# Count credits per program
spec_credits = {}
for row in spec_gr_rows:
    pid = spec_program_ids.get(int(row["program_id"]), 0)
    spec_credits[pid] = spec_credits.get(pid, 0) + 3
for pid, credits in spec_credits.items():
    pname = next((p["program_name"] for p in programs if p["program_id"] == pid), "")
    grad_requirements.append({
        "requirement_id": gr_id,
        "admission_year": 2026,
        "program_id": pid,
        "requirement_category": "특화전공 최소 이수학점",
        "required_credits": credits,
        "requirement_text": f"{pname}: 전공선택 {credits}학점 이상 이수 필요",
        "source_url": SOURCE_URL_CURRICULUM,
    })
    gr_id += 1

# 9d. Convergence graduation requirements
conv_gr_rows = read_pdf_csv("convergence_curriculum.csv")
conv_credits = {}
for row in conv_gr_rows:
    pid = conv_program_ids.get(int(row["program_id"]), 0)
    conv_credits[pid] = conv_credits.get(pid, 0) + 3
for pid, credits in conv_credits.items():
    pname = next((p["program_name"] for p in programs if p["program_id"] == pid), "")
    grad_requirements.append({
        "requirement_id": gr_id,
        "admission_year": 2026,
        "program_id": pid,
        "requirement_category": "융합전공 최소 이수학점",
        "required_credits": credits,
        "requirement_text": f"{pname}: 전공선택 {credits}학점 이상 이수 필요",
        "source_url": SOURCE_URL_CURRICULUM,
    })
    gr_id += 1

# 9e. AISW graduation requirements
aisw_gr_credits = {}
aisw_curr_rows2 = read_pdf_csv("aisw_curriculum.csv")
for row in aisw_curr_rows2:
    pid = aisw_program_ids.get(int(row["program_id"]), 0)
    ct = row.get("completion_type", "")
    if ct in ("전공필수", "전공선택"):
        aisw_gr_credits[pid] = aisw_gr_credits.get(pid, 0) + 3
for pid, credits in aisw_gr_credits.items():
    pname = next((p["program_name"] for p in programs if p["program_id"] == pid), "")
    grad_requirements.append({
        "requirement_id": gr_id,
        "admission_year": 2023,
        "program_id": pid,
        "requirement_category": "전공(전공필수+전공선택)",
        "required_credits": credits,
        "requirement_text": f"{pname}: 전공필수+전공선택 합계 {credits}학점",
        "source_url": SOURCE_URL_AISW,
    })
    gr_id += 1

print(f"  Total graduation_requirements: {len(grad_requirements)}")


# ============================================================
# Step 10: Notices (231 notices)
# ============================================================
print("Step 10: Loading notices...")

NOTICES_RAW = [
    (None, "[공지] 2026-2학기 융합/특화전공 신청 안내", "2026-07-15", "학사"),
    (None, "[공지] AI아트코딩과윤리 멘토링 신청안내", "2026-03-19", "학사"),
    (229, "[홍보] ACPC 2026 (AWS x Codetree) 전국 대학생/대학원생 프로그래밍 경진대회 개최 안내", "2026-07-16", "행사"),
    (228, "[안내] 2026년 관광데이터 활용 공모전 웹·앱 구현 부문 모집 안내 (~7/21까지)", "2026-07-15", "행사"),
    (227, "[공지] 2026 SW중심대학 학생 주도형 아이디어 공모전 결과 발표 일정 변경 안내", "2026-07-07", "학사"),
    (226, "[공지] 2026년도 1학기 SW포인트(소중한 포인트) 신청 안내", "2026-06-30", "장학"),
    (225, "[안내] 2026 상반기 교재개발 사업 안내 (접수기한 연장)", "2026-06-24", "학사"),
    (224, "[홍보] 2026년 코디세이 올인원 교육 과정", "2026-06-19", "행사"),
    (223, "[홍보] [경기대학교] 2026 AI-Powered 『경기대학교-크래프톤 정글 웹개발 집중 캠프』 참가", "2026-06-15", "행사"),
    (222, "[홍보] (삼육대학교) [특화트랙 대학 연합] 2026년 AI+X 미래혁신 융합 아이디어톤", "2026-06-15", "행사"),
    (221, "[공지] 2026 SW중심대학 디지털경진대회 학교 대표 선발 안내", "2026-06-08", "학사"),
    (220, "[공지] 2026-1학기 SW융합/특화전공 장학금 신청 안내", "2026-06-04", "장학"),
    (219, "[안내] (양식 변경) 2026 한일 브릿지 아이디어톤 참가자 모집", "2026-06-04", "학사"),
    (218, "[마감] 2026년 SW중심대학 디지털경진대회 학생 선발 안내 (접수마감)", "2026-04-29", "학사"),
    (217, "[공지] 제1차 한신 AISW 알고리즘 공개 경진대회 결과 안내", "2026-06-02", "학사"),
    (216, "[홍보] 2026 소상공인 온라인 플랫폼 역량강화 교육생 모집", "2026-06-01", "행사"),
    (215, "[홍보] 2026 경기 가상융합 캠퍼스 정규교육과정 모집 (~6/30까지)", "2026-06-01", "행사"),
    (214, "[안내] 2026 SW중심대학 학생 주도형 아이디어 공모전 안내", "2026-05-22", "학사"),
    (213, "[안내] 제1차 한신 AISW 알고리즘 공개 경진대회 안내", "2026-05-20", "학사"),
    (212, "[홍보] 제9회 국민대학교 자율주행 경진대회 (~5/22까지 접수)", "2026-05-14", "행사"),
    (211, "[홍보] 2026 관광데이터 활용 공모전(생성형 AI 활용 관광 프롬프톤 부문)(~5/20 16:00까지)", "2026-05-13", "행사"),
    (210, "[안내] 2026-2학기 융합/특화전공 신청 안내", "2026-05-13", "학사"),
    (209, "2026 산학협력 프로젝트 선정자 공지", "2026-05-12", "기타"),
    (208, "[안내] SW 전문가 특강 안내 (주제: 지능형 센서 시스템 관련 직무 이야기)", "2026-05-07", "학사"),
    (207, "[홍보] 2026 AI Pilot Top Gun Challenge 참가팀 모집(기한: 5/19까지)", "2026-05-07", "행사"),
    (206, "[공지] 오픈소스 SW 동아리 학생 선발 안내", "2026-05-06", "학사"),
    (205, "[공지] 2026년 AI-SW중심대학 AI·블록체인 비즈니스모델 경진대회 최종평가 대상자 안내", "2026-05-06", "학사"),
    (204, "[안내] 2026년도 SW중심대학사업 학술대회 참가등록비 지원 사업 안내", "2026-04-28", "학사"),
    (203, "[안내] 2026 산학협력 프로젝트 선정과제 공지 및 학생연구원 신청 안내", "2026-04-27", "학사"),
    (202, "[홍보] 2026 SW전공교수 TOPCIT 릴레이 특강 참여 안내", "2026-04-27", "행사"),
    (201, "[안내] 2026 오픈소스 SW 동아리 신청 안내(~4/30 13:00까지)", "2026-04-21", "학사"),
    (200, "[안내] 2026-1학기 SW중심대학 노트북 대여 신청 안내(2차)", "2026-04-21", "학사"),
    (199, "[공지] 융합/특화동아리 학생 선발 안내", "2026-04-20", "학사"),
    (198, "[정정공고] 2026 산학협력 프로젝트 신청 안내 (연구자, 학생)", "2026-04-17", "학사"),
    (197, "[홍보] 제16회 SW개발 공모전 사전설명회 신청 및 접수(~4.26)", "2026-04-15", "행사"),
    (196, "[공지] 2026 SW중심대학 에세이 공모전 교내 최종 출품작 선정 결과 안내", "2026-04-14", "학사"),
    (195, "[홍보] 2026년 관광데이터 활용 공모전 웹·앱 개발 부문 (기한: ~5/6까지)", "2026-04-14", "행사"),
    (194, "[홍보] 서울 플레이업 AI 게임 챌린지 공모전 (4/10~5/7)", "2026-04-13", "행사"),
    (193, "[홍보] 전국민 AI경진대회 (대학생 트랙: 인공지능 루키대회) 기한: ~5/8까지)", "2026-04-13", "행사"),
    (192, "[홍보] OpenAPI를 활용한 2026 관광데이터 활용 공모전 개최(웹·앱 개발 부문) (~5/6까지)", "2026-04-08", "행사"),
    (191, "[안내] 2026년 SW중심대학 AI·블록체인 비지니스 모델 경진대회(~4/24까지)", "2026-04-08", "학사"),
    (190, "2026 산학협력 프로젝트 신청 안내 (연구자, 학생)", "2026-04-07", "기타"),
    (189, "[홍보] 경북 국제 AI·메타버스 영상 공모전(GAMFF AI 영상 공모전)", "2026-04-07", "행사"),
    (188, "[공지] [IITP]TOPCIT 설명회 (4/10 오후 1:00, 송암관)", "2026-04-06", "학사"),
    (187, "[안내] 2026 융합/특화동아리 신청 안내(~4/15 17:00까지)", "2026-04-06", "학사"),
    (186, "[공지] 제25회 TOPCIT 정기시험 접수 안내 (~4/15 17:00까지)", "2026-04-03", "학사"),
    (185, "2026 산학협력 프로젝트 설명회 개최 4/7(화) 점심시간", "2026-04-02", "학사"),
    (184, "[홍보] 2026년 AI ROOKIE 대회 (신청기간: ~5/8 17:00까지)", "2026-03-31", "행사"),
    (183, "[공지] 전공탐색박람회 융합/특화전공 상담 부스 안내", "2026-03-30", "학사"),
    (182, "[공지] 2026-1 클린코딩클리닉 멘토 추가신청 안내!!! (조별신청마감)", "2026-03-10", "학사"),
    (181, "[소중협] 2026 SW중심대학 에세이 공모전 (제출기한: ~4/10까지)", "2026-03-09", "학사"),
    (180, "[안내] 2026-1학기 SW중심대학 노트북 대여 신청 안내", "2026-03-04", "학사"),
    (179, "[공지] 2026 융합전공 설명회 (사전신청: ~3/4(수)까지)", "2026-02-26", "학사"),
    (178, "[공지] 2026 특화전공 설명회 (사전신청: ~3/3(화)까지)", "2026-02-26", "학사"),
    (177, "[안내] SW융합/특화전공 장학금 지급 기준", "2026-02-25", "장학"),
    (176, "[홍보] 이노베이션아카데미_2026 코디세이 AI 올인원 제1기 교육생 모집 안내", "2026-02-24", "행사"),
    (175, "[안내] 2026 한신대학교 SW중심대학 산학협력 프로젝트 기술수요조사(~3/27 금)", "2026-02-20", "학사"),
    (174, "[홍보] [경기대학교] 국가공인 SW테스트 전문가 CSTS 자격시험 안내", "2026-02-09", "행사"),
    (173, "[공지] 2026-1학기 융합전공 신청 안내 (4차 접수 마감)", "2026-02-03", "학사"),
    (172, "[공지] 2026 입학전특별교육 생성형AI맛보기 캠프 안내", "2026-02-02", "학사"),
    (171, "[공지] 26-1학기 융합/특화전공 수강신청 및 분반 개설시간표 안내", "2026-01-26", "학사"),
    (170, "[공지] 2026-1학기 융합/특화전공 신청 안내 (일정 변경)", "2026-01-13", "학사"),
    (169, "[공지] 2026년도 AI·SW마에스트로 과정 제17기 연수생 모집 공고", "2026-01-12", "학사"),
    (168, "[신입생] 2026학년도 입학전특별교육 SW교과목 수강 안내", "2026-01-08", "학사"),
    (167, "[공지] 2025-2학기 SW포인트 지급 예정자 명단", "2025-12-22", "장학"),
    (166, "[공지] 2025-동계 방중 사무실 이전 안내", "2025-12-17", "학사"),
    (165, "[안내] 디지털라이프케어서비스 교과목 교재개발 안내", "2025-12-15", "학사"),
    (164, "[홍보] LG Aimers 8기 모집 안내 (기한: ~12/18)", "2025-12-12", "행사"),
    (163, "[공지] AI GPU 서버 활용 방법 설명회 안내(교원 및 대학원 대상)", "2025-12-08", "학사"),
    (162, "[공지] 2025-2학기 SW융합/특화전공 장학금 신청 안내 (일정 변경)", "2025-12-04", "장학"),
    (161, "[공지] 2025년도 2학기 SW포인트(소중한 포인트) 신청 안내(기한: ~12/11까지)", "2025-12-04", "장학"),
    (160, "[공지] 특화전공 설명회 안내(12/3)", "2025-11-27", "학사"),
    (159, "[공지] 2025 한신 AI·SW 페스티벌 수상자 및 상장 수령 안내", "2025-11-26", "학사"),
    (158, "[공지] 2026-1학기 융합/특화전공 신청 안내", "2025-11-16", "학사"),
    (157, "[공지] 2025 한신 AI·SW 페스티벌 시상식 참석자 안내", "2025-11-13", "학사"),
    (156, "[공지] 2025 한신 AI·SW 페스티벌 경진대회 발표 심사 안내", "2025-11-12", "학사"),
    (155, "[공지] 특화전공 2025학년도 겨울계절학기 개설 교과목 안내", "2025-11-12", "학사"),
    (154, "2025 SW인재페스티벌 안내 (11/27~28, 서울 용산 드래곤시티 3층)", "2025-11-10", "행사"),
    (153, "[긴급공지] 기업탐방 프로그램 스마일게이트 추가인원 모집 (2명 선착순)", "2025-11-06", "학사"),
    (152, "[공지] 2025년도 SW중심대학사업 2026 CES 참관 합격자 안내", "2025-11-05", "학사"),
    (151, "[안내] 2025 한신 AI·SW페스티벌 행사에 초대합니다(11/18~19)", "2025-11-03", "학사"),
    (150, "[공지] AI·SW 창업아이디어 경진대회 2차 합격자 발표", "2025-11-03", "학사"),
    (149, "[공지] AI·SW 일반 경진대회 1차 합격자 발표", "2025-11-03", "학사"),
    (148, "[공지] AI·SW 창업아이디어 경진대회 1차 합격자 발표", "2025-10-27", "학사"),
    (147, "[홍보] 경기대 SW전공교수 TOPCIT 릴레이 특강", "2025-10-21", "행사"),
    (146, "[홍보] AI 시대, SW 엔지니어의 글로벌 취·창업 전략 참가자모집 (~10/24)", "2025-10-21", "행사"),
    (145, "[홍보] 제27회 아이디어 유니버시아드 대회 (기한:~11/4까지예선접수)", "2025-10-21", "행사"),
    (144, "[홍보] [경기글로벌게임센터] AI를 활용한 게임 개발 실무 교육 과정(11/4)", "2025-10-20", "행사"),
    (143, "[모집] 2025-2학기 노트북 대여 안내(2차)", "2025-10-20", "학사"),
    (142, "[공지] SW해외연수 프로그램 2026 CES참관 참가자 모집", "2025-10-17", "학사"),
    (141, "[홍보] AI 모의 면접 관련 설명회 및 사전 신청 공지", "2025-10-16", "행사"),
    (140, "[공지] AI·SW 캡스톤디자인 경진대회 참가학생 접수번호, 과제번호 공유", "2025-10-16", "학사"),
    (139, "[홍보] SW중심대학과 함께하는 오픈소스 특강 안내_삼성전자 박수홍 오픈소스그룹장", "2025-10-14", "행사"),
    (138, "[공지] 2025 강촌 캡스톤디자인 및 AI해커톤대회 참여자 선발 명단", "2025-10-14", "학사"),
    (137, "[수요조사] [기업탐방]스마일게이트xDDP(2025. 12. 5., 판교) (기한: 10/15 오전 10시까지)", "2025-10-02", "학사"),
    (136, "[AI·SW페스티벌] 휴먼서비스대학 AI·SW 개발 공모 일반 경진대회 참가자 모집", "2025-10-01", "학사"),
    (135, "[소중협] 2025 SW중심대학 에세이 공모전 안내 (응모기간 : 10. 1.~10. 14.)", "2025-09-30", "학사"),
    (134, "[공지] 오픈소스 SW 동아리 선발자", "2025-09-30", "학사"),
    (133, "[공지] 2025 SUMTECH해커톤 선발 명단", "2025-09-24", "학사"),
    (132, "[공지] 5개대학연합 2025 캡스톤디자인 및 AI 해커톤 참여자 모집(~10/13까지 기한 연장)", "2025-09-03", "학사"),
    (131, "[홍보] 2025학년도 AI·SW취업특강 신청자모집 (점심식사제공)_모의면접진행 안내", "2025-09-22", "행사"),
    (130, "[AI·SW페스티벌] AI아트코딩 공모전 참가자 모집", "2025-09-22", "학사"),
    (129, "[추가모집] 2025년 하반기 제24회 TOPCIT 정기평가 접수 안내 (~9/24)", "2025-09-22", "학사"),
    (128, "[SW중심대학사업] 2025-2학기 노트북 대여 안내(2차)", "2025-09-16", "학사"),
    (127, "[AI·SW페스티벌] AI·SW 개발 공모 캡스톤디자인 경진대회 참가자 모집", "2025-09-15", "학사"),
    (126, "[AI·SW페스티벌] AI·SW 개발 공모 일반 경진대회 참가자 모집", "2025-09-15", "학사"),
    (125, "[AI·SW페스티벌] AI·SW 창업아이디어경진대회 참가자 모집", "2025-09-15", "학사"),
    (124, "[홍보] [한양대학교SW중심대학사업단] 2025 전국 대학생 SW창업 아이디어톤", "2025-09-12", "행사"),
    (123, "[안내] 2025년 SW창업 동아리 모집", "2025-09-12", "학사"),
    (122, "[안내] 2025학년도 2학기 OSS 특강 신청 안내", "2025-09-10", "학사"),
    (121, "[안내] 오픈소스 SW 동아리 신청자 모집 (~9/26)", "2025-09-10", "학사"),
    (120, "2025년 하반기 제24회 TOPCIT 정기평가 접수 안내 (~9/18)", "2025-09-10", "학사"),
    (119, "[공지] 10개대학연합 SUMTECH Hackathon 2025", "2025-09-05", "학사"),
    (118, "[알림] 제23회 TOPCIT 성적 우수학생 총장상, 단장상 수상자 안내", "2025-09-03", "학사"),
    (117, "[SW교육센터] 생성형 AI 공모전 멘토링(프롬프트 클리닉) 신청 안내", "2025-09-03", "학사"),
    (116, "[재공지] SW중심대학사업단 에세이 공모전 방학 미션 SW중심대학덕분에", "2025-09-03", "학사"),
    (115, "[홍보] 2025학년도 청년창업특강 신청자모집 (점심식사제공)", "2025-09-02", "행사"),
    (114, "[SW교육센터] 2025학년도 2학기 클린코딩클리닉 신청 안내", "2025-09-02", "학사"),
    (113, "[SW중심대학사업] 2025-2학기 노트북 대여 안내(1차)", "2025-08-25", "학사"),
    (112, "[안내] 2025-1학기 SW포인트 신청자 명단", "2025-08-25", "장학"),
    (111, "[안내] SW포인트 신청 확인 필요 명단", "2025-08-21", "장학"),
    (110, "[SW교육센터] 2025학년도 2학기 실습강의 근로장학생 선발 공고(80시간)", "2025-08-21", "학사"),
    (109, "[안내] SW포인트 중 창업특강 참가 이력 확인 요망", "2025-08-18", "장학"),
    (108, "[홍보] [충북대 산업인공지능센터] +AI Make A Thon", "2025-07-31", "행사"),
    (107, "[홍보] [경기복지재단] 2026년 신규 사업 발굴 아이디어 공모전", "2025-07-23", "행사"),
    (106, "[안내] 2025 상반기 교재/교안 개발 지원 사업 안내", "2025-07-23", "학사"),
    (105, "[안내] 25-2학기 융합/특화전공 수강신청 및 분반 개설시간표 안내", "2025-07-22", "학사"),
    (104, "[공고] SW중심대학사업단 에세이 공모전 방학 미션 SW중심대학덕분에", "2025-07-18", "학사"),
    (103, "[홍보] 경기대 2025 CSTS 썸머특강 안내 (7.21~7.23, ZOOM)", "2025-07-16", "행사"),
    (102, "[홍보] 경기대학교-크래프톤 정글 웹개발 집중 캠프(8/11~8/22)", "2025-07-15", "행사"),
    (101, "[안내] 2025학년도 2학기 융합/특화전공 신청 안내(5차 접수 마감)", "2025-07-15", "학사"),
    (100, "[홍보] 2025 노인·장애인 보조기기 개발 제6회 국립재활원 보조기기 해커톤 참가자 모집", "2025-07-11", "행사"),
    (99, "2025학년도 1학기 SW융합/특화전공 장학금 증빙 제출 안내", "2025-07-08", "장학"),
    (98, "[안내] 제11회 부산 창업 아이디어 경진대회 참가자 모집 공고(총 상금 6,150만원)", "2025-07-07", "행사"),
    (97, "(추가안내) 2025년 1학기 SW포인트(소중한 포인트) 신청 안내", "2025-07-01", "장학"),
    (96, "[재안내] 2025년도 SW포인트(소중한포인트) 안내", "2025-04-24", "장학"),
    (95, "[안내] 2025 청년 창업가 양성 지원사업(몽골)", "2025-06-25", "학사"),
    (94, "[한라대학교 SW중심대학사업단] HL FMA 자율주행 경진대회", "2025-06-19", "행사"),
    (93, "2025년 ICT 학점연계 프로젝트 인턴십 실습생 모집 안내(~7/10)", "2025-06-19", "학사"),
    (92, "[공지] MARS2025 관련 안내", "2025-06-13", "학사"),
    (91, "[안내] 안랩클라우드메이트 인턴 추천 채용(기한: ~6/17까지)", "2025-06-09", "학사"),
    (90, "[공지] 화성특례시 MARS 2025 현장 체험학습 사전 수요조사", "2025-06-05", "학사"),
    (89, "[안내] 2025-1 클린코딩클리닉 튜티 신청 기한 연장(~6/16)", "2025-06-05", "학사"),
    (88, "[공지] SW중심대학 SW창업캠프 선발 최종 결과 안내", "2025-06-04", "학사"),
    (87, "[공지] SW중심대학 디지털경진대회 선발 최종 결과 안내", "2025-05-30", "학사"),
    (86, "[공지] SW동아리 (융합/특화) 선발 안내", "2025-05-28", "학사"),
    (85, "[홍보] 2025 오픈소스 개발자대회 (기한: ~6.30까지)", "2025-05-28", "행사"),
    (84, "[홍보] 네이버클라우드 인공지능(AI)전문인력 양성과정 (기한: ~5월 28일까지)", "2025-05-27", "행사"),
    (83, "[안내] 청년창업특강 비교과 마일리지 지급 방법 안내(~6/6 00시 마감)", "2025-05-27", "학사"),
    (82, "[연장안내] 2025 SW중심대학 디지털경진대회 참가 팀 모집 안내_AI부문(기한:~5/30까지)", "2025-04-22", "학사"),
    (81, "[안내] 2025-1 클린코딩클리닉 튜터 신청 기한 연장(~5/30)", "2025-05-21", "학사"),
    (80, "[안내] (사)한국디지털콘텐츠학회 2025년도 하계 종합학술대회 및 대학생논문경진대회 투고료 지원", "2025-05-20", "학사"),
    (79, "[안내] SW중심대학사업 특화트랙 연합 2025 SW창업 캠프(7/14~7/18)", "2025-05-20", "학사"),
    (78, "[안내] SW융합·특화전공 포트폴리오 설명회 개최 일정 변경", "2025-05-20", "학사"),
    (77, "[안내] SW융합전공 및 SW특화전공 신청 안내", "2025-05-19", "학사"),
    (76, "[안내] SW융합·특화전공 포트폴리오 설명회 개최", "2025-05-16", "학사"),
    (75, "[모집 기간 연장] SW융합동아리 모집 공고(기한: ~5/23까지)", "2025-05-14", "학사"),
    (74, "[홍보] 2025 창의적 아이템 기반 기술 창업 활성화 교육(기한: ~5/26까지)", "2025-05-13", "행사"),
    (73, "[홍보] (경기대학교) 2025 AI-Powered SW전공교수 TOPCIT 릴레이 특강", "2025-05-13", "행사"),
    (72, "[홍보] 2025년 가상융합서비스 개발자 경진대회(기한:~6/12까지)", "2025-05-12", "행사"),
    (71, "[안내] 2025년 SW중심대학 AI창업 및 블록체인 창업 아이디어 경진대회 안내", "2025-05-09", "학사"),
    (70, "[홍보] 생성형AI·공공데이터 창업경진대회 (기한: 5.30까지)", "2025-05-08", "행사"),
    (69, "[안내] 2025-1 클린코딩클리닉 참여자 모집 안내", "2025-04-28", "학사"),
    (68, "[안내] SW 융합/특화 동아리(LAB) 신청자 모집(~5/9)", "2025-04-24", "학사"),
    (67, "[홍보] AI 및 컴퓨터 비전을 통한 이미지 분류기 만들기 교육프로그램", "2025-04-24", "행사"),
    (66, "[홍보/마감] 비교과 마일리지·SW포인트지급 2025 청년창업특강 신청자 모집", "2025-04-22", "행사"),
    (65, "[홍보] 2025 아이소리공모전 개최(기한: ~6/30까지)", "2025-04-22", "행사"),
    (64, "[안내] 2025 산학협력프로젝트 선정관련 정보 공개", "2025-04-22", "학사"),
    (63, "[홍보] 배리어프리 앱 개발 콘테스트(신청기한: 5/21, 5시까지)", "2025-04-21", "행사"),
    (62, "[홍보] 2025 서울특별시장애청소년IT챌린지 IT체험 부스운영 대학생 서포터즈 모집", "2025-04-18", "행사"),
    (61, "[홍보] 제23회 TOPCIT 정기평가 설명회 안내", "2025-04-14", "행사"),
    (60, "[안내] 제23회 상반기 TOPCIT 정기평가 응시자 모집", "2025-04-10", "학사"),
    (59, "[안내] 2025 산학협력 프로젝트 선정과제 공지 및 학생연구원 신청 안내", "2025-04-07", "학사"),
    (58, "[안내] 2025년 SW중심대학 AI 창업 아이디어 경진대회 참가를 위한 온라인 교육 진행 (4/9)", "2025-04-04", "학사"),
    (57, "[수정 안내] 2025 산학협력 프로젝트 정정 공고 (연구자 마감 연장 ~4/6)", "2025-03-25", "학사"),
    (56, "[홍보] 2025 용인세브란스병원 디지털 헬스케어 해커톤", "2025-03-24", "행사"),
    (55, "[안내] 2025 산학협력 프로젝트 공고(전체 설명회 3/25)", "2025-03-18", "학사"),
    (54, "[홍보] ICT학점연계 프로젝트 인턴십 하반기 글로벌 실습생 모집 안내(~4/1까지 신청)", "2025-03-18", "행사"),
    (53, "[홍보] 2025년 SW중심대학 AI 창업 아이디어 경진대회 개최 안내", "2025-03-18", "학사"),
    (52, "[안내] 2025 한이음 드림업(구.ICT멘토링) 대학 사업설명회 (캡스톤디자인 수강 3,4학년 대상)", "2025-03-07", "학사"),
    (51, "[안내] 2025학년도 SW중심대학 SW특화 전공 홍보자료 및 Q&A", "2025-03-05", "학사"),
    (50, "[안내] 2025학년도 SW중심대학 SW융합 전공 홍보자료 및 Q&A", "2025-03-05", "학사"),
    (49, "[안내] 융합전공 및 특화전공 OT 참여 안내", "2025-02-27", "학사"),
    (48, "[안내] 채용 코딩테스트 PCCP 시험 안내", "2025-02-12", "학사"),
    (47, "[홍보] 국가공인 SW테스트전문가 CSTS자격시험 대비 공개 특강", "2025-02-10", "행사"),
    (46, "2025년도 SW마에스트로 과정 제16기 연수생 추천자 선정 발표", "2025-02-05", "학사"),
    (45, "[홍보] 2025 프로그래머스 코드챌린지 개최 (참가접수: ~2.5, 17시)", "2025-01-28", "행사"),
    (44, "[안내] 특화전공 및 융합전공 신청기간 연장 안내 (기한 확인)", "2025-01-24", "학사"),
    (43, "[안내] 2025-1학기 융합전공 핵심교과목 분반 개설시간표", "2025-01-22", "학사"),
    (42, "한신 AI 아트코딩 해커톤 대회(2/10~2/11, 1박2일간) 참가자 모집", "2025-01-16", "학사"),
    (41, "[안내] 특화전공 및 융합전공 신청 안내 (신청기간: 1/20~1/22)", "2025-01-16", "학사"),
    (40, "2025년도 SW마에스트로 과정 제16기 연수생 모집 공고", "2025-01-14", "학사"),
    (39, "[신입생] 2025학년도 입학전특별교육 SW 교과목 수강 혜택 안내", "2025-01-09", "학사"),
    (38, "[안내] SW특화트랙8개연합 코딩경진대회 시상자 공지 안내", "2024-12-23", "학사"),
    (37, "[안내] SW중심대학사업 노트북 대여 신청 안내", "2024-12-18", "학사"),
    (36, "[SW특화8개대학연합] 2024 코딩경진대회 (신청기한: 2024. 12. 13)", "2024-12-06", "학사"),
    (35, "[안내] 2024 한신 AI·SW 페스티벌 수상자 공지 및 상장 수령 안내", "2024-12-04", "학사"),
    (34, "[안내] SW특화전공 및 융합전공 사전 신청 안내(기간연장~17일까지)", "2024-12-02", "학사"),
    (33, "[안내] SW교재 개발 지원 안내", "2024-11-28", "학사"),
    (32, "[안내] 채용 코딩테스트 교육 플랫폼 제공 (AI·SW대학 재학생 대상)", "2024-11-27", "학사"),
    (31, "[SW중심대학협의회] 설문조사 협조 요청(기한: ~12/6까지)", "2024-11-25", "학사"),
    (30, "[안내] 2024 한신 AI·SW 페스티벌 행사에 초대합니다. (11/19)", "2024-11-18", "학사"),
    (29, "[홍보] 2024 SW인재페스티벌(2024.12.5~6, 세종대학교)", "2024-11-15", "행사"),
    (28, "[안내] 2024한신 AI·SW페스티벌 AI·SW창업아이디어 발표시간표 (총40팀)", "2024-11-15", "학사"),
    (27, "[안내] 2024한신AI·SW페스티벌 AI·SW개발_일반부 발표시간표 (총 25팀)", "2024-11-15", "학사"),
    (26, "[안내] 2024한신 AI·SW페스티벌 캡스톤디자인 발표시간표 (총65팀)", "2024-11-15", "학사"),
    (25, "[안내] LAB Tree 교육 운영 안내", "2024-11-14", "학사"),
    (24, "[홍보] 한양대학교 ERICA와 함께하는 2024 전국 SW 프로그래밍 경진대회", "2024-11-14", "행사"),
    (23, "[안내] SW특화전공 및 SW융합전공 소개", "2024-11-13", "학사"),
    (22, "2024년도 SW중심대학사업 2025CES참가자 합격자 안내", "2024-11-11", "학사"),
    (21, "2024년도 SW중심대학사업 2025CES참가자 1차서류평가 합격자 안내", "2024-11-05", "학사"),
    (20, "[안내] 산학협력 프로젝트 선정 팀 공지", "2024-11-04", "학사"),
    (19, "[SW중심대학] AI·SW 페스티벌 사전 교육 파일 공유", "2024-11-04", "학사"),
    (18, "2024년 청년창업특강 강연 일정 안내", "2024-11-01", "행사"),
    (17, "2024 한신 AI·SW 페스티벌 신청 사전 교육 안내", "2024-10-30", "학사"),
    (16, "[제출기한 연장] 2024 한신 AI·SW 페스티벌 신청 안내 (~11/12 신청마감)", "2024-10-25", "학사"),
    (15, "2024 ICT이노베이션스퀘어 해커톤 전국 대회(신청기간: ~11/8)", "2024-10-25", "행사"),
    (14, "2024년 SW중심대학사업 2025 CES 참관 프로그램 참가자 모집(신청마감)", "2024-10-24", "학사"),
    (13, "[홍보] 2024 대한민국 SW교육 페스티벌 행사 안내(11.1~11.3)", "2024-10-24", "행사"),
    (12, "[홍보] SW중심대학 산학협력프로젝트 신청(변경 2024. 10. 29 15시까지)", "2024-10-15", "학사"),
    (11, "[홍보] 2024년 SW중심대학 생성형 AI 활용 경험 공모전 개최 안내(~10/27까지)", "2024-10-14", "행사"),
    (10, "제22회 TOPCIT 정기평가 응시자 사전교육 안내 (응시자 필참)", "2024-10-04", "학사"),
    (9, "[안내] 2024년 제22회 TOPCIT 학습사이트 안내", "2024-09-25", "학사"),
    (8, "[홍보] (SW중심대학협의회) 온라인 콘텐츠 SW인재열전 인터뷰이 모집 안내", "2024-10-04", "행사"),
    (7, "2024년 캡스톤 디자인 및 AI 해커톤 대회(타대학 연합) 참가자 모집(~10/2까지 기한 연장)", "2024-09-20", "학사"),
    (6, "[SW교육센터] 클린코딩클리닉 참여자 모집 안내", "2024-09-04", "학사"),
    (5, "[홍보] 2024 SW우수작품 경진대회 (SW인재페스티벌 출품) 참가자 모집(~9/13까지)", "2024-09-04", "행사"),
    (4, "[홍보] 2024 SW중심대학 에세이 공모전(9/2~9/20)", "2024-09-02", "학사"),
    (3, "[홍보] 2024 제1회 국방 AI 아이디어톤(참가접수: 24. 8. 8.~10.7. 온라인)", "2024-09-02", "행사"),
    (2, "[안내] TOPCIT 제22회 정기평가 안내", "2024-09-02", "학사"),
    (1, "[공지] 한신대학교 SW중심대학사업 운영규정(2024. 8. 1.)", "2024-09-02", "학사"),
]

notices = []
for i, (num, title, date, category) in enumerate(NOTICES_RAW):
    notices.append({
        "notice_id": i + 1,
        "source_board": "SW중심대학사업단 공지사항",
        "title": title,
        "category": category,
        "posted_date": date,
        "notice_url": SOURCE_URL_NOTICES,
        "content": "",
    })

print(f"  Notices: {len(notices)}")


# ============================================================
# Step 11: Academic Events (40 events)
# ============================================================
print("Step 11: Academic events...")
academic_events = [
    {"event_id": 1, "academic_year": 2026, "semester": "2", "event_name": "2026-2학기 수강신청", "event_type": "COURSE_REGISTRATION", "start_date": "2026-08-04", "end_date": "2026-08-08", "is_mandatory": True, "description": "2026학년도 2학기 수강신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 2, "academic_year": 2026, "semester": "2", "event_name": "2026-2학기 수강신청 변경기간", "event_type": "COURSE_REGISTRATION", "start_date": "2026-08-25", "end_date": "2026-08-27", "is_mandatory": False, "description": "수강신청 정정기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 3, "academic_year": 2026, "semester": "2", "event_name": "2026-2학기 등록금 납부", "event_type": "TUITION_PAYMENT", "start_date": "2026-08-11", "end_date": "2026-08-13", "is_mandatory": True, "description": "2026학년도 2학기 등록금 납부 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 4, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 기말 강의평가", "event_type": "FINAL_COURSE_EVALUATION", "start_date": "2026-06-02", "end_date": "2026-06-12", "is_mandatory": True, "description": "기말 강의평가 기간. 미이수 시 성적 열람 불가", "source_url": SOURCE_URL_COURSE},
    {"event_id": 5, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 기말고사", "event_type": "EXAM", "start_date": "2026-06-16", "end_date": "2026-06-22", "is_mandatory": True, "description": "기말고사 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 6, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 성적조회", "event_type": "GRADE_INQUIRY", "start_date": "2026-06-30", "end_date": "2026-07-03", "is_mandatory": True, "description": "1학기 성적 조회 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 7, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 성적정정", "event_type": "GRADE_INQUIRY", "start_date": "2026-07-03", "end_date": "2026-07-04", "is_mandatory": False, "description": "성적 정정 신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 8, "academic_year": 2026, "semester": "", "event_name": "2026-2학기 융합/특화전공 신청", "event_type": "PRE_REGISTRATION", "start_date": "2026-07-14", "end_date": "2026-07-25", "is_mandatory": False, "description": "2026-2학기 융합/특화전공 신청 안내", "source_url": SOURCE_URL_CURRICULUM},
    {"event_id": 9, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 휴학신청", "event_type": "ADMINISTRATIVE", "start_date": "2026-03-02", "end_date": "2026-03-13", "is_mandatory": False, "description": "휴학신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 10, "academic_year": 2026, "semester": "2", "event_name": "2026-2학기 복학신청", "event_type": "ADMINISTRATIVE", "start_date": "2026-08-04", "end_date": "2026-08-08", "is_mandatory": False, "description": "복학신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 11, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 수강신청", "event_type": "COURSE_REGISTRATION", "start_date": "2026-02-09", "end_date": "2026-02-13", "is_mandatory": True, "description": "2026학년도 1학기 수강신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 12, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 수강신청 변경기간", "event_type": "COURSE_REGISTRATION", "start_date": "2026-03-02", "end_date": "2026-03-04", "is_mandatory": False, "description": "1학기 수강신청 정정기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 13, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 등록금 납부", "event_type": "TUITION_PAYMENT", "start_date": "2026-02-16", "end_date": "2026-02-18", "is_mandatory": True, "description": "2026학년도 1학기 등록금 납부 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 14, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 중간고사", "event_type": "EXAM", "start_date": "2026-04-14", "end_date": "2026-04-20", "is_mandatory": True, "description": "중간고사 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 15, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 중간 강의평가", "event_type": "FINAL_COURSE_EVALUATION", "start_date": "2026-04-07", "end_date": "2026-04-11", "is_mandatory": True, "description": "중간 강의평가 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 16, "academic_year": 2025, "semester": "2", "event_name": "2025-2학기 수강신청", "event_type": "COURSE_REGISTRATION", "start_date": "2025-08-04", "end_date": "2025-08-08", "is_mandatory": True, "description": "2025학년도 2학기 수강신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 17, "academic_year": 2025, "semester": "2", "event_name": "2025-2학기 수강신청 변경기간", "event_type": "COURSE_REGISTRATION", "start_date": "2025-08-25", "end_date": "2025-08-27", "is_mandatory": False, "description": "2학기 수강신청 정정기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 18, "academic_year": 2025, "semester": "2", "event_name": "2025-2학기 등록금 납부", "event_type": "TUITION_PAYMENT", "start_date": "2025-08-11", "end_date": "2025-08-13", "is_mandatory": True, "description": "2025학년도 2학기 등록금 납부 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 19, "academic_year": 2025, "semester": "1", "event_name": "2025-1학기 기말고사", "event_type": "EXAM", "start_date": "2025-06-16", "end_date": "2025-06-22", "is_mandatory": True, "description": "기말고사 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 20, "academic_year": 2025, "semester": "1", "event_name": "2025-1학기 기말 강의평가", "event_type": "FINAL_COURSE_EVALUATION", "start_date": "2025-06-02", "end_date": "2025-06-12", "is_mandatory": True, "description": "기말 강의평가 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 21, "academic_year": 2025, "semester": "1", "event_name": "2025-1학기 성적조회", "event_type": "GRADE_INQUIRY", "start_date": "2025-06-30", "end_date": "2025-07-03", "is_mandatory": True, "description": "1학기 성적 조회 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 22, "academic_year": 2025, "semester": "1", "event_name": "2025-1학기 성적정정", "event_type": "GRADE_INQUIRY", "start_date": "2025-07-03", "end_date": "2025-07-04", "is_mandatory": False, "description": "성적 정정 신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 23, "academic_year": 2025, "semester": "", "event_name": "2025-2학기 융합/특화전공 신청", "event_type": "PRE_REGISTRATION", "start_date": "2025-07-07", "end_date": "2025-07-18", "is_mandatory": False, "description": "2025-2학기 융합/특화전공 신청 안내", "source_url": SOURCE_URL_CURRICULUM},
    {"event_id": 24, "academic_year": 2025, "semester": "1", "event_name": "2025-1학기 수강신청", "event_type": "COURSE_REGISTRATION", "start_date": "2025-02-03", "end_date": "2025-02-07", "is_mandatory": True, "description": "2025학년도 1학기 수강신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 25, "academic_year": 2025, "semester": "1", "event_name": "2025-1학기 수강신청 변경기간", "event_type": "COURSE_REGISTRATION", "start_date": "2025-03-03", "end_date": "2025-03-05", "is_mandatory": False, "description": "1학기 수강신청 정정기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 26, "academic_year": 2025, "semester": "1", "event_name": "2025-1학기 등록금 납부", "event_type": "TUITION_PAYMENT", "start_date": "2025-02-10", "end_date": "2025-02-12", "is_mandatory": True, "description": "2025학년도 1학기 등록금 납부 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 27, "academic_year": 2025, "semester": "1", "event_name": "2025-1학기 중간고사", "event_type": "EXAM", "start_date": "2025-04-14", "end_date": "2025-04-20", "is_mandatory": True, "description": "중간고사 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 28, "academic_year": 2025, "semester": "2", "event_name": "2025-2학기 중간고사", "event_type": "EXAM", "start_date": "2025-10-20", "end_date": "2025-10-26", "is_mandatory": True, "description": "중간고사 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 29, "academic_year": 2025, "semester": "2", "event_name": "2025-2학기 기말고사", "event_type": "EXAM", "start_date": "2025-12-15", "end_date": "2025-12-21", "is_mandatory": True, "description": "기말고사 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 30, "academic_year": 2025, "semester": "2", "event_name": "2025-2학기 기말 강의평가", "event_type": "FINAL_COURSE_EVALUATION", "start_date": "2025-12-01", "end_date": "2025-12-11", "is_mandatory": True, "description": "기말 강의평가 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 31, "academic_year": 2025, "semester": "2", "event_name": "2025-2학기 성적조회", "event_type": "GRADE_INQUIRY", "start_date": "2025-12-29", "end_date": "2026-01-02", "is_mandatory": True, "description": "2학기 성적 조회 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 32, "academic_year": 2025, "semester": "2", "event_name": "2025-2학기 성적정정", "event_type": "GRADE_INQUIRY", "start_date": "2026-01-02", "end_date": "2026-01-03", "is_mandatory": False, "description": "성적 정정 신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 33, "academic_year": 2025, "semester": "2", "event_name": "2025-동계 계절학기 수강신청", "event_type": "COURSE_REGISTRATION", "start_date": "2025-12-22", "end_date": "2025-12-24", "is_mandatory": False, "description": "동계 계절학기 수강신청", "source_url": SOURCE_URL_COURSE},
    {"event_id": 34, "academic_year": 2026, "semester": "", "event_name": "2026-동계 계절학기 수강신청", "event_type": "COURSE_REGISTRATION", "start_date": "2026-12-21", "end_date": "2026-12-23", "is_mandatory": False, "description": "동계 계절학기 수강신청", "source_url": SOURCE_URL_COURSE},
    {"event_id": 35, "academic_year": 2026, "semester": "2", "event_name": "2026-2학기 기말 강의평가", "event_type": "FINAL_COURSE_EVALUATION", "start_date": "2026-12-01", "end_date": "2026-12-11", "is_mandatory": True, "description": "기말 강의평가 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 36, "academic_year": 2026, "semester": "2", "event_name": "2026-2학기 기말고사", "event_type": "EXAM", "start_date": "2026-12-14", "end_date": "2026-12-20", "is_mandatory": True, "description": "기말고사 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 37, "academic_year": 2026, "semester": "2", "event_name": "2026-2학기 성적조회", "event_type": "GRADE_INQUIRY", "start_date": "2026-12-29", "end_date": "2027-01-02", "is_mandatory": True, "description": "2학기 성적 조회 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 38, "academic_year": 2026, "semester": "1", "event_name": "2026-1학기 휴학신청", "event_type": "ADMINISTRATIVE", "start_date": "2026-02-23", "end_date": "2026-03-06", "is_mandatory": False, "description": "1학기 휴학신청 기간", "source_url": SOURCE_URL_COURSE},
    {"event_id": 39, "academic_year": 2026, "semester": "1", "event_name": "2026-하계 계절학기 수강신청", "event_type": "COURSE_REGISTRATION", "start_date": "2026-05-25", "end_date": "2026-05-27", "is_mandatory": False, "description": "하계 계절학기 수강신청", "source_url": SOURCE_URL_COURSE},
    {"event_id": 40, "academic_year": 2026, "semester": "2", "event_name": "2026-2학기 중간고사", "event_type": "EXAM", "start_date": "2026-10-19", "end_date": "2026-10-25", "is_mandatory": True, "description": "중간고사 기간", "source_url": SOURCE_URL_COURSE},
]


# ============================================================
# Step 12: New table data from PDFs
# ============================================================
print("Step 12: Building new table data...")

# 12a. Program Policies
policies = []
pol_rows = read_pdf_csv("intro_policies.csv")
for row in pol_rows:
    merged_prog_id = intro_program_ids.get(int(row["program_id"]), 0)
    policies.append({
        "policy_id": int(row["policy_id"]),
        "program_id": merged_prog_id,
        "policy_name": row["policy_name"],
        "policy_text": row["policy_text"],
        "effective_year": 2023,
    })
print(f"  Program policies: {len(policies)}")

# 12b. Program Scholarships
scholarships = []
sch_rows = read_pdf_csv("intro_scholarships.csv")
for row in sch_rows:
    merged_prog_id = intro_program_ids.get(int(row["program_id"]), 0)
    scholarships.append({
        "scholarship_id": int(row["scholarship_id"]),
        "program_id": merged_prog_id,
        "scholarship_name": row["scholarship_name"],
        "description": row["description"],
        "amount": row["amount"],
        "criteria": row["criteria"],
    })
print(f"  Program scholarships: {len(scholarships)}")

# 12c. Course Equivalencies
equivalencies = []
eq_rows = read_pdf_csv("convergence_equivalencies.csv")
for row in eq_rows:
    primary_id = pdf_id_to_merged["convergence"].get(row["primary_course_id"].strip(), 0)
    equiv_id = pdf_id_to_merged["convergence"].get(row["equivalent_course_id"].strip(), 0)
    prog_id = conv_program_ids.get(int(row["program_id"]), 0) if row.get("program_id") else None
    if primary_id and equiv_id:
        equivalencies.append({
            "equivalence_id": int(row["equivalence_id"]),
            "primary_course_id": primary_id,
            "equivalent_course_id": equiv_id,
            "program_id": prog_id,
            "note": row.get("note", ""),
        })
print(f"  Course equivalencies: {len(equivalencies)}")

# 12d. Course Relationships (from AISW 이수체계도)
relationships = []
rel_rows = read_pdf_csv("aisw_relationships.csv")
for row in rel_rows:
    from_id = course_code_to_id.get(row["from_course_id"].strip(), 0)
    to_id = course_code_to_id.get(row["to_course_id"].strip(), 0)
    if from_id and to_id:
        relationships.append({
            "relationship_id": int(row["relationship_id"]),
            "from_course_id": from_id,
            "to_course_id": to_id,
            "relationship_type": row.get("relationship_type", "PREREQUISITE"),
            "program_id": None,
            "note": row.get("note", ""),
        })
print(f"  Course relationships: {len(relationships)}")

# 12e. Course Keywords (from intro)
course_keywords = []
kw_rows = read_pdf_csv("intro_keywords.csv")
for row in kw_rows:
    course_keywords.append({
        "keyword_id": int(row["keyword_id"]),
        "offering_id": int(row["offering_id"]),
        "keyword": row["keyword"],
        "keyword_source": row["keyword_source"],
        "confidence_score": float(row["confidence_score"]) if row.get("confidence_score") else None,
        "keyword_category": row.get("keyword_category", ""),
        "weight": float(row["weight"]) if row.get("weight") else None,
        "source_text": row.get("source_text", ""),
    })
print(f"  Course keywords: {len(course_keywords)}")

# 12f. Empty tables (created via app)
users = []
students = []
student_programs = []
user_interests = []
student_course_history = []
course_recommendations = []
chat_sessions = []
chat_messages = []


# ============================================================
# CSV Writing
# ============================================================
print("\n" + "=" * 60)
print("Writing CSV files...")

def write_csv(filename, fieldnames, rows):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {filename}: {len(rows)} rows")

# 1. courses
course_rows = []
for i, code in enumerate(courses_order, 1):
    c = courses_map[code]
    course_rows.append({
        "course_id": i,
        "course_code": c["course_code"],
        "course_name": c["course_name"],
        "credit": c["credit"],
        "theory_hours": c["theory_hours"],
        "practice_hours": c["practice_hours"],
        "course_description": c["course_description"],
        "source_url": c["source_url"],
    })

write_csv("courses.csv", [
    "course_id", "course_code", "course_name", "credit",
    "theory_hours", "practice_hours", "course_description", "source_url"
], course_rows)

# 2. course_offerings
write_csv("course_offerings.csv", [
    "offering_id", "course_id", "academic_year", "semester",
    "section", "professor_name", "syllabus_url"
], offerings)

# 3. course_schedules
write_csv("course_schedules.csv", [
    "schedule_id", "offering_id", "day_of_week", "start_time",
    "end_time", "classroom"
], schedules)

# 4. programs
write_csv("programs.csv", [
    "program_id", "program_name", "program_type", "required_credits",
    "effective_from_year", "effective_to_year", "source_url"
], programs)

# 5. curriculum_courses (with program_id)
write_csv("curriculum_courses.csv", [
    "curriculum_course_id", "curriculum_year", "course_id",
    "recommended_grade", "semester", "completion_type",
    "is_required", "note", "program_id"
], curriculum_courses)

# 6. graduation_requirements
write_csv("graduation_requirements.csv", [
    "requirement_id", "admission_year", "program_id",
    "requirement_category", "required_credits", "requirement_text", "source_url"
], grad_requirements)

# 7. program_courses
write_csv("program_courses.csv", [
    "program_course_id", "program_id", "course_id",
    "effective_year", "recognition_credit", "is_required", "note"
], program_courses)

# 8. academic_events
write_csv("academic_events.csv", [
    "event_id", "academic_year", "semester", "event_name", "event_type",
    "start_date", "end_date", "is_mandatory", "description", "source_url"
], academic_events)

# 9. notices
write_csv("notices.csv", [
    "notice_id", "source_board", "title", "category",
    "posted_date", "notice_url", "content"
], notices)

# 10. course_keywords
write_csv("course_keywords.csv", [
    "keyword_id", "offering_id", "keyword", "keyword_source",
    "confidence_score", "keyword_category", "weight", "source_text"
], course_keywords)

# 11. program_policies
write_csv("program_policies.csv", [
    "policy_id", "program_id", "policy_name", "policy_text", "effective_year"
], policies)

# 12. program_scholarships
write_csv("program_scholarships.csv", [
    "scholarship_id", "program_id", "scholarship_name",
    "description", "amount", "criteria"
], scholarships)

# 13. course_equivalencies
write_csv("course_equivalencies.csv", [
    "equivalence_id", "primary_course_id", "equivalent_course_id",
    "program_id", "note"
], equivalencies)

# 14. course_relationships
write_csv("course_relationships.csv", [
    "relationship_id", "from_course_id", "to_course_id",
    "relationship_type", "program_id", "note"
], relationships)

# Empty tables
write_csv("users.csv", ["user_id", "login_id", "password_hash", "role"], users)
write_csv("students.csv", ["student_id", "user_id", "student_number", "admission_year", "current_grade"], students)
write_csv("student_programs.csv", ["student_program_id", "student_id", "program_id", "program_role", "selected_year", "completion_status", "created_at"], student_programs)
write_csv("user_interests.csv", ["user_interest_id", "user_id", "interest_type", "keyword", "created_at"], user_interests)
write_csv("student_course_history.csv", ["history_id", "student_id", "course_id", "academic_year", "semester", "earned_credit", "completion_status", "is_retake", "attempt_no", "original_history_id", "credit_counted"], student_course_history)
write_csv("course_recommendations.csv", ["recommendation_id", "student_id", "offering_id", "match_score", "reason", "generated_at"], course_recommendations)
write_csv("chat_sessions.csv", ["session_id", "user_id", "created_at", "updated_at"], chat_sessions)
write_csv("chat_messages.csv", ["message_id", "session_id", "sender_type", "message_text", "created_at"], chat_messages)


# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("=== GradManager CSV 생성 완료 ===")
print(f"출력 경로: {OUTPUT_DIR}")
print(f"과목 수 (courses): {len(course_rows)}")
print(f"개설강좌 (course_offerings): {len(offerings)}")
print(f"강의시간 (course_schedules): {len(schedules)}")
print(f"전공과정 (programs): {len(programs)}")
print(f"교육과정 (curriculum_courses): {len(curriculum_courses)}")
print(f"졸업요건 (graduation_requirements): {len(grad_requirements)}")
print(f"전공과목연결 (program_courses): {len(program_courses)}")
print(f"학사일정 (academic_events): {len(academic_events)}")
print(f"공지사항 (notices): {len(notices)}")
print(f"과목키워드 (course_keywords): {len(course_keywords)}")
print(f"전공정책 (program_policies): {len(policies)}")
print(f"전공장학금 (program_scholarships): {len(scholarships)}")
print(f"과목동일인정 (course_equivalencies): {len(equivalencies)}")
print(f"과목이수흐름 (course_relationships): {len(relationships)}")
print("=" * 60)
