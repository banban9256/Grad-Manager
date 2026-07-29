"""가상 학생 데이터 및 SQLite DB 영구 저장(Persistence) 레이어"""

import sqlite3
import json
import os

# DB 파일 절대경로 계산 (프로젝트 루트의 gradmanager.db)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DB_PATH = os.path.join(BASE_DIR, "gradmanager.db")

# 인메모리 기본 가상 데이터 (최초 1회 DB 적재용)
DEFAULT_STUDENTS = {
    "20210001": {
        "name": "김정보",
        "student_id": "20210001",
        "department": "AISW",
        "major_tracks": ["AISW 본전공"],
        "enrolled_year": 2021,
        "current_semester": 7,
        "completed_credits": 90,
        "required_credits": 130,
        "completed_courses": [
            "KY677", "KY921", "KYC56", "KYC55", "KY217",
            "KY313", "KYC54", "KYC69", "KY410",
            "SH304", "SH317", "SH318", "SH312", "SH355",
            "SH402", "SH403", "SH354", "DS301", "FLOW-065",
            "KY696", "KYC88", "KYC89", "KY245", "KY755",
            "KY961", "KYA81", "KYC45", "KY304", "KY201"
        ],
        "in_progress_courses": ["SH328", "SH322"],
        "gpa": 3.8,
        "mileage": 45,
        "keyword_preferences": ["장학금", "AI", "인턴"],
        "preferred_days": ["월", "화", "수", "목", "금"],
        "preferred_times": ["09:00-12:00", "14:00-17:00"],
        "avoid_times": ["18:00-21:00"],
        "custom_schedule_blocks": []
    },
    "20220001": {
        "name": "박졸업",
        "student_id": "20220001",
        "department": "AISW",
        "major_tracks": ["AISW 본전공", "인지 감성 특화"],
        "enrolled_year": 2022,
        "current_semester": 5,
        "completed_credits": 70,
        "required_credits": 130,
        "completed_courses": [
            "KY677", "KY921", "KYC56", "KYC55", "KY217",
            "KY313", "KYC54", "KYC69", "KY410",
            "SH304", "SH317", "SH318", "SH312", "SH355",
            "SH402", "SH354", "DS301", "KY696", "KYC88",
            "KYC89", "KY245", "KY755", "KY304", "KY201"
        ],
        "in_progress_courses": ["SH322", "SH328"],
        "gpa": 3.5,
        "mileage": 30,
        "keyword_preferences": ["공모전", "특화전공", "융합"],
        "preferred_days": ["월", "화", "수", "목", "금"],
        "preferred_times": ["10:00-18:00"],
        "avoid_times": [],
        "custom_schedule_blocks": []
    },
}

def _get_db_conn():
    """SQLite DB 커넥션 생성"""
    return sqlite3.connect(DB_PATH)

def init_db():
    """프로필 영구 보존용 student_profiles 테이블 생성 및 기본값 초기화"""
    conn = _get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_profiles (
        student_id TEXT PRIMARY KEY,
        profile_json TEXT NOT NULL
    );
    """)
    conn.commit()
    
    # 데이터가 비어 있는 경우 기본 데모 학생 복원 인서트
    cursor.execute("SELECT COUNT(*) FROM student_profiles;")
    count = cursor.fetchone()[0]
    if count == 0:
        for sid, sdata in DEFAULT_STUDENTS.items():
            cursor.execute(
                "INSERT INTO student_profiles (student_id, profile_json) VALUES (?, ?);",
                (sid, json.dumps(sdata, ensure_ascii=False))
            )
        conn.commit()
    else:
        # 기존 프로필 데이터 유지 (자동 리셋 비활성화)
        pass
    conn.close()

# 백엔드 모듈 로딩 시 데이터베이스 및 테이블 자동 초기화 트리거
init_db()

# 기존 로직과의 호환성을 위한 STUDENTS 인메모리 프록시 딕셔너리 클래스 정의
class SQLiteStudentsProxy(dict):
    """
    기존 STUDENTS[student_id] = s 및 get() 동작을 
    SQLite DB와 실시간 투명 연동하는 Proxy 객체
    """
    def __getitem__(self, key):
        student = get_student(key)
        if student is None:
            raise KeyError(key)
        return student

    def __setitem__(self, key, value):
        save_student(key, value)

    def __contains__(self, key):
        return get_student(key) is not None

    def get(self, key, default=None):
        student = get_student(key)
        return student if student is not None else default

    def items(self):
        return get_all_students().items()

    def values(self):
        return get_all_students().values()

    def keys(self):
        return get_all_students().keys()

# 글로벌 가상 변수 STUDENTS를 프록시 객체로 대체하여 기존 API 코드 파손 방지
STUDENTS = SQLiteStudentsProxy()

def get_student(student_id: str) -> dict | None:
    """학번으로 SQLite DB에서 학생 정보 조회"""
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT profile_json FROM student_profiles WHERE student_id = ?;", (str(student_id),))
        row = cursor.fetchone()
        
        if row:
            student = json.loads(row[0])
            
            # 실시간으로 student_course_history 테이블을 조회하여 completed_courses와 completed_credits 동기화
            try:
                # 1. students 테이블에서 입학연도(admission_year)와 학년(current_grade) 조회하여 병합
                cursor.execute("""
                    SELECT admission_year, current_grade 
                    FROM students 
                    WHERE student_number = ?;
                """, (str(student_id),))
                student_row = cursor.fetchone()
                
                if student_row:
                    admission_year, current_grade = student_row
                    student["enrolled_year"] = int(admission_year)
                    student["admission_year"] = int(admission_year)
                    student["current_grade"] = int(current_grade)
                else:
                    # DB에 없을 경우 학번(student_id)에서 앞 4자리를 추출하여 입학연도로 활용
                    try:
                        extracted_year = int(str(student_id)[:4])
                        student["enrolled_year"] = extracted_year
                        student["admission_year"] = extracted_year
                    except:
                        pass
                
                # 학번 문자열 파싱 (예: 20240001 -> '24학번')
                enrolled_yr = student.get("enrolled_year")
                if enrolled_yr:
                    student["class_of"] = f"{str(enrolled_yr)[-2:]}학번"
                else:
                    student["class_of"] = "학번 미정"

                # current_semester를 기반으로 학년 계산 보정
                curr_sem = student.get("current_semester", 1)
                try:
                    curr_sem_int = int(curr_sem)
                    grade_num = (curr_sem_int + 1) // 2
                    grade_num = min(4, max(1, grade_num))
                    student["current_grade"] = grade_num
                    student["grade"] = f"{grade_num}학년"
                except:
                    student["grade"] = "학년 미정"

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student_course_history';")
                if cursor.fetchone():
                    # F학점(낙제)을 제외하고 통과한 과목들만 기수강 과목 코드로 수집
                    cursor.execute("""
                        SELECT c.course_code, h.earned_credit, h.grade, c.course_name
                        FROM student_course_history h
                        JOIN courses c ON h.course_id = c.course_id
                        WHERE h.student_id = ?
                    """, (int(student_id),))
                    
                    histories = cursor.fetchall()
                    completed_codes = []
                    completed_course_names = []
                    completed_courses_detail = []
                    total_credits = 0.0
                    for code, credit, grade, name in histories:
                        c_code = code.lstrip("*")
                        if grade and grade.upper() != "F":
                            if c_code not in completed_codes:
                                completed_codes.append(c_code)
                            if name:
                                completed_course_names.append(name)
                                completed_courses_detail.append({
                                    "code": c_code,
                                    "name": name,
                                    "credits": float(credit) if credit else 0.0,
                                    "grade": grade
                                })
                            total_credits += float(credit) if credit else 0.0
                    
                    student["completed_courses"] = completed_codes
                    student["completed_course_names"] = completed_course_names
                    student["completed_courses_detail"] = completed_courses_detail
                    student["completed_credits"] = int(total_credits) if total_credits == int(total_credits) else total_credits
            except Exception as inner_e:
                print(f"[SQLITE ERROR] failed to sync completed courses: {inner_e}")
                
            conn.close()
            return student
            
        conn.close()
    except Exception as e:
        print(f"[SQLITE ERROR] get_student failed: {e}")
    
    # DB 조회 실패 혹은 없을 시 기본 데모 데이터 수집
    return DEFAULT_STUDENTS.get(str(student_id))

def save_student(student_id: str, student_dict: dict) -> bool:
    """학생 정보를 SQLite DB에 영구 업데이트 및 덮어쓰기"""
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO student_profiles (student_id, profile_json) VALUES (?, ?);",
            (str(student_id), json.dumps(student_dict, ensure_ascii=False))
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[SQLITE ERROR] save_student failed: {e}")
        return False

def get_all_students() -> dict:
    """전체 학생 목록 반환 (DB로부터 동적 리로드)"""
    students_map = {}
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, profile_json FROM student_profiles;")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            students_map[row[0]] = json.loads(row[1])
    except Exception as e:
        print(f"[SQLITE ERROR] get_all_students failed: {e}")
        
    if not students_map:
        return DEFAULT_STUDENTS
    return students_map
