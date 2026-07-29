# app/convert_db.py
import sqlite3
import os
import re

# --- [추가] 마이그레이션 중 사용자 데이터 유실 방지 가드 ---
backed_up_profiles = []
if os.path.exists("gradmanager.db"):
    try:
        temp_conn = sqlite3.connect("gradmanager.db")
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student_profiles';")
        if temp_cursor.fetchone():
            temp_cursor.execute("SELECT student_id, profile_json FROM student_profiles;")
            backed_up_profiles = temp_cursor.fetchall()
            print(f"[BACKUP GUARD] 기존 학생 프로필 {len(backed_up_profiles)}개 임시 백업 완료.")
        temp_conn.close()
    except Exception as e:
        print(f"[BACKUP GUARD WARNING] 백업 도중 오류 발생: {e}")

# 1. 기존 실패한 DB 삭제 대신 테이블 DROP 처리 (Windows 파일 락 우회)
if os.path.exists("gradmanager.db"):
    try:
        conn_drop = sqlite3.connect("gradmanager.db")
        cursor_drop = conn_drop.cursor()
        cursor_drop.execute("PRAGMA foreign_keys = OFF;")
        cursor_drop.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';")
        tables_to_drop = [row[0] for row in cursor_drop.fetchall()]
        for table in tables_to_drop:
            cursor_drop.execute(f'DROP TABLE IF EXISTS "{table}";')
        conn_drop.commit()
        conn_drop.close()
        print(f"[DROP GUARD] 기존 테이블 {len(tables_to_drop)}개 일괄 DROP 완료.")
    except Exception as e:
        print(f"[DROP GUARD WARNING] 테이블 DROP 중 오류 발생: {e}")

# 2. 파일 읽기
with open("gradmanager_dump.sql", "r", encoding="utf-8-sig") as f:
    sql_text = f.read()

# 3. 주석 제거 
sql_text = re.sub(r'--.*?\n', '\n', sql_text)
sql_text = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)

def split_sql_statements(sql_text):
    """문자열 리터럴 내의 세미콜론(;)을 무시하고 실제 SQL 구문 단위로 안전하게 분리합니다."""
    statements = []
    current = []
    in_quote = False
    quote_char = None
    escaped = False
    
    for char in sql_text:
        if escaped:
            current.append(char)
            escaped = False
            continue
            
        if char == '\\':
            current.append(char)
            escaped = True
            continue
            
        if char in ("'", '"'):
            if not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char:
                in_quote = False
                quote_char = None
            current.append(char)
        elif char == ';' and not in_quote:
            statements.append("".join(current))
            current = []
        else:
            current.append(char)
            
    if current:
        stmt = "".join(current).strip()
        if stmt:
            statements.append(stmt)
            
    return statements

# 4. 세미콜론 기준으로 문장 분리 (문자열 보호 적용)
raw_statements = split_sql_statements(sql_text)

cleaned_statements = []

for stmt in raw_statements:
    stmt_upper = stmt.strip().upper()
    if not stmt.strip():
        continue
    
    
    if any(stmt_upper.startswith(prefix) for prefix in ["SET", "LOCK", "UNLOCK", "DROP"]):
        continue

    
    if "CREATE TABLE" in stmt_upper:
        # 1) 백틱(`) -> 큰따옴표(")
        stmt = stmt.replace('`', '"')
        
        # 2) ENGINE=..., DEFAULT CHARSET=..., COMMENT=... 옵션 제거 (테이블 맨 끝 부분)
        stmt = re.sub(r'(?i)\)\s*ENGINE\s*=\s*[^;]+', ')', stmt)
        stmt = re.sub(r'(?i)\)\s*DEFAULT\s+CHARSET\s*=\s*[^;]+', ')', stmt)
        
        # 3) 컬럼 정의 내 COMMENT '...' 제거
        stmt = re.sub(r"(?i)COMMENT\s+'[^']*'", '', stmt)
        stmt = re.sub(r'(?i)COMMENT\s+"[^"]*"', '', stmt)
        
        # 4) AUTO_INCREMENT 컬럼을 SQLite INTEGER PRIMARY KEY AUTOINCREMENT로 변환
        stmt = re.sub(
            r'("?[a-zA-Z_]+_id"?)\s+INT\s+(?:NOT\s+NULL\s+)?AUTO_INCREMENT',
            r'\1 INTEGER PRIMARY KEY AUTOINCREMENT',
            stmt,
            flags=re.IGNORECASE
        )
        # 만약 남아있을 수 있는 AUTO_INCREMENT 구문 제거
        stmt = re.sub(r'(?i)AUTO_INCREMENT\s*=\s*\d+', '', stmt)
        stmt = re.sub(r'(?i)AUTO_INCREMENT', '', stmt)

        # 5) KEY / INDEX / CONSTRAINT 행 완전히 제거
        lines = stmt.split('\n')
        new_lines = []
        for line in lines:
            line_upper = line.strip().upper()
            if any(line_upper.startswith(k) for k in ["KEY ", "INDEX ", "UNIQUE KEY", "CONSTRAINT ", "PRIMARY KEY"]):
                # PRIMARY KEY가 테이블 맨 밑 독립 행으로 있으면 스킵
                if line_upper.startswith("PRIMARY KEY"):
                    continue
                continue
            new_lines.append(line)
        
        stmt = '\n'.join(new_lines)
        
        # 6) 구문 정리 중 남은 콤마(,) 오류 방지 (마지막 콤마 제거)
        stmt = re.sub(r',\s*\)', '\n)', stmt)

    # --- [INSERT INTO 정리] ---
    elif "INSERT INTO" in stmt_upper:
        stmt = stmt.replace('`', '"')

    cleaned_statements.append(stmt)

# 5. SQLite DB 연결 및 실행
conn = sqlite3.connect("gradmanager.db")
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = OFF;")

success_cnt = 0
fail_cnt = 0

for stmt in cleaned_statements:
    stmt_str = stmt.strip()
    if not stmt_str:
        continue
    try:
        cursor.execute(stmt_str)
        success_cnt += 1
    except Exception as e:
        fail_cnt += 1

conn.commit()

# 생성된 테이블 확인
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print(f"\n==================================================")
print(f" 변환 완료! (성공: {success_cnt}개 / 실패: {fail_cnt}개)")
print(f" 생성된 테이블 목록 ({len(tables)}개):")
for t in tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM "{t[0]}"')
        count = cursor.fetchone()[0]
        print(f"  - {t[0]}: {count}개 데이터 입력됨")
    except Exception:
        pass
# --- [추가] 백업해 두었던 사용자 프로필 데이터 복원 ---
if backed_up_profiles:
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            student_id TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL
        );
        """)
        for sid, p_json in backed_up_profiles:
            cursor.execute(
                "INSERT OR REPLACE INTO student_profiles (student_id, profile_json) VALUES (?, ?);",
                (sid, p_json)
            )
        conn.commit()
        print(f"[RESTORE GUARD] 백업되었던 {len(backed_up_profiles)}개의 학생 프로필을 성공적으로 복원했습니다!")
    except Exception as e:
        print(f"[RESTORE GUARD ERROR] 프로필 복원 실패: {e}")

    # --- [추가] student_course_history 테이블 컬럼 보정 플로우 ---
    try:
        cursor.execute("PRAGMA table_info(student_course_history);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "semester_taken" not in columns:
            cursor.execute("ALTER TABLE student_course_history ADD COLUMN semester_taken VARCHAR(20) DEFAULT NULL;")
            print("[PATCH GUARD] student_course_history 테이블에 'semester_taken' 컬럼 추가 완료.")
        if "grade" not in columns:
            cursor.execute("ALTER TABLE student_course_history ADD COLUMN grade VARCHAR(10) DEFAULT NULL;")
            print("[PATCH GUARD] student_course_history 테이블에 'grade' 컬럼 추가 완료.")
            
        conn.commit()
    except Exception as e:
        print(f"[PATCH GUARD ERROR] 컬럼 추가 실패: {e}")

print(f"==================================================")
conn.close()