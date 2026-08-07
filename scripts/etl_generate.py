#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GradManager ETL Script
Parses Nexacro XML course timetable data (23-1 ~ 26-1)
Generates: cleaned CSV files + MySQL dump
"""
import xml.etree.ElementTree as ET
import csv
import os
import re
import sys
from datetime import datetime

if sys.platform == 'win32':
    import locale
    if hasattr(locale, 'getpreferredencoding'):
        locale.getpreferredencoding(True)

BASE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = r'C:\Users\cwr12\Downloads'
OUT_DIR = os.path.join(BASE, '..', 'data', 'output')
CSV_DIR = os.path.join(OUT_DIR, 'csv')
SQL_DIR = os.path.join(OUT_DIR, 'sql')

NS = '{http://www.nexacroplatform.com/platform/dataset}'
SEMESTER_MAP = {'1': '1학기', '2': '2학기', '3': '여름계절', '4': '겨울계절'}


def discover_xml_files():
    """Dynamically find all response XML files in Downloads"""
    result = []
    for fname in os.listdir(RAW_DIR):
        if not fname.startswith('response_') or not fname.endswith('.xml'):
            continue
        base = fname[9:-4]  # remove 'response_' and '.xml'
        m = re.match(r'(\d{4})[_]?(\d)$', base)
        if m:
            year = int(m.group(1))
            sem = m.group(2)
            result.append((fname, year, sem))
            continue
        if u'\u05b5' in base or '여름' in base:
            year_m = re.search(r'(\d{4})', base)
            if year_m:
                result.append((fname, int(year_m.group(1)), '3'))
            continue
        if '\uaca0' in base or '겨울' in base:
            year_m = re.search(r'(\d{4})', base)
            if year_m:
                result.append((fname, int(year_m.group(1)), '4'))
    result.sort(key=lambda x: (x[1], x[2]))
    return result


def parse_time_string(time_str):
    """Parse time strings like '금요일(16:00~17:15), 금요일(17:30~18:45)'"""
    results = []
    if not time_str or time_str.strip() == "-":
        return results
    
    # 쉼표 구분 없이 연속된 형태도 re.findall을 사용해 모두 추출
    pattern = r'([월화수목금토일])(?:요일)?\((\d{1,2}):(\d{2})~(\d{1,2}):(\d{2})\)'
    matches = re.findall(pattern, time_str)
    
    day_map = {
        '월': '월', '화': '화', '수': '수', '목': '목', '금': '금', '토': '토', '일': '일',
    }
    
    for day_char, sh, sm, eh, em in matches:
        day = day_map.get(day_char, day_char)
        results.append({
            'day_of_week': day,
            'start_time': '%02d:%s:00' % (int(sh), sm),
            'end_time': '%02d:%s:00' % (int(eh), em),
        })
    return results


def parse_room_string(room_str):
    if not room_str:
        return []
    cleaned = clean_room_string(room_str)
    result = []
    for r in cleaned.split(','):
        r = r.strip()
        if not r:
            continue
        r = clean_room_string(r)
        if r:
            result.append(r)
    return result


def parse_all_xml(xml_files):
    all_rows = []
    for filename, year, sem_code in xml_files:
        filepath = os.path.join(RAW_DIR, filename)
        if not os.path.exists(filepath):
            print('  [SKIP] %s not found' % filename)
            continue
        print('  [PARSING] %s...' % filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = f.read()
        
        # Check if XML is truncated (no closing </Root>)
        if '</Root>' not in raw:
            # Find last complete </Row> tag
            last_row_end = raw.rfind('</Row>')
            if last_row_end > 0:
                raw = raw[:last_row_end + len('</Row>')]
            # Remove any incomplete tags after the last </Row>
            raw = raw.rstrip()
            # Add proper closing tags
            raw += '\n</Rows>\n</Dataset>\n</Root>'
            print('    [WARN] XML truncated, repaired')
        
        root = ET.fromstring(raw)
        count = 0
        for ds in root.findall(NS + 'Dataset'):
            rows_container = ds.find(NS + 'Rows')
            if rows_container is None:
                continue
            for row in rows_container.findall(NS + 'Row'):
                data = {}
                for col in row.findall(NS + 'Col'):
                    cid = col.get('id')
                    data[cid] = col.text or ''
                data['_academic_year'] = year
                data['_semester_code'] = sem_code
                data['_semester_name'] = SEMESTER_MAP.get(sem_code, sem_code)
                all_rows.append(data)
                count += 1
        print('    -> %d rows' % count)
    return all_rows


def parse_credit(pnt_str):
    """Parse PNT field: handles (1), (0), .5, plain numbers"""
    if not pnt_str:
        return 0.0
    s = pnt_str.strip()
    # Strip parentheses: (1) -> 1, (0) -> 0
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1]
    try:
        return float(s)
    except ValueError:
        return 0.0


def clean_room_string(room_str):
    """Strip embedded student counts like ' ( 46 명 )' from room values"""
    if not room_str:
        return room_str
    return re.sub(r'\s*\(\s*\d+\s*명\s*\)', '', room_str).strip()


def build_courses(rows):
    course_map = {}
    for r in rows:
        code = r.get('COURSE_CD', '').strip()
        if not code:
            continue
        if code not in course_map:
            credit = parse_credit(r.get('PNT', '0'))
            course_map[code] = {
                'course_code': code,
                'course_name': r.get('COURSE_NM', '').strip(),
                'credit': credit,
                'course_type': r.get('COPL_GBNM', '').strip(),
                'source_url': '',
            }
    return course_map


def build_programs(rows):
    prog_map = {}
    prog_id = 1
    for r in rows:
        dept_cd = r.get('NOW_DEPT_CD', '').strip()
        dept_nm = r.get('NOW_DEPT_NM', '').strip()
        estb_cd = r.get('ESTB_SBJT_CD', '').strip()
        estb_nm = r.get('ESTB_SBJT_NM', '').strip()
        key = dept_cd if dept_cd else estb_cd
        name = dept_nm if dept_nm else estb_nm
        if key and key not in prog_map and name:
            prog_map[key] = {
                'program_id': prog_id,
                'program_name': name,
                'program_type': 'MAJOR',
                'required_credits': None,
                'effective_from_year': None,
                'effective_to_year': None,
                'source_url': '',
            }
            prog_id += 1
    return prog_map


def build_course_offerings(rows):
    offerings = []
    schedules = []
    off_id = 1
    for r in rows:
        code = r.get('COURSE_CD', '').strip()
        if not code:
            continue
        year = r['_academic_year']
        sem = r['_semester_name']
        section = r.get('CLAS', '').strip()
        professor = r.get('LISTAGG_PESN_GEND_NM', '').strip()
        time_str = r.get('LISTAGG_TEHIN', '').strip()
        room_str = r.get('LISTAGG_ROOM', '').strip()

        offerings.append({
            'offering_id': off_id,
            'course_code': code,
            'academic_year': year,
            'semester': sem,
            'section': section,
            'professor_name': professor,
            'syllabus_url': '',
        })

        time_slots = parse_time_string(time_str)
        rooms = parse_room_string(room_str)
        for i, slot in enumerate(time_slots):
            room = rooms[i] if i < len(rooms) else (rooms[0] if rooms else '')
            schedules.append({
                'schedule_id': len(schedules) + 1,
                'offering_id': off_id,
                'day_of_week': slot['day_of_week'],
                'start_time': slot['start_time'],
                'end_time': slot['end_time'],
                'classroom': room,
            })
        off_id += 1
    return offerings, schedules


def write_csv(filename, columns, data_rows):
    filepath = os.path.join(CSV_DIR, filename)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in data_rows:
            writer.writerow({k: row.get(k, '') for k in columns})
    print('  [CSV] %s (%d rows)' % (filename, len(data_rows)))


def escape_sql(val):
    if val is None:
        return 'NULL'
    s = str(val)
    s = s.replace('\\', '\\\\')
    s = s.replace("'", "\\'")
    s = s.replace('"', '\\"')
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    s = s.replace('\t', '\\t')
    return "'%s'" % s


def build_mysql_dump(programs, courses, offerings, schedules):
    lines = []
    lines.append('-- GradManager MySQL Dump')
    lines.append('-- Generated: %s' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    lines.append('-- Source: Nexacro Course Timetable XML (23-1 ~ 26-2)')
    lines.append('')
    lines.append('SET NAMES utf8mb4;')
    lines.append('SET CHARACTER SET utf8mb4;')
    lines.append('SET FOREIGN_KEY_CHECKS=0;')
    lines.append('SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";')
    lines.append('')

    # ── programs ──
    lines.append('DROP TABLE IF EXISTS `programs`;')
    lines.append('CREATE TABLE `programs` (')
    lines.append('  `program_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `program_name` VARCHAR(100) NOT NULL,')
    lines.append('  `program_type` VARCHAR(30) NOT NULL DEFAULT \'MAJOR\',')
    lines.append('  `required_credits` DECIMAL(5,1) DEFAULT NULL,')
    lines.append('  `effective_from_year` INT NOT NULL,')
    lines.append('  `effective_to_year` INT DEFAULT NULL,')
    lines.append('  `source_url` TEXT NOT NULL,')
    lines.append('  PRIMARY KEY (`program_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')
    for p in programs.values():
        eff_from = p['effective_from_year']
        eff_to = p['effective_to_year']
        req = p['required_credits']
        lines.append(
            "INSERT INTO `programs` (`program_id`,`program_name`,`program_type`,"
            "`required_credits`,`effective_from_year`,`effective_to_year`,`source_url`) "
            "VALUES (%d,%s,%s,%s,%s,%s,%s);" % (
                p['program_id'], escape_sql(p['program_name']),
                escape_sql(p['program_type']),
                str(req) if req else 'NULL',
                str(eff_from) if eff_from else 'NULL',
                str(eff_to) if eff_to else 'NULL',
                escape_sql(p['source_url'])))
    lines.append('')

    # ── courses ──
    lines.append('DROP TABLE IF EXISTS `courses`;')
    lines.append('CREATE TABLE `courses` (')
    lines.append('  `course_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `course_code` VARCHAR(30) NOT NULL,')
    lines.append('  `course_name` VARCHAR(150) NOT NULL,')
    lines.append('  `credit` DECIMAL(3,1) NOT NULL,')
    lines.append('  `theory_hours` DECIMAL(3,1) DEFAULT NULL,')
    lines.append('  `practice_hours` DECIMAL(3,1) DEFAULT NULL,')
    lines.append('  `course_description` TEXT DEFAULT NULL,')
    lines.append('  `source_url` TEXT NOT NULL,')
    lines.append('  PRIMARY KEY (`course_id`),')
    lines.append('  UNIQUE KEY `uk_course_code` (`course_code`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')
    for cid, c in enumerate(courses.values(), 1):
        lines.append(
            "INSERT INTO `courses` (`course_id`,`course_code`,`course_name`,"
            "`credit`,`theory_hours`,`practice_hours`,`course_description`,`source_url`) "
            "VALUES (%d,%s,%s,%s,NULL,NULL,NULL,%s);" % (
                cid, escape_sql(c['course_code']),
                escape_sql(c['course_name']),
                c['credit'],
                escape_sql(c['source_url'])))
    lines.append('')

    # ── course_offerings ──
    lines.append('DROP TABLE IF EXISTS `course_offerings`;')
    lines.append('CREATE TABLE `course_offerings` (')
    lines.append('  `offering_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `course_id` INT NOT NULL,')
    lines.append('  `academic_year` INT NOT NULL,')
    lines.append('  `semester` VARCHAR(10) NOT NULL,')
    lines.append('  `section` VARCHAR(20) NOT NULL,')
    lines.append('  `professor_name` VARCHAR(100) DEFAULT NULL,')
    lines.append('  `syllabus_url` TEXT DEFAULT NULL,')
    lines.append('  PRIMARY KEY (`offering_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    code_to_id = {c['course_code']: i for i, c in enumerate(courses.values(), 1)}
    for o in offerings:
        cid = code_to_id.get(o['course_code'], 0)
        lines.append(
            "INSERT INTO `course_offerings` (`offering_id`,`course_id`,`academic_year`,"
            "`semester`,`section`,`professor_name`,`syllabus_url`) "
            "VALUES (%d,%d,%d,%s,%s,%s,%s);" % (
                o['offering_id'], cid, o['academic_year'],
                escape_sql(o['semester']), escape_sql(o['section']),
                escape_sql(o['professor_name']), escape_sql(o['syllabus_url'])))
    lines.append('')

    # ── course_schedules ──
    lines.append('DROP TABLE IF EXISTS `course_schedules`;')
    lines.append('CREATE TABLE `course_schedules` (')
    lines.append('  `schedule_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `offering_id` INT NOT NULL,')
    lines.append('  `day_of_week` VARCHAR(10) NOT NULL,')
    lines.append('  `start_time` TIME NOT NULL,')
    lines.append('  `end_time` TIME NOT NULL,')
    lines.append('  `classroom` VARCHAR(100) DEFAULT NULL,')
    lines.append('  PRIMARY KEY (`schedule_id`),')
    lines.append('  KEY `fk_schedule_offering` (`offering_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')
    for s in schedules:
        lines.append(
            "INSERT INTO `course_schedules` (`schedule_id`,`offering_id`,"
            "`day_of_week`,`start_time`,`end_time`,`classroom`) "
            "VALUES (%d,%d,%s,%s,%s,%s);" % (
                s['schedule_id'], s['offering_id'],
                escape_sql(s['day_of_week']), escape_sql(s['start_time']),
                escape_sql(s['end_time']), escape_sql(s['classroom'])))
    lines.append('')

    # ── Remaining tables (DDL only, no data) ──

    lines.append('-- ── User / Student tables ──')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `users`;')
    lines.append('CREATE TABLE `users` (')
    lines.append('  `user_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `login_id` VARCHAR(50) NOT NULL,')
    lines.append('  `password_hash` VARCHAR(255) NOT NULL,')
    lines.append('  `role` VARCHAR(20) NOT NULL DEFAULT \'STUDENT\',')
    lines.append('  PRIMARY KEY (`user_id`),')
    lines.append('  UNIQUE KEY `uk_login_id` (`login_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `students`;')
    lines.append('CREATE TABLE `students` (')
    lines.append('  `student_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `user_id` INT NOT NULL,')
    lines.append('  `student_number` VARCHAR(20) NOT NULL,')
    lines.append('  `admission_year` INT NOT NULL,')
    lines.append('  `current_grade` INT NOT NULL,')
    lines.append('  PRIMARY KEY (`student_id`),')
    lines.append('  UNIQUE KEY `uk_student_user` (`user_id`),')
    lines.append('  UNIQUE KEY `uk_student_number` (`student_number`),')
    lines.append('  CONSTRAINT `fk_student_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `student_programs`;')
    lines.append('CREATE TABLE `student_programs` (')
    lines.append('  `student_program_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `student_id` INT NOT NULL,')
    lines.append('  `program_id` INT NOT NULL,')
    lines.append('  `program_role` VARCHAR(20) NOT NULL DEFAULT \'PRIMARY\',')
    lines.append('  `selected_year` INT DEFAULT NULL,')
    lines.append('  `completion_status` VARCHAR(20) DEFAULT NULL,')
    lines.append('  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,')
    lines.append('  PRIMARY KEY (`student_program_id`),')
    lines.append('  CONSTRAINT `fk_sp_student` FOREIGN KEY (`student_id`) REFERENCES `students`(`student_id`),')
    lines.append('  CONSTRAINT `fk_sp_program` FOREIGN KEY (`program_id`) REFERENCES `programs`(`program_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `student_course_history`;')
    lines.append('CREATE TABLE `student_course_history` (')
    lines.append('  `history_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `student_id` INT NOT NULL,')
    lines.append('  `course_id` INT NOT NULL,')
    lines.append('  `academic_year` INT DEFAULT NULL,')
    lines.append('  `semester` VARCHAR(10) DEFAULT NULL,')
    lines.append('  `earned_credit` DECIMAL(3,1) DEFAULT NULL,')
    lines.append('  `completion_status` VARCHAR(20) NOT NULL,')
    lines.append('  `is_retake` BOOLEAN NOT NULL DEFAULT FALSE,')
    lines.append('  `attempt_no` INT NOT NULL DEFAULT 1,')
    lines.append('  `original_history_id` INT DEFAULT NULL,')
    lines.append('  `credit_counted` BOOLEAN NOT NULL DEFAULT TRUE,')
    lines.append('  PRIMARY KEY (`history_id`),')
    lines.append('  CONSTRAINT `fk_sch_student` FOREIGN KEY (`student_id`) REFERENCES `students`(`student_id`),')
    lines.append('  CONSTRAINT `fk_sch_course` FOREIGN KEY (`course_id`) REFERENCES `courses`(`course_id`),')
    lines.append('  CONSTRAINT `fk_sch_original` FOREIGN KEY (`original_history_id`) REFERENCES `student_course_history`(`history_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `user_interests`;')
    lines.append('CREATE TABLE `user_interests` (')
    lines.append('  `user_interest_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `user_id` INT NOT NULL,')
    lines.append('  `interest_type` VARCHAR(30) NOT NULL,')
    lines.append('  `keyword` VARCHAR(100) NOT NULL,')
    lines.append('  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,')
    lines.append('  PRIMARY KEY (`user_interest_id`),')
    lines.append('  CONSTRAINT `fk_ui_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('-- ── Curriculum tables ──')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `curriculum_courses`;')
    lines.append('CREATE TABLE `curriculum_courses` (')
    lines.append('  `curriculum_course_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `curriculum_year` INT NOT NULL,')
    lines.append('  `course_id` INT NOT NULL,')
    lines.append('  `recommended_grade` INT DEFAULT NULL,')
    lines.append('  `semester` VARCHAR(10) DEFAULT NULL,')
    lines.append('  `completion_type` VARCHAR(30) NOT NULL,')
    lines.append('  `is_required` BOOLEAN NOT NULL DEFAULT FALSE,')
    lines.append('  `note` TEXT DEFAULT NULL,')
    lines.append('  PRIMARY KEY (`curriculum_course_id`),')
    lines.append('  CONSTRAINT `fk_cc_course` FOREIGN KEY (`course_id`) REFERENCES `courses`(`course_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `graduation_requirements`;')
    lines.append('CREATE TABLE `graduation_requirements` (')
    lines.append('  `requirement_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `admission_year` INT NOT NULL,')
    lines.append('  `program_id` INT DEFAULT NULL,')
    lines.append('  `requirement_category` VARCHAR(50) NOT NULL,')
    lines.append('  `required_credits` DECIMAL(6,1) DEFAULT NULL,')
    lines.append('  `requirement_text` TEXT DEFAULT NULL,')
    lines.append('  `source_url` TEXT DEFAULT NULL,')
    lines.append('  PRIMARY KEY (`requirement_id`),')
    lines.append('  CONSTRAINT `fk_gr_program` FOREIGN KEY (`program_id`) REFERENCES `programs`(`program_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `program_courses`;')
    lines.append('CREATE TABLE `program_courses` (')
    lines.append('  `program_course_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `program_id` INT NOT NULL,')
    lines.append('  `course_id` INT NOT NULL,')
    lines.append('  `effective_year` INT NOT NULL,')
    lines.append('  `recognition_credit` DECIMAL(3,1) DEFAULT NULL,')
    lines.append('  `is_required` BOOLEAN DEFAULT NULL,')
    lines.append('  `note` TEXT DEFAULT NULL,')
    lines.append('  PRIMARY KEY (`program_course_id`),')
    lines.append('  CONSTRAINT `fk_pc_program` FOREIGN KEY (`program_id`) REFERENCES `programs`(`program_id`),')
    lines.append('  CONSTRAINT `fk_pc_course` FOREIGN KEY (`course_id`) REFERENCES `courses`(`course_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('-- ── AI / Keyword tables ──')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `course_keywords`;')
    lines.append('CREATE TABLE `course_keywords` (')
    lines.append('  `keyword_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `offering_id` INT NOT NULL,')
    lines.append('  `keyword` VARCHAR(100) NOT NULL,')
    lines.append('  `keyword_source` VARCHAR(20) NOT NULL,')
    lines.append('  `confidence_score` DECIMAL(5,2) DEFAULT NULL,')
    lines.append('  `keyword_category` VARCHAR(50) DEFAULT NULL,')
    lines.append('  `weight` DECIMAL(5,2) DEFAULT NULL,')
    lines.append('  `source_text` TEXT DEFAULT NULL,')
    lines.append('  PRIMARY KEY (`keyword_id`),')
    lines.append('  CONSTRAINT `fk_ck_offering` FOREIGN KEY (`offering_id`) REFERENCES `course_offerings`(`offering_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `course_recommendations`;')
    lines.append('CREATE TABLE `course_recommendations` (')
    lines.append('  `recommendation_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `student_id` INT NOT NULL,')
    lines.append('  `offering_id` INT NOT NULL,')
    lines.append('  `match_score` DECIMAL(5,2) NOT NULL,')
    lines.append('  `reason` TEXT DEFAULT NULL,')
    lines.append('  `generated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,')
    lines.append('  PRIMARY KEY (`recommendation_id`),')
    lines.append('  CONSTRAINT `fk_cr_student` FOREIGN KEY (`student_id`) REFERENCES `students`(`student_id`),')
    lines.append('  CONSTRAINT `fk_cr_offering` FOREIGN KEY (`offering_id`) REFERENCES `course_offerings`(`offering_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('-- ── Chat tables ──')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `chat_sessions`;')
    lines.append('CREATE TABLE `chat_sessions` (')
    lines.append('  `session_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `user_id` INT NOT NULL,')
    lines.append('  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,')
    lines.append('  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,')
    lines.append('  PRIMARY KEY (`session_id`),')
    lines.append('  CONSTRAINT `fk_cs_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `chat_messages`;')
    lines.append('CREATE TABLE `chat_messages` (')
    lines.append('  `message_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `session_id` INT NOT NULL,')
    lines.append('  `sender_type` VARCHAR(20) NOT NULL,')
    lines.append('  `message_text` TEXT NOT NULL,')
    lines.append('  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,')
    lines.append('  PRIMARY KEY (`message_id`),')
    lines.append('  CONSTRAINT `fk_cm_session` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions`(`session_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('-- ── Academic events / Notices ──')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `academic_events`;')
    lines.append('CREATE TABLE `academic_events` (')
    lines.append('  `event_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `academic_year` INT NOT NULL,')
    lines.append('  `semester` VARCHAR(10) DEFAULT NULL,')
    lines.append('  `event_name` VARCHAR(200) NOT NULL,')
    lines.append('  `event_type` VARCHAR(50) NOT NULL,')
    lines.append('  `start_date` DATE NOT NULL,')
    lines.append('  `end_date` DATE DEFAULT NULL,')
    lines.append('  `is_mandatory` BOOLEAN NOT NULL DEFAULT TRUE,')
    lines.append('  `description` TEXT DEFAULT NULL,')
    lines.append('  `source_url` TEXT DEFAULT NULL,')
    lines.append('  PRIMARY KEY (`event_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('DROP TABLE IF EXISTS `notices`;')
    lines.append('CREATE TABLE `notices` (')
    lines.append('  `notice_id` INT NOT NULL AUTO_INCREMENT,')
    lines.append('  `source_board` VARCHAR(100) NOT NULL,')
    lines.append('  `title` VARCHAR(300) NOT NULL,')
    lines.append('  `category` VARCHAR(50) DEFAULT NULL,')
    lines.append('  `posted_date` DATE NOT NULL,')
    lines.append('  `notice_url` TEXT NOT NULL,')
    lines.append('  `content` TEXT DEFAULT NULL,')
    lines.append('  PRIMARY KEY (`notice_id`)')
    lines.append(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
    lines.append('')

    lines.append('SET FOREIGN_KEY_CHECKS=1;')
    return '\n'.join(lines)


def main():
    os.makedirs(CSV_DIR, exist_ok=True)
    os.makedirs(SQL_DIR, exist_ok=True)

    print('=== Step 1: Discover XML files ===')
    xml_files = discover_xml_files()
    for fname, year, sem in xml_files:
        print('  %s -> %d-%s' % (fname, year, sem))
    print('  Total files: %d' % len(xml_files))

    print('\n=== Step 2: Parse all XML files ===')
    rows = parse_all_xml(xml_files)
    print('  Total rows: %d' % len(rows))

    print('\n=== Step 3: Build data structures ===')
    courses = build_courses(rows)
    programs = build_programs(rows)
    offerings, schedules = build_course_offerings(rows)
    print('  Unique courses: %d' % len(courses))
    print('  Unique programs: %d' % len(programs))
    print('  Course offerings: %d' % len(offerings))
    print('  Schedule entries: %d' % len(schedules))

    print('\n=== Step 4: Write CSV files ===')
    code_to_id = {c['course_code']: i for i, c in enumerate(courses.values(), 1)}

    write_csv('programs.csv',
        ['program_id', 'program_name', 'program_type', 'required_credits',
         'effective_from_year', 'effective_to_year', 'source_url'],
        programs.values())

    course_rows = []
    for i, c in enumerate(courses.values(), 1):
        course_rows.append({
            'course_id': i, 'course_code': c['course_code'],
            'course_name': c['course_name'], 'credit': c['credit'],
            'theory_hours': '', 'practice_hours': '',
            'course_description': '', 'source_url': c['source_url'],
        })
    write_csv('courses.csv',
        ['course_id', 'course_code', 'course_name', 'credit',
         'theory_hours', 'practice_hours', 'course_description', 'source_url'],
        course_rows)

    offering_rows = []
    for o in offerings:
        offering_rows.append({
            'offering_id': o['offering_id'],
            'course_id': code_to_id.get(o['course_code'], ''),
            'academic_year': o['academic_year'],
            'semester': o['semester'], 'section': o['section'],
            'professor_name': o['professor_name'],
            'syllabus_url': o['syllabus_url'],
        })
    write_csv('course_offerings.csv',
        ['offering_id', 'course_id', 'academic_year', 'semester',
         'section', 'professor_name', 'syllabus_url'],
        offering_rows)

    write_csv('course_schedules.csv',
        ['schedule_id', 'offering_id', 'day_of_week', 'start_time',
         'end_time', 'classroom'],
        schedules)

    raw_cols = ['ESTB_SBJT_CD', 'ESTB_SBJT_NM', 'SHYR', 'SMST_GBCD',
                'COURSE_CD', 'COURSE_NM', 'CLAS', 'COPL_GBNM',
                'LISTAGG_GRADE', 'PNT', 'LISTAGG_TEHIN', 'LISTAGG_ROOM',
                'LISTAGG_PESN_GEND_NM', 'PESN_NO', 'INWON', 'NOTE',
                'MMDIST_GBNM', 'PLAN_YN', 'BUID_NM', 'CYBER_GBCD',
                'NOW_DEPT_CD', 'NOW_DEPT_NM',
                '_academic_year', '_semester_code', '_semester_name']
    write_csv('raw_data.csv', raw_cols, rows)

    print('\n=== Step 5: Generate MySQL dump ===')
    dump = build_mysql_dump(programs, courses, offerings, schedules)
    dump_path = os.path.join(SQL_DIR, 'gradmanager_dump.sql')
    with open(dump_path, 'w', encoding='utf-8') as f:
        f.write(dump)
    print('  [SQL] gradmanager_dump.sql (%d bytes)' % len(dump))

    print('\n=== Done! ===')
    print('  CSV files: %s' % CSV_DIR)
    print('  SQL dump:  %s' % dump_path)

    # Summary
    print('\n=== Summary ===')
    by_semester = {}
    for r in rows:
        key = '%d-%s' % (r['_academic_year'], r['_semester_code'])
        by_semester[key] = by_semester.get(key, 0) + 1
    for k in sorted(by_semester.keys()):
        print('  %s: %d courses' % (k, by_semester[k]))


if __name__ == '__main__':
    main()
