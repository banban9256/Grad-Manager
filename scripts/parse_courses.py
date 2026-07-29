"""
2026-1학기 개설강의 JSON → courses / course_offerings / course_schedules CSV
sugang.hs.ac.kr 에서 수집한 전체 개설강의 데이터 파싱
"""
import json, csv, os, re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(BASE_DIR, "..", "data", "input_data", "all_courses_26_1.json")
OUT = os.path.join(BASE_DIR, "..", "data", "output")

SOURCE_URL = "https://sugang.hs.ac.kr/course/subject/list"

DAY_MAP = {"월": "월", "화": "화", "수": "수", "목": "목", "금": "금", "토": "토"}

def parse_credit(hakjum_str):
    """학점 문자열 → float, '(0)' 등은 0.0"""
    s = hakjum_str.strip().replace("(", "").replace(")", "")
    try:
        return float(s)
    except:
        return 0.0

def parse_time(gyosi_str):
    """
    GYOSI 예: '금(13:00~14:40)', '화(11:00~12:40)', '월(10:00~11:40)/수(10:00~11:40)', '월(09:30~10:45)수(11:00~12:15)', '-'
    → [(day, start, end), ...]
    """
    if not gyosi_str or gyosi_str.strip() == "-":
        return []
    results = []
    # 글로벌 매칭으로 요일(시작~종료) 패턴을 수에 관계없이 모두 추출 (수요일 [수] 누락 해결)
    pattern = r'([월화수목금토일])(?:요일)?\((\d{1,2}:\d{2})~(\d{1,2}:\d{2})\)'
    matches = re.findall(pattern, gyosi_str)
    for day_char, start, end in matches:
        day = DAY_MAP.get(day_char, day_char)
        results.append((day, start, end))
    return results

def parse_theory_practice(gyosi_str, credit):
    """시간 정보에서 이론/실습 시간 추정 (간단히: 실습 없으면 전부 이론)"""
    # 학점수에 비례 (실습 과목 구분이 없으므로 전부 이론으로)
    if credit <= 0:
        return 0.0, 0.0
    return credit, 0.0

def main():
    with open(INPUT, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    subjects = data["subjectList"]
    print(f"JSON에서 읽은 전체 수업 수: {len(subjects)}")

    # ── courses.csv (고유 과목) ──
    courses_map = {}  # code → {course_code, course_name, credit, ...}
    for s in subjects:
        code = s["GAESUL_GWAMOK"]
        if code in courses_map:
            continue
        credit = parse_credit(s.get("HAKJUM", "0"))
        courses_map[code] = {
            "course_code": code,
            "course_name": s.get("GWAMOK_KORNAME", ""),
            "credit": credit,
            "theory_hours": credit,
            "practice_hours": 0.0,
            "course_description": s.get("GAESUL_BIGO", ""),
            "source_url": SOURCE_URL,
        }

    print(f"고유 과목 수: {len(courses_map)}")

    # 이수구분별 통계
    isu_counts = {}
    for s in subjects:
        isu = s.get("ISU_NM", "미상")
        isu_counts[isu] = isu_counts.get(isu, 0) + 1
    print("\n이수구분별 수업 수:")
    for k, v in sorted(isu_counts.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    # ── course_offerings.csv ──
    offerings = []
    offering_id = 1
    # offering_key → offering_id 매핑
    offering_key_map = {}

    for s in subjects:
        code = s["GAESUL_GWAMOK"]
        section = s.get("GAESUL_BUNBAN", "A")
        prof = s.get("GYOSU_NAME", "")
        offering_key = (code, 2026, "1학기", section)

        if offering_key in offering_key_map:
            oid = offering_key_map[offering_key]
        else:
            offerings.append({
                "offering_id": offering_id,
                "course_id_placeholder": code,
                "academic_year": 2026,
                "semester": "1학기",
                "section": section,
                "professor_name": prof,
                "syllabus_url": "",
            })
            offering_key_map[offering_key] = offering_id
            oid = offering_id
            offering_id += 1

    print(f"개설강좌 수: {len(offerings)}")

    # ── course_schedules.csv ──
    schedules = []
    schedule_id = 1

    for s in subjects:
        code = s["GAESUL_GWAMOK"]
        section = s.get("GAESUL_BUNBAN", "A")
        offering_key = (code, 2026, "1학기", section)
        oid = offering_key_map.get(offering_key)
        if not oid:
            continue

        gyosi = s.get("GYOSI", "-")
        classroom = s.get("HOSU", "")
        times = parse_time(gyosi)

        for day, start, end in times:
            schedules.append({
                "schedule_id": schedule_id,
                "offering_id": oid,
                "day_of_week": day,
                "start_time": start,
                "end_time": end,
                "classroom": classroom,
            })
            schedule_id += 1

    print(f"강의시간 수: {len(schedules)}")

    # ── CSV 쓰기 ──
    def write_csv(filename, fieldnames, rows):
        path = os.path.join(OUT, filename)
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"  {filename}: {len(rows)} rows")

    # courses: code → id 매핑
    course_code_to_id = {}
    course_rows = []
    for i, (code, c) in enumerate(courses_map.items(), 1):
        course_code_to_id[code] = i
        course_rows.append({
            "course_id": i,
            **c,
        })

    write_csv("courses.csv", [
        "course_id", "course_code", "course_name", "credit",
        "theory_hours", "practice_hours", "course_description", "source_url"
    ], course_rows)

    # offerings: placeholder → actual course_id
    offering_rows = []
    for o in offerings:
        cid = course_code_to_id.get(o["course_id_placeholder"], 0)
        offering_rows.append({
            "offering_id": o["offering_id"],
            "course_id": cid,
            "academic_year": o["academic_year"],
            "semester": o["semester"],
            "section": o["section"],
            "professor_name": o["professor_name"],
            "syllabus_url": o["syllabus_url"],
        })

    write_csv("course_offerings.csv", [
        "offering_id", "course_id", "academic_year", "semester",
        "section", "professor_name", "syllabus_url"
    ], offering_rows)

    write_csv("course_schedules.csv", [
        "schedule_id", "offering_id", "day_of_week",
        "start_time", "end_time", "classroom"
    ], schedules)

    # ── 요약 ──
    print(f"\n{'='*50}")
    print(f"2026-1학기 개설강의 파싱 완료")
    print(f"  고유 과목: {len(courses_map)}")
    print(f"  개설강좌: {len(offerings)}")
    print(f"  강의시간: {len(schedules)}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
