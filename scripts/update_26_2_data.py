# -*- coding: utf-8 -*-
"""
update_26_2_data.py
26-2학기 개설 강의 데이터를 '26전체강의목록.csv' 파일로 교체하는 마이그레이션 스크립트.
"""
import csv
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data", "output")
NEW_LIST_PATH = os.path.join(BASE_DIR, "..", "data", "input_data", "26전체강의목록.csv")

_CHAPEL_CODES = {"KY100", "KY101", "KY201", "KY304", "KY509"}

def run_command(command_list, cwd):
    print(f"Running command: {' '.join(command_list)} in {cwd}")
    result = subprocess.run(command_list, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing command: {result.stderr}")
        sys.exit(1)
    else:
        print(f"Command succeeded: {result.stdout}")

def copy_csv_files_to_output():
    import shutil
    dest_dir = os.path.join(BASE_DIR, "..", "data", "output")
    os.makedirs(dest_dir, exist_ok=True)
    print(f"Copying CSV files from {DATA_DIR} to {dest_dir}...")
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".csv"):
            src = os.path.join(DATA_DIR, fname)
            dst = os.path.join(dest_dir, fname)
            if os.path.abspath(src) == os.path.abspath(dst):
                continue
            shutil.copy(src, dst)
    print("CSV files copied successfully.")

def main():
    print("=" * 60)
    print("Starting 26-2 course data migration...")
    print("=" * 60)

def normalize_isu(isu_str):
    if not isu_str:
        return "일반선택"
    isu_str = isu_str.strip()
    mapping = {
        "교필": "교양필수",
        "일선": "일반선택",
        "전선": "전공선택",
        "교선": "교양선택",
        "계공": "계열공통",
        "전필": "전공필수"
    }
    return mapping.get(isu_str, "일반선택")

def parse_credit(credit_str):
    import re
    if not credit_str:
        return 3.0
    num_match = re.search(r'(\d+(?:\.\d+)?)', credit_str)
    if num_match:
        try:
            return float(num_match.group(1))
        except ValueError:
            pass
    return 3.0

def parse_schedules(schedule_str, classroom_str):
    import re
    # 강의시간 문자열에서 요일(시작~종료) 패턴 찾기 (예: 화(16:00~17:15)화(17:30~18:45) 등)
    pattern = r'([월화수목금토일])\((\d{2}:\d{2})~(\d{2}:\d{2})\)'
    matches = re.findall(pattern, schedule_str)
    
    # 강의실 문자열에서 맨 앞 숫자/영어 문자만 떼기 (예: 3408() -> 3408)
    classroom = "미정"
    if classroom_str:
        cls_match = re.match(r'^([^\(]+)', classroom_str.strip())
        if cls_match:
            classroom = cls_match.group(1).strip()
            if not classroom:
                classroom = "미정"
                
    results = []
    for day, start, end in matches:
        results.append({
            "day_of_week": day,
            "start_time": start,
            "end_time": end,
            "classroom": classroom
        })
    return results

def main():
    print("=" * 60)
    print("Starting 26-2 course data migration...")
    print("=" * 60)

    # data/output의 파일들을 output 디렉토리로 동기화
    copy_csv_files_to_output()

    # 1. 기존 CSV 데이터 로딩
    courses_path = os.path.join(DATA_DIR, "courses.csv")
    offerings_path = os.path.join(DATA_DIR, "course_offerings.csv")
    schedules_path = os.path.join(DATA_DIR, "course_schedules.csv")

    with open(courses_path, "r", encoding="utf-8-sig") as f:
        courses = list(csv.DictReader(f))
    with open(offerings_path, "r", encoding="utf-8-sig") as f:
        offerings = list(csv.DictReader(f))
    with open(schedules_path, "r", encoding="utf-8-sig") as f:
        schedules = list(csv.DictReader(f))

    print(f"Initial courses count: {len(courses)}")
    print(f"Initial offerings count: {len(offerings)}")
    print(f"Initial schedules count: {len(schedules)}")

    # 2. 기존 2026학년도 2학기 데이터 식별 및 제거
    del_offering_ids = set()
    kept_offerings = []
    for o in offerings:
        if o["academic_year"] == "2026" and o["semester"] == "2학기":
            del_offering_ids.add(int(o["offering_id"]))
        else:
            kept_offerings.append(o)

    kept_schedules = []
    for s in schedules:
        if int(s["offering_id"]) not in del_offering_ids:
            kept_schedules.append(s)

    print(f"Removed {len(offerings) - len(kept_offerings)} offerings for 2026-2학기.")
    print(f"Removed {len(schedules) - len(kept_schedules)} schedules for 2026-2학기.")

    offerings = kept_offerings
    schedules = kept_schedules

    # 3. 26전체강의목록.csv 읽기 (헤더: 학과코드,이수구분,학수번호,교과목명,학점,교수명,강의시간,강의실,수강인원,정원)
    new_courses_to_add = []
    with open(NEW_LIST_PATH, "r", encoding="utf-8-sig") as f:
        new_list_reader = csv.DictReader(f)
        for row in new_list_reader:
            new_courses_to_add.append(row)

    print(f"Loaded {len(new_courses_to_add)} rows from '26전체강의목록.csv'.")

    # 4. courses.csv 맵핑 & 신규 과목 추가
    existing_courses_map = {c["course_code"].lstrip("*"): c for c in courses}
    max_course_id = max(int(c["course_id"]) for c in courses) if courses else 0

    # courses에 새로운 과목 추가
    for row in new_courses_to_add:
        # 학수번호(예: KYC55-A2)에서 학수코드와 분반 분리
        code_parts = row["학수번호"].split('-')
        code_raw = code_parts[0]
        code_clean = code_raw.lstrip("*")
        name = row["교과목명"]
        credit_val = parse_credit(row["학점"])

        if code_clean not in existing_courses_map:
            max_course_id += 1
            new_course_entry = {
                "course_id": max_course_id,
                "course_code": code_raw,
                "course_name": name,
                "credit": credit_val,
                "theory_hours": credit_val,
                "practice_hours": 0.0,
                "course_description": f"# [이수구분: {normalize_isu(row['이수구분'])}]",
                "source_url": "https://sugang.hs.ac.kr/course/subject/list",
            }
            courses.append(new_course_entry)
            existing_courses_map[code_clean] = new_course_entry
            print(f"Added new course: {code_raw} ({name}) - {credit_val} credits")

    # 5. course_offerings.csv 및 course_schedules.csv 에 새 데이터 추가
    max_offering_id = max(int(o["offering_id"]) for o in offerings) if offerings else 0
    max_schedule_id = max(int(s["schedule_id"]) for s in schedules) if schedules else 0

    for row in new_courses_to_add:
        code_parts = row["학수번호"].split('-')
        code_raw = code_parts[0]
        code_clean = code_raw.lstrip("*")
        section = code_parts[1] if len(code_parts) > 1 else "A"
        
        course_info = existing_courses_map[code_clean]
        course_id = course_info["course_id"]

        # 1) offering 추가
        max_offering_id += 1
        prof = row["교수명"].strip() if row["교수명"] else "미정"
        new_offering_entry = {
            "offering_id": max_offering_id,
            "course_id": course_id,
            "academic_year": 2026,
            "semester": "2학기",
            "section": section,
            "professor_name": prof if prof else "미정",
            "syllabus_url": "",
        }
        offerings.append(new_offering_entry)

        # 2) schedule 추가 (시간표 파싱 및 적재)
        parsed_times = parse_schedules(row["강의시간"], row["강의실"])
        for sched_item in parsed_times:
            max_schedule_id += 1
            new_schedule_entry = {
                "schedule_id": max_schedule_id,
                "offering_id": max_offering_id,
                "day_of_week": sched_item["day_of_week"],
                "start_time": sched_item["start_time"],
                "end_time": sched_item["end_time"],
                "classroom": sched_item["classroom"],
            }
            schedules.append(new_schedule_entry)

    # 6. CSV 저장
    courses_headers = ["course_id", "course_code", "course_name", "credit", "theory_hours", "practice_hours", "course_description", "source_url"]
    offerings_headers = ["offering_id", "course_id", "academic_year", "semester", "section", "professor_name", "syllabus_url"]
    schedules_headers = ["schedule_id", "offering_id", "day_of_week", "start_time", "end_time", "classroom"]

    output_dir_dest = os.path.join(BASE_DIR, "..", "data", "output")
    os.makedirs(output_dir_dest, exist_ok=True)

    for path_dir in [DATA_DIR, output_dir_dest]:
        c_path = os.path.join(path_dir, "courses.csv")
        o_path = os.path.join(path_dir, "course_offerings.csv")
        s_path = os.path.join(path_dir, "course_schedules.csv")

        with open(c_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=courses_headers)
            writer.writeheader()
            writer.writerows(courses)

        with open(o_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=offerings_headers)
            writer.writeheader()
            writer.writerows(offerings)

        with open(s_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=schedules_headers)
            writer.writeheader()
            writer.writerows(schedules)

    print("-" * 60)
    print(f"Updated courses count: {len(courses)}")
    print(f"Updated offerings count: {len(offerings)}")
    print(f"Updated schedules count: {len(schedules)}")
    print("-" * 60)

    # 7. dump sql 갱신
    python_exe = os.path.join(BASE_DIR, "..", ".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python"
    
    # generate_dump.py 및 app/convert_db.py 차례로 실행
    run_command([python_exe, "generate_dump.py"], BASE_DIR)
    backend_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "backend"))
    run_command([python_exe, "app/convert_db.py"], backend_dir)

    print("=" * 60)
    print("Migration finished successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
