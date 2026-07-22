# app/convert_db.py
import sqlite3
import os
import re

# 1. 기존 실패한 DB 삭제
if os.path.exists("gradmanager.db"):
    os.remove("gradmanager.db")

# 2. 파일 읽기
with open("data/gradmanager_dump.sql", "r", encoding="utf-8-sig") as f:
    sql_text = f.read()

# 3. 주석 제거 (-- 및 /* */)
sql_text = re.sub(r'--.*?\n', '\n', sql_text)
sql_text = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)

# 4. 세미콜론 기준으로 문장 분리
raw_statements = sql_text.split(';')

cleaned_statements = []

for stmt in raw_statements:
    stmt_upper = stmt.strip().upper()
    if not stmt.strip():
        continue
    
    # SET, LOCK, UNLOCK, DROP 등 불필요 제어문은 통째로 스킵
    if any(stmt_upper.startswith(prefix) for prefix in ["SET", "LOCK", "UNLOCK", "DROP"]):
        continue

    # --- [CREATE TABLE 정리] ---
    if "CREATE TABLE" in stmt_upper:
        # 1) 백틱(`) -> 큰따옴표(")
        stmt = stmt.replace('`', '"')
        
        # 2) ENGINE=..., DEFAULT CHARSET=..., COMMENT=... 옵션 제거 (테이블 맨 끝 부분)
        stmt = re.sub(r'(?i)\)\s*ENGINE\s*=\s*[^;]+', ')', stmt)
        stmt = re.sub(r'(?i)\)\s*DEFAULT\s+CHARSET\s*=\s*[^;]+', ')', stmt)
        
        # 3) 컬럼 정의 내 COMMENT '...' 제거
        stmt = re.sub(r"(?i)COMMENT\s+'[^']*'", '', stmt)
        stmt = re.sub(r'(?i)COMMENT\s+"[^"]*"', '', stmt)
        
        # 4) AUTO_INCREMENT 제거
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
print(f"🎉 변환 완료! (성공: {success_cnt}개 / 실패: {fail_cnt}개)")
print(f"📌 생성된 테이블 목록 ({len(tables)}개):")
for t in tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM "{t[0]}"')
        count = cursor.fetchone()[0]
        print(f"  - {t[0]}: {count}개 데이터 입력됨")
    except Exception:
        pass
print(f"==================================================")

conn.close()