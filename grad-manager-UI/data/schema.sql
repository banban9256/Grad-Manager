-- ==========================================
-- GradManager Database Schema DDL (PostgreSQL)
-- ==========================================

-- 1. users (사용자 계정)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    login_id VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('STUDENT', 'ADMIN')),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'BANNED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS '사용자 로그인 및 권한 관리 테이블';
COMMENT ON COLUMN users.user_id IS '사용자 고유 식별 번호 (PK)';
COMMENT ON COLUMN users.login_id IS '로그인용 사용자 아이디 (Unique)';
COMMENT ON COLUMN users.password_hash IS '단방향 암호화(해시)된 패스워드';
COMMENT ON COLUMN users.role IS '사용자 역할 (STUDENT: 학생, ADMIN: 관리자)';
COMMENT ON COLUMN users.status IS '사용자 계정 상태 (ACTIVE: 활성, INACTIVE: 휴면, BANNED: 차단)';


-- 2. students (학생 상세정보)
CREATE TABLE students (
    student_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    student_number VARCHAR(20) NOT NULL UNIQUE,
    admission_year INT NOT NULL CHECK (admission_year BETWEEN 2000 AND 2099),
    current_grade INT NOT NULL CHECK (current_grade BETWEEN 1 AND 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE students IS '학생 기본 프로필 정보 테이블';
COMMENT ON COLUMN students.student_id IS '학생 고유 식별 번호 (PK)';
COMMENT ON COLUMN students.user_id IS '연결된 사용자 계정 ID (FK, 1:1)';
COMMENT ON COLUMN students.student_number IS '학번 (Unique)';
COMMENT ON COLUMN students.admission_year IS '입학 연도 (졸업요건 적용 기준)';
COMMENT ON COLUMN students.current_grade IS '현재 학년 (1~4)';


-- 3. programs (전공과정 마스터)
CREATE TABLE programs (
    program_id SERIAL PRIMARY KEY,
    program_name VARCHAR(100) NOT NULL,
    program_type VARCHAR(30) NOT NULL CHECK (program_type IN ('MAJOR', 'SPECIALIZED', 'CONVERGENCE')),
    required_credits DECIMAL(5,1) DEFAULT 0.0 CHECK (required_credits >= 0),
    effective_from_year INT NOT NULL CHECK (effective_from_year BETWEEN 2000 AND 2099),
    effective_to_year INT CHECK (effective_to_year BETWEEN 2000 AND 2099),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE programs IS '학과 전공과정(본전공, 특화전공, 융합전공) 정의 테이블';
COMMENT ON COLUMN programs.program_id IS '전공과정 고유 ID (PK)';
COMMENT ON COLUMN programs.program_name IS '전공과정 명칭 (예: AISW 본전공, 특화전공 등)';
COMMENT ON COLUMN programs.program_type IS '전공 구분 (MAJOR: 본전공, SPECIALIZED: 특화전공, CONVERGENCE: 융합전공)';
COMMENT ON COLUMN programs.required_credits IS '전공 이수를 위해 필요한 총 기준 학점';
COMMENT ON COLUMN programs.effective_from_year IS '적용 시작연도';
COMMENT ON COLUMN programs.effective_to_year IS '적용 종료연도 (NULL 허용)';
COMMENT ON COLUMN programs.source_url IS '공식 졸업요건 요람 출처 링크';


-- 4. student_programs (학생 선택 전공과정)
CREATE TABLE student_programs (
    student_program_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    program_id INT NOT NULL REFERENCES programs(program_id) ON DELETE CASCADE,
    program_role VARCHAR(20) NOT NULL CHECK (program_role IN ('PRIMARY', 'ADDITIONAL')),
    selected_year INT CHECK (selected_year BETWEEN 2000 AND 2099),
    completion_status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS' CHECK (completion_status IN ('IN_PROGRESS', 'COMPLETED', 'FAILED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- 한 명의 학생은 본전공(PRIMARY) 1개, 추가전공(ADDITIONAL) 최대 1개만 매핑 가능하도록 강제
    CONSTRAINT unique_student_program_role UNIQUE (student_id, program_role)
);

COMMENT ON TABLE student_programs IS '학생별로 선택하여 이수 중인 전공과정 맵핑 테이블';
COMMENT ON COLUMN student_programs.student_program_id IS '학생 전공과정 연결 ID (PK)';
COMMENT ON COLUMN student_programs.student_id IS '학생 ID (FK)';
COMMENT ON COLUMN student_programs.program_id IS '선택한 전공과정 ID (FK)';
COMMENT ON COLUMN student_programs.program_role IS '전공 구분 역할 (PRIMARY: 본전공, ADDITIONAL: 특화/융합 추가전공)';
COMMENT ON COLUMN student_programs.selected_year IS '해당 전공 과정을 선택한 연도';
COMMENT ON COLUMN student_programs.completion_status IS '전공과정 이수 충족 상태 (IN_PROGRESS: 이수중, COMPLETED: 충족, FAILED: 미충족)';


-- 5. graduation_requirements (졸업 요건 세부항목)
CREATE TABLE graduation_requirements (
    requirement_id SERIAL PRIMARY KEY,
    admission_year INT NOT NULL CHECK (admission_year BETWEEN 2000 AND 2099),
    program_id INT REFERENCES programs(program_id) ON DELETE SET NULL, -- 전체 공통 졸업요건일 경우 NULL 가능
    requirement_category VARCHAR(50) NOT NULL, -- 총학점, 교양필수, 전공필수, 영어성적 등
    required_credits DECIMAL(6,1) DEFAULT 0.0 CHECK (required_credits >= 0),
    requirement_text TEXT,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE graduation_requirements IS '학번별/전공별 졸업요건 상세 정의 테이블';
COMMENT ON COLUMN graduation_requirements.requirement_id IS '졸업요건 고유 ID (PK)';
COMMENT ON COLUMN graduation_requirements.admission_year IS '해당 졸업요건이 적용되는 입학 학번';
COMMENT ON COLUMN graduation_requirements.program_id IS '적용되는 전공과정 ID (공통 요건일 경우 NULL, FK)';
COMMENT ON COLUMN graduation_requirements.requirement_category IS '졸업요건 대분류 (예: 총학점, 교양, 전공필수 등)';
COMMENT ON COLUMN graduation_requirements.required_credits IS '충족에 필요한 최소 학점 조건';
COMMENT ON COLUMN graduation_requirements.requirement_text IS '학점으로 환산할 수 없는 상세 조건 내용 (예: 논문 제출 등)';
COMMENT ON COLUMN graduation_requirements.source_url IS '공식 출처 주소';


-- 6. courses (교과목 마스터)
CREATE TABLE courses (
    course_id SERIAL PRIMARY KEY,
    course_code VARCHAR(30) NOT NULL UNIQUE,
    course_name VARCHAR(150) NOT NULL,
    credit DECIMAL(3,1) NOT NULL CHECK (credit >= 0),
    theory_hours DECIMAL(3,1) DEFAULT 0.0 CHECK (theory_hours >= 0),
    practice_hours DECIMAL(3,1) DEFAULT 0.0 CHECK (practice_hours >= 0),
    course_description TEXT,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE courses IS '전체 개설 가능한 교과목의 마스터 테이블';
COMMENT ON COLUMN courses.course_id IS '과목 고유 ID (PK)';
COMMENT ON COLUMN courses.course_code IS '학수번호 (Unique)';
COMMENT ON COLUMN courses.course_name IS '교과목명';
COMMENT ON COLUMN courses.credit IS '부여 학점';
COMMENT ON COLUMN courses.theory_hours IS '주당 이론 강의 시간';
COMMENT ON COLUMN courses.practice_hours IS '주당 실습/실험 강의 시간';
COMMENT ON COLUMN courses.course_description IS '교과목 설명 (키워드 분석에 사용)';
COMMENT ON COLUMN courses.source_url IS '공식 출처 주소';


-- 7. curriculum_courses (연도별 교육과정 편성 정보)
CREATE TABLE curriculum_courses (
    curriculum_course_id SERIAL PRIMARY KEY,
    curriculum_year INT NOT NULL CHECK (curriculum_year BETWEEN 2000 AND 2099),
    course_id INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    recommended_grade INT CHECK (recommended_grade BETWEEN 1 AND 4),
    semester VARCHAR(10) CHECK (semester IN ('1학기', '2학기', '여름학기', '겨울학기')),
    completion_type VARCHAR(30) NOT NULL, -- 전필, 전선, 교필, 교선 등
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- 동일 연도에 같은 과목이 중복 편성되는 것을 방지
    CONSTRAINT unique_curriculum_year_course UNIQUE (curriculum_year, course_id)
);

COMMENT ON TABLE curriculum_courses IS '특정 연도의 공식 교육과정에 편입된 과목 정보 테이블';
COMMENT ON COLUMN curriculum_courses.curriculum_course_id IS '교육과정 편성 ID (PK)';
COMMENT ON COLUMN curriculum_courses.curriculum_year IS '교육과정 적용 연도';
COMMENT ON COLUMN curriculum_courses.course_id IS '과목 ID (FK)';
COMMENT ON COLUMN curriculum_courses.recommended_grade IS '권장 이수 학년';
COMMENT ON COLUMN curriculum_courses.semester IS '권장 이수 학기';
COMMENT ON COLUMN curriculum_courses.completion_type IS '이수 구분';
COMMENT ON COLUMN curriculum_courses.is_required IS '해당 교육과정에서 무조건 이수해야 하는 필수과목 여부';
COMMENT ON COLUMN curriculum_courses.note IS '비고 및 대체과목 인정 등의 특이사항';


-- 8. program_courses (전공과정별 인정 과목 매핑)
CREATE TABLE program_courses (
    program_course_id SERIAL PRIMARY KEY,
    program_id INT NOT NULL REFERENCES programs(program_id) ON DELETE CASCADE,
    course_id INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    effective_year INT NOT NULL CHECK (effective_year BETWEEN 2000 AND 2099),
    recognition_credit DECIMAL(3,1) CHECK (recognition_credit >= 0),
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- 중복 매핑 방지
    CONSTRAINT unique_program_course UNIQUE (program_id, course_id, effective_year)
);

COMMENT ON TABLE program_courses IS '특화/융합전공 등 각 전공과정에서 전공 학점으로 대체 인정해 주는 과목 정보 테이블';
COMMENT ON COLUMN program_courses.program_course_id IS '전공과목 연결 ID (PK)';
COMMENT ON COLUMN program_courses.program_id IS '전공과정 ID (FK)';
COMMENT ON COLUMN program_courses.course_id IS '과목 ID (FK)';
COMMENT ON COLUMN program_courses.effective_year IS '적용 시작연도';
COMMENT ON COLUMN program_courses.recognition_credit IS '대체 인정해 주는 학점 수 (기본 과목 학점과 다를 수 있음)';
COMMENT ON COLUMN program_courses.is_required IS '해당 전공과정 내 필수 과목 여부';


-- 9. course_offerings (학기별 실제 개설 강좌)
CREATE TABLE course_offerings (
    offering_id SERIAL PRIMARY KEY,
    course_id INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    academic_year INT NOT NULL CHECK (academic_year BETWEEN 2000 AND 2099),
    semester VARCHAR(10) NOT NULL CHECK (semester IN ('1학기', '2학기', '여름학기', '겨울학기')),
    section VARCHAR(20) NOT NULL, -- 분반 번호
    professor_name VARCHAR(100),
    syllabus_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- 학수번호, 학년도, 학기, 분반 기준 유니크
    CONSTRAINT unique_offering UNIQUE (course_id, academic_year, semester, section)
);

COMMENT ON TABLE course_offerings IS '각 학기에 실제로 개설된 과목 분반 정보 테이블';
COMMENT ON COLUMN course_offerings.offering_id IS '개설강좌 고유 ID (PK)';
COMMENT ON COLUMN course_offerings.course_id IS '과목 ID (FK)';
COMMENT ON COLUMN course_offerings.academic_year IS '개설 연도 (예: 2026)';
COMMENT ON COLUMN course_offerings.semester IS '개설 학기 (1학기, 2학기 등)';
COMMENT ON COLUMN course_offerings.section IS '분반 기호/번호';
COMMENT ON COLUMN course_offerings.professor_name IS '담당 교수 명칭';
COMMENT ON COLUMN course_offerings.syllabus_url IS '강의계획서 원본 링크';


-- 10. course_schedules (개설강좌별 강의시간 및 장소)
CREATE TABLE course_schedules (
    schedule_id SERIAL PRIMARY KEY,
    offering_id INT NOT NULL REFERENCES course_offerings(offering_id) ON DELETE CASCADE,
    day_of_week VARCHAR(10) NOT NULL CHECK (day_of_week IN ('MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN')),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    period_number INT CHECK (period_number BETWEEN 1 AND 12), -- 시간 계산 편의를 위해 보완된 교시 정보
    classroom VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_time_flow CHECK (start_time < end_time)
);

COMMENT ON TABLE course_schedules IS '개설강좌의 상세 요일, 시간, 강의실 관리 테이블';
COMMENT ON COLUMN course_schedules.schedule_id IS '강의시간 고유 ID (PK)';
COMMENT ON COLUMN course_schedules.offering_id IS '개설강좌 ID (FK)';
COMMENT ON COLUMN course_schedules.day_of_week IS '요일 코드 (MON, TUE, WED...)';
COMMENT ON COLUMN course_schedules.start_time IS '강의 시작 시간';
COMMENT ON COLUMN course_schedules.end_time IS '강의 종료 시간';
COMMENT ON COLUMN course_schedules.period_number IS '시간표 배치용 기준 교시 정보 (예: 1~9)';
COMMENT ON COLUMN course_schedules.classroom IS '강의 공간(강의실) 정보';


-- 11. tags (공통 표준 키워드 태그 - **신설**)
CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(50) NOT NULL UNIQUE,
    tag_category VARCHAR(50) DEFAULT 'GENERAL', -- 학과, 기술스택, 진무분야 등 카테고리
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE tags IS '학생 관심사 및 개설 과목 키워드 불일치 방지를 위한 표준 키워드 마스터 테이블';
COMMENT ON COLUMN tags.tag_id IS '태그 고유 ID (PK)';
COMMENT ON COLUMN tags.tag_name IS '태그 명칭 (예: AI, 웹, 앱, 게임 등)';
COMMENT ON COLUMN tags.tag_category IS '태그 분류 범주';


-- 12. user_interests (사용자 관심 키워드 매핑)
CREATE TABLE user_interests (
    user_interest_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    interest_type VARCHAR(30) NOT NULL CHECK (interest_type IN ('COURSE', 'EVENT')),
    tag_id INT NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_interest_tag UNIQUE (user_id, interest_type, tag_id)
);

COMMENT ON TABLE user_interests IS '사용자가 등록한 관심 분야 태그 매핑 테이블';
COMMENT ON COLUMN user_interests.user_interest_id IS '관심 키워드 매핑 ID (PK)';
COMMENT ON COLUMN user_interests.user_id IS '사용자 계정 ID (FK)';
COMMENT ON COLUMN user_interests.interest_type IS '관심 키워드 대상 구분 (COURSE: 수강추천용, EVENT: 학사일정필터용)';
COMMENT ON COLUMN user_interests.tag_id IS '매핑된 표준 키워드 태그 ID (FK)';


-- 13. course_keywords (개설강좌별 특징 태그/추출 키워드)
CREATE TABLE course_keywords (
    keyword_id SERIAL PRIMARY KEY,
    offering_id INT NOT NULL REFERENCES course_offerings(offering_id) ON DELETE CASCADE,
    tag_id INT NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    keyword_source VARCHAR(20) NOT NULL DEFAULT 'AI' CHECK (keyword_source IN ('AI', 'USER', 'SYSTEM')),
    confidence_score DECIMAL(5,2) CHECK (confidence_score BETWEEN 0.0 AND 100.0),
    weight DECIMAL(5,2) DEFAULT 1.0 CHECK (weight >= 0),
    source_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_offering_tag UNIQUE (offering_id, tag_id)
);

COMMENT ON TABLE course_keywords IS '각 개설 강좌에서 추출되어 연계된 표준 키워드 정보';
COMMENT ON COLUMN course_keywords.keyword_id IS '강의 키워드 ID (PK)';
COMMENT ON COLUMN course_keywords.offering_id IS '개설강좌 ID (FK)';
COMMENT ON COLUMN course_keywords.tag_id IS '매핑된 표준 키워드 태그 ID (FK)';
COMMENT ON COLUMN course_keywords.keyword_source IS '키워드 매핑 주체 (AI 분석, 사용자 입력 등)';
COMMENT ON COLUMN course_keywords.confidence_score IS 'AI 텍스트 마이닝 매핑 신뢰도 수치 (0~100)';
COMMENT ON COLUMN course_keywords.weight IS '추천 가중치 (1.0 기준)';
COMMENT ON COLUMN course_keywords.source_text IS '키워드가 추출된 강의계획서/과목설명 내 원문';


-- 14. student_course_history (학생 이수 내역 및 성적)
CREATE TABLE student_course_history (
    history_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    course_id INT NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT, -- 이수 내역이 있는 과목은 함부로 삭제 불가능하도록 제약
    academic_year INT NOT NULL CHECK (academic_year BETWEEN 2000 AND 2099),
    semester VARCHAR(10) NOT NULL CHECK (semester IN ('1학기', '2학기', '여름학기', '겨울학기')),
    earned_credit DECIMAL(3,1) NOT NULL CHECK (earned_credit >= 0),
    completion_status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED' CHECK (completion_status IN ('COMPLETED', 'FAILED', 'RETRACTED')),
    is_retake BOOLEAN NOT NULL DEFAULT FALSE,
    attempt_no INT NOT NULL DEFAULT 1 CHECK (attempt_no >= 1),
    original_history_id INT REFERENCES student_course_history(history_id) ON DELETE SET NULL, -- 재수강의 경우 최초 수강 이력 참조
    credit_counted BOOLEAN NOT NULL DEFAULT TRUE, -- 졸업 학점 계산에 반영 여부
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE student_course_history IS '학생들이 과거에 이수했거나 현재 수강 중인 성적 및 이수 과목 이력 테이블';
COMMENT ON COLUMN student_course_history.history_id IS '이수내역 고유 ID (PK)';
COMMENT ON COLUMN student_course_history.student_id IS '학생 ID (FK)';
COMMENT ON COLUMN student_course_history.course_id IS '과목 ID (FK)';
COMMENT ON COLUMN student_course_history.academic_year IS '과목을 이수한 학년도';
COMMENT ON COLUMN student_course_history.semester IS '이수 학기';
COMMENT ON COLUMN student_course_history.earned_credit IS '해당 과목을 통과하며 취득한 학점 수';
COMMENT ON COLUMN student_course_history.completion_status IS '이수 결과 상태 (COMPLETED: 이수완료, FAILED: 과락/F학점, RETRACTED: 재수강 무효화)';
COMMENT ON COLUMN student_course_history.is_retake IS '재수강 여부 (첫 수강이면 FALSE, 재수강이면 TRUE)';
COMMENT ON COLUMN student_course_history.attempt_no IS '수강 시도 횟수 (1차 수강, 2차 수강 등)';
COMMENT ON COLUMN student_course_history.original_history_id IS '자가 참조 FK (재수강 시 최초 수강했을 때의 history_id 연계)';
COMMENT ON COLUMN student_course_history.credit_counted IS '졸업 소요학점 가산 여부 (재수강되어 무효 처리된 과목은 FALSE)';


-- 15. academic_events (학사 일정 관리)
CREATE TABLE academic_events (
    event_id SERIAL PRIMARY KEY,
    academic_year INT NOT NULL CHECK (academic_year BETWEEN 2000 AND 2099),
    semester VARCHAR(10) CHECK (semester IN ('1학기', '2학기', '여름학기', '겨울학기')),
    event_name VARCHAR(200) NOT NULL,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('TUITION_PAYMENT', 'PRE_REGISTRATION', 'COURSE_REGISTRATION', 'FINAL_COURSE_EVALUATION', 'OTHER')),
    start_date DATE NOT NULL,
    end_date DATE,
    is_mandatory BOOLEAN DEFAULT FALSE,
    description TEXT,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE academic_events IS '졸업 요건 관리 및 학사 등록 관련 주요 일정 정보';
COMMENT ON COLUMN academic_events.event_id IS '학사일정 고유 ID (PK)';
COMMENT ON COLUMN academic_events.academic_year IS '학사 학년도';
COMMENT ON COLUMN academic_events.event_name IS '학사 일정 명칭';
COMMENT ON COLUMN academic_events.event_type IS '일정 종류 (등록금 납부, 예비수강신청, 수강신청 등)';
COMMENT ON COLUMN academic_events.start_date IS '시작일';
COMMENT ON COLUMN academic_events.end_date IS '종료일 (하루 일정인 경우 NULL 허용)';
COMMENT ON COLUMN academic_events.is_mandatory IS '사용자 필수 알림 안내 대상 일정 여부';


-- 16. notices (공지사항 수집함)
CREATE TABLE notices (
    notice_id SERIAL PRIMARY KEY,
    source_board VARCHAR(100) NOT NULL DEFAULT 'SW대학 공지',
    title VARCHAR(300) NOT NULL,
    category VARCHAR(50),
    posted_date DATE NOT NULL,
    notice_url TEXT NOT NULL,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE notices IS 'SW대학 등 교내 주요 공지사항 데이터 수집 테이블';
COMMENT ON COLUMN notices.notice_id IS '공지사항 ID (PK)';
COMMENT ON COLUMN notices.source_board IS '출처 게시판 명칭';
COMMENT ON COLUMN notices.title IS '공지 제목';
COMMENT ON COLUMN notices.category IS '공지 분야 카테고리 (학사, 취업, 장학 등)';
COMMENT ON COLUMN notices.posted_date IS '작성일/게시일';
COMMENT ON COLUMN notices.notice_url IS '공지사항 원본 연결 링크';
COMMENT ON COLUMN notices.content IS '공지사항 본문 내용';


-- 17. course_recommendations (학생별 강의 추천 결과 저장)
CREATE TABLE course_recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    offering_id INT NOT NULL REFERENCES course_offerings(offering_id) ON DELETE CASCADE,
    match_score DECIMAL(5,2) NOT NULL CHECK (match_score BETWEEN 0.0 AND 100.0),
    reason TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE course_recommendations IS '사용자 관심 분야와 졸업요건 진척도를 기반으로 생성한 AI 강의 추천 결과';
COMMENT ON COLUMN course_recommendations.recommendation_id IS '추천 결과 ID (PK)';
COMMENT ON COLUMN course_recommendations.student_id IS '추천 대상 학생 ID (FK)';
COMMENT ON COLUMN course_recommendations.offering_id IS '추천 개설 강좌 ID (FK)';
COMMENT ON COLUMN course_recommendations.match_score IS '관심사 적합성 계산 점수 (0~100)';
COMMENT ON COLUMN course_recommendations.reason IS '개설 강좌를 추천하는 사유';
COMMENT ON COLUMN course_recommendations.generated_at IS '추천 매칭 연산 수행 시점';


-- 18. chat_sessions (챗봇 대화방)
CREATE TABLE chat_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE chat_sessions IS '사용자 챗봇 대화 세션 관리 테이블';
COMMENT ON COLUMN chat_sessions.session_id IS '대화 세션 ID (PK)';
COMMENT ON COLUMN chat_sessions.user_id IS '대화 당사자 사용자 ID (FK, 1:1)';


-- 19. chat_messages (챗봇 대화 내용 기록)
CREATE TABLE chat_messages (
    message_id SERIAL PRIMARY KEY,
    session_id INT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('USER', 'ASSISTANT')),
    message_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE chat_messages IS '챗봇 세션별 사용자 질문 및 챗봇 응답 메시지 내역';
COMMENT ON COLUMN chat_messages.message_id IS '메시지 고유 ID (PK)';
COMMENT ON COLUMN chat_messages.session_id IS '소속 대화 세션 ID (FK)';
COMMENT ON COLUMN chat_messages.sender_type IS '메시지 전송자 유형 (USER: 학생 사용자, ASSISTANT: AI 비서)';
COMMENT ON COLUMN chat_messages.message_text IS '메시지 텍스트 본문';


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
