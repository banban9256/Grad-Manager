-- ==========================================
-- GradManager Database Schema DDL (PostgreSQL)
-- ==========================================

-- 1. users (사용자 계정)
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    login_id VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('STUDENT', 'ADMIN')),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'BANNED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 2. students (학생 상세정보)
CREATE TABLE students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    student_number VARCHAR(20) NOT NULL UNIQUE,
    admission_year INT NOT NULL CHECK (admission_year BETWEEN 2000 AND 2099),
    current_grade INT NOT NULL CHECK (current_grade BETWEEN 1 AND 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 3. programs (전공과정 마스터)
CREATE TABLE programs (
    program_id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_name VARCHAR(100) NOT NULL,
    program_type VARCHAR(30) NOT NULL CHECK (program_type IN ('MAJOR', 'SPECIALIZED', 'CONVERGENCE')),
    required_credits REAL(5,1) DEFAULT 0.0 CHECK (required_credits >= 0),
    effective_from_year INT NOT NULL CHECK (effective_from_year BETWEEN 2000 AND 2099),
    effective_to_year INT CHECK (effective_to_year BETWEEN 2000 AND 2099),
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 4. student_programs (학생 선택 전공과정)
CREATE TABLE student_programs (
    student_program_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    program_id INT NOT NULL REFERENCES programs(program_id) ON DELETE CASCADE,
    program_role VARCHAR(20) NOT NULL CHECK (program_role IN ('PRIMARY', 'ADDITIONAL')),
    selected_year INT CHECK (selected_year BETWEEN 2000 AND 2099),
    completion_status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS' CHECK (completion_status IN ('IN_PROGRESS', 'COMPLETED', 'FAILED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 한 명의 학생은 본전공(PRIMARY) 1개, 추가전공(ADDITIONAL) 최대 1개만 매핑 가능하도록 강제
    CONSTRAINT unique_student_program_role UNIQUE (student_id, program_role)
);



-- 5. graduation_requirements (졸업 요건 세부항목)
CREATE TABLE graduation_requirements (
    requirement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_year INT NOT NULL CHECK (admission_year BETWEEN 2000 AND 2099),
    program_id INT REFERENCES programs(program_id) ON DELETE SET NULL, -- 전체 공통 졸업요건일 경우 NULL 가능
    requirement_category VARCHAR(50) NOT NULL, -- 총학점, 교양필수, 전공필수, 영어성적 등
    required_credits REAL(6,1) DEFAULT 0.0 CHECK (required_credits >= 0),
    requirement_text TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 6. courses (교과목 마스터)
CREATE TABLE courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code VARCHAR(30) NOT NULL UNIQUE,
    course_name VARCHAR(150) NOT NULL,
    credit REAL(3,1) NOT NULL CHECK (credit >= 0),
    theory_hours REAL(3,1) DEFAULT 0.0 CHECK (theory_hours >= 0),
    practice_hours REAL(3,1) DEFAULT 0.0 CHECK (practice_hours >= 0),
    course_description TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 7. curriculum_courses (연도별 교육과정 편성 정보)
CREATE TABLE curriculum_courses (
    curriculum_course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    curriculum_year INT NOT NULL CHECK (curriculum_year BETWEEN 2000 AND 2099),
    course_id INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    recommended_grade INT CHECK (recommended_grade BETWEEN 1 AND 4),
    semester VARCHAR(10) CHECK (semester IN ('1학기', '2학기', '여름학기', '겨울학기')),
    completion_type VARCHAR(30) NOT NULL, -- 전필, 전선, 교필, 교선 등
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 동일 연도에 같은 과목이 중복 편성되는 것을 방지
    CONSTRAINT unique_curriculum_year_course UNIQUE (curriculum_year, course_id)
);



-- 8. program_courses (전공과정별 인정 과목 매핑)
CREATE TABLE program_courses (
    program_course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INT NOT NULL REFERENCES programs(program_id) ON DELETE CASCADE,
    course_id INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    effective_year INT NOT NULL CHECK (effective_year BETWEEN 2000 AND 2099),
    recognition_credit REAL(3,1) CHECK (recognition_credit >= 0),
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 중복 매핑 방지
    CONSTRAINT unique_program_course UNIQUE (program_id, course_id, effective_year)
);



-- 9. course_offerings (학기별 실제 개설 강좌)
CREATE TABLE course_offerings (
    offering_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    academic_year INT NOT NULL CHECK (academic_year BETWEEN 2000 AND 2099),
    semester VARCHAR(10) NOT NULL CHECK (semester IN ('1학기', '2학기', '여름학기', '겨울학기')),
    section VARCHAR(20) NOT NULL, -- 분반 번호
    professor_name VARCHAR(100),
    syllabus_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 학수번호, 학년도, 학기, 분반 기준 유니크
    CONSTRAINT unique_offering UNIQUE (course_id, academic_year, semester, section)
);



-- 10. course_schedules (개설강좌별 강의시간 및 장소)
CREATE TABLE course_schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offering_id INT NOT NULL REFERENCES course_offerings(offering_id) ON DELETE CASCADE,
    day_of_week VARCHAR(10) NOT NULL CHECK (day_of_week IN ('MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN')),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    period_number INT CHECK (period_number BETWEEN 1 AND 12), -- 시간 계산 편의를 위해 보완된 교시 정보
    classroom VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_time_flow CHECK (start_time < end_time)
);



-- 11. tags (공통 표준 키워드 태그 - **신설**)
CREATE TABLE tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name VARCHAR(50) NOT NULL UNIQUE,
    tag_category VARCHAR(50) DEFAULT 'GENERAL', -- 학과, 기술스택, 진무분야 등 카테고리
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 12. user_interests (사용자 관심 키워드 매핑)
CREATE TABLE user_interests (
    user_interest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    interest_type VARCHAR(30) NOT NULL CHECK (interest_type IN ('COURSE', 'EVENT')),
    tag_id INT NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_interest_tag UNIQUE (user_id, interest_type, tag_id)
);



-- 13. course_keywords (개설강좌별 특징 태그/추출 키워드)
CREATE TABLE course_keywords (
    keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offering_id INT NOT NULL REFERENCES course_offerings(offering_id) ON DELETE CASCADE,
    tag_id INT NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    keyword_source VARCHAR(20) NOT NULL DEFAULT 'AI' CHECK (keyword_source IN ('AI', 'USER', 'SYSTEM')),
    confidence_score REAL(5,2) CHECK (confidence_score BETWEEN 0.0 AND 100.0),
    weight REAL(5,2) DEFAULT 1.0 CHECK (weight >= 0),
    source_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_offering_tag UNIQUE (offering_id, tag_id)
);



-- 14. student_course_history (학생 이수 내역 및 성적)
CREATE TABLE student_course_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    course_id INT NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT, -- 이수 내역이 있는 과목은 함부로 삭제 불가능하도록 제약
    academic_year INT NOT NULL CHECK (academic_year BETWEEN 2000 AND 2099),
    semester VARCHAR(10) NOT NULL CHECK (semester IN ('1학기', '2학기', '여름학기', '겨울학기')),
    earned_credit REAL(3,1) NOT NULL CHECK (earned_credit >= 0),
    completion_status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED' CHECK (completion_status IN ('COMPLETED', 'FAILED', 'RETRACTED')),
    is_retake BOOLEAN NOT NULL DEFAULT FALSE,
    attempt_no INT NOT NULL DEFAULT 1 CHECK (attempt_no >= 1),
    original_history_id INT REFERENCES student_course_history(history_id) ON DELETE SET NULL, -- 재수강의 경우 최초 수강 이력 참조
    credit_counted BOOLEAN NOT NULL DEFAULT TRUE, -- 졸업 학점 계산에 반영 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 15. academic_events (학사 일정 관리)
CREATE TABLE academic_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    academic_year INT NOT NULL CHECK (academic_year BETWEEN 2000 AND 2099),
    semester VARCHAR(10) CHECK (semester IN ('1학기', '2학기', '여름학기', '겨울학기')),
    event_name VARCHAR(200) NOT NULL,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('TUITION_PAYMENT', 'PRE_REGISTRATION', 'COURSE_REGISTRATION', 'FINAL_COURSE_EVALUATION', 'OTHER')),
    start_date DATE NOT NULL,
    end_date DATE,
    is_mandatory BOOLEAN DEFAULT FALSE,
    description TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 16. notices (공지사항 수집함)
CREATE TABLE notices (
    notice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_board VARCHAR(100) NOT NULL DEFAULT 'SW대학 공지',
    title VARCHAR(300) NOT NULL,
    category VARCHAR(50),
    posted_date DATE NOT NULL,
    notice_url TEXT NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 17. course_recommendations (학생별 강의 추천 결과 저장)
CREATE TABLE course_recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    offering_id INT NOT NULL REFERENCES course_offerings(offering_id) ON DELETE CASCADE,
    match_score REAL(5,2) NOT NULL CHECK (match_score BETWEEN 0.0 AND 100.0),
    reason TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 18. chat_sessions (챗봇 대화방)
CREATE TABLE chat_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- 19. chat_messages (챗봇 대화 내용 기록)
CREATE TABLE chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('USER', 'ASSISTANT')),
    message_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- ==========================================
-- 효율적인 추천 및 검색을 위한 데이터베이스 인덱스(INDEX) 정의
-- ==========================================

-- 학생 학수번호 수강이력 탐색 최적화
CREATE INDEX idx_history_student ON student_course_history (student_id);

-- 학기별 강좌 개설정보 조회 최적화
CREATE INDEX idx_offerings_semester ON course_offerings (academic_year, semester);

-- AI 추천 결과 매칭 연산용
CREATE INDEX idx_recommendations_student ON course_recommendations (student_id, match_score DESC);

-- 공지사항 최신순 조회 최적화
CREATE INDEX idx_notices_posted ON notices (posted_date DESC);
