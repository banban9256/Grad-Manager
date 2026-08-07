import sqlite3

def main():
    conn = sqlite3.connect('backend/gradmanager.db')
    cursor = conn.cursor()
    
    # 2026학년도 2학기 offerings 확인
    cursor.execute("SELECT COUNT(*) FROM course_offerings WHERE academic_year=2026 AND semester='2학기'")
    count = cursor.fetchone()[0]
    print(f"2026-2학기 offerings 개수: {count}")
    
    if count > 0:
        # 교수명이 '미정'이거나 비어있는 경우 확인
        cursor.execute("SELECT COUNT(*) FROM course_offerings WHERE academic_year=2026 AND semester='2학기' AND (professor_name IS NULL OR professor_name = '미정' OR professor_name = '')")
        no_prof_count = cursor.fetchone()[0]
        print(f"2026-2학기 교수명 미정/비어있는 offerings 개수: {no_prof_count}")
        
        # 스케줄 정보가 없는 offerings 확인
        cursor.execute("""
            SELECT COUNT(*) FROM course_offerings o 
            LEFT JOIN course_schedules s ON o.offering_id = s.offering_id 
            WHERE o.academic_year=2026 AND o.semester='2학기' AND s.schedule_id IS NULL
        """)
        no_sched_count = cursor.fetchone()[0]
        print(f"2026-2학기 시간표 정보가 없는 offerings 개수: {no_sched_count}")
        
        # 샘플 출력
        cursor.execute("""
            SELECT o.offering_id, c.course_code, c.course_name, o.professor_name
            FROM course_offerings o
            JOIN courses c ON o.course_id = c.course_id
            WHERE o.academic_year=2026 AND o.semester='2학기'
            LIMIT 5
        """)
        print("\n샘플 offerings:")
        for row in cursor.fetchall():
            print(row)
            
        # 스케줄 샘플
        cursor.execute("""
            SELECT o.offering_id, c.course_name, s.day_of_week, s.start_time, s.end_time, s.classroom
            FROM course_offerings o
            JOIN courses c ON o.course_id = c.course_id
            JOIN course_schedules s ON o.offering_id = s.offering_id
            WHERE o.academic_year=2026 AND o.semester='2학기'
            LIMIT 5
        """)
        print("\n샘플 스케줄:")
        for row in cursor.fetchall():
            print(row)
            
    conn.close()

if __name__ == '__main__':
    main()
