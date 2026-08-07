-- ============================================================
-- GradManager (졸업을 부탁해) - MySQL DDL
-- Generated: 2026-07-19
-- Target: AISW학과 23~24학번 + 특화/융합전공
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- -----------------------------------------------------------
-- 1. programs (전공과정)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `programs`;
CREATE TABLE `programs` (
  `program_id`          INT           NOT NULL AUTO_INCREMENT,
  `program_name`        VARCHAR(100)  NOT NULL COMMENT '전공과정명',
  `program_type`        VARCHAR(30)   NOT NULL COMMENT 'MAJOR / SPECIALIZED / CONVERGENCE',
  `required_credits`    DECIMAL(5,1)  DEFAULT NULL COMMENT '과정 필요학점',
  `effective_from_year` INT           NOT NULL COMMENT '적용 시작연도',
  `effective_to_year`   INT           DEFAULT NULL COMMENT '적용 종료연도',
  `source_url`          TEXT          NOT NULL COMMENT '공식 출처 주소',
  PRIMARY KEY (`program_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='전공과정';

-- -----------------------------------------------------------
-- 2. students (학생)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `students`;
CREATE TABLE `students` (
  `student_id`      INT          NOT NULL AUTO_INCREMENT,
  `user_id`         INT          NOT NULL COMMENT '사용자 계정 FK',
  `student_number`  VARCHAR(20)  NOT NULL COMMENT '학번',
  `admission_year`  INT          NOT NULL COMMENT '입학연도',
  `current_grade`   INT          NOT NULL COMMENT '현재 학년 (1~4)',
  PRIMARY KEY (`student_id`),
  UNIQUE KEY `uk_student_user` (`user_id`),
  UNIQUE KEY `uk_student_number` (`student_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='학생';

-- -----------------------------------------------------------
-- 3. courses (과목)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `courses`;
CREATE TABLE `courses` (
  `course_id`          INT            NOT NULL AUTO_INCREMENT,
  `course_code`        VARCHAR(30)    NOT NULL COMMENT '학수번호',
  `course_name`        VARCHAR(150)   NOT NULL COMMENT '과목명',
  `credit`             DECIMAL(3,1)   NOT NULL COMMENT '학점',
  `theory_hours`       DECIMAL(3,1)   DEFAULT NULL COMMENT '이론시간',
  `practice_hours`     DECIMAL(3,1)   DEFAULT NULL COMMENT '실습시간',
  `course_description` TEXT           DEFAULT NULL COMMENT '교과목 설명',
  `source_url`         TEXT           NOT NULL COMMENT '공식 출처 주소',
  PRIMARY KEY (`course_id`),
  UNIQUE KEY `uk_course_code` (`course_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='과목';

-- -----------------------------------------------------------
-- 4. curriculum_courses (교육과정 연결)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `curriculum_courses`;
CREATE TABLE `curriculum_courses` (
  `curriculum_course_id` INT          NOT NULL AUTO_INCREMENT,
  `curriculum_year`      INT          NOT NULL COMMENT '교육과정 적용연도',
  `course_id`            INT          NOT NULL COMMENT '과목 FK',
  `recommended_grade`    INT          DEFAULT NULL COMMENT '권장 학년',
  `semester`             VARCHAR(10)  DEFAULT NULL COMMENT '1학기 / 2학기',
  `completion_type`      VARCHAR(30)  NOT NULL COMMENT '이수구분 (전필/전선/교필/교선 등)',
  `is_required`          BOOLEAN      NOT NULL DEFAULT FALSE COMMENT '필수과목 여부',
  `note`                 TEXT         DEFAULT NULL COMMENT '비고',
  `program_id`           INT          DEFAULT NULL COMMENT '전공과정 FK',
  PRIMARY KEY (`curriculum_course_id`),
  KEY `fk_curr_course` (`course_id`),
  KEY `fk_curr_program` (`program_id`),
  CONSTRAINT `fk_curr_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`course_id`),
  CONSTRAINT `fk_curr_program` FOREIGN KEY (`program_id`) REFERENCES `programs` (`program_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='교육과정 연결';

-- -----------------------------------------------------------
-- 5. graduation_requirements (졸업요건)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `graduation_requirements`;
CREATE TABLE `graduation_requirements` (
  `requirement_id`        INT          NOT NULL AUTO_INCREMENT,
  `admission_year`        INT          NOT NULL COMMENT '적용 입학연도',
  `program_id`            INT          DEFAULT NULL COMMENT '전공과정 FK (NULL이면 공통)',
  `requirement_category`  VARCHAR(50)  NOT NULL COMMENT '총학점/교양/전공 등',
  `required_credits`      DECIMAL(6,1) DEFAULT NULL COMMENT '필요학점',
  `requirement_text`      TEXT         DEFAULT NULL COMMENT '상세조건',
  `source_url`            TEXT         NOT NULL COMMENT '공식 출처 주소',
  PRIMARY KEY (`requirement_id`),
  KEY `fk_req_program` (`program_id`),
  CONSTRAINT `fk_req_program` FOREIGN KEY (`program_id`) REFERENCES `programs` (`program_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='졸업요건';

-- -----------------------------------------------------------
-- 6. program_courses (전공과정 과목 연결)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `program_courses`;
CREATE TABLE `program_courses` (
  `program_course_id`   INT           NOT NULL AUTO_INCREMENT,
  `program_id`          INT           NOT NULL COMMENT '전공과정 FK',
  `course_id`           INT           NOT NULL COMMENT '인정과목 FK',
  `effective_year`      INT           NOT NULL COMMENT '적용연도',
  `recognition_credit`  DECIMAL(3,1)  DEFAULT NULL COMMENT '인정학점',
  `is_required`         BOOLEAN       DEFAULT NULL COMMENT '전공과정 내 필수 여부',
  `note`                TEXT          DEFAULT NULL COMMENT '비고',
  PRIMARY KEY (`program_course_id`),
  KEY `fk_pc_program` (`program_id`),
  KEY `fk_pc_course` (`course_id`),
  CONSTRAINT `fk_pc_program` FOREIGN KEY (`program_id`) REFERENCES `programs` (`program_id`),
  CONSTRAINT `fk_pc_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='전공과목 연결';

-- -----------------------------------------------------------
-- 7. course_offerings (학기별 개설강좌)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `course_offerings`;
CREATE TABLE `course_offerings` (
  `offering_id`      INT          NOT NULL AUTO_INCREMENT,
  `course_id`        INT          NOT NULL COMMENT '과목 FK',
  `academic_year`    INT          NOT NULL COMMENT '개설연도',
  `semester`         VARCHAR(10)  NOT NULL COMMENT '1학기 / 2학기',
  `section`          VARCHAR(20)  NOT NULL COMMENT '분반',
  `professor_name`   VARCHAR(100) DEFAULT NULL COMMENT '담당교수',
  `syllabus_url`     TEXT         DEFAULT NULL COMMENT '강의계획서 주소',
  PRIMARY KEY (`offering_id`),
  UNIQUE KEY `uk_offering` (`course_id`, `academic_year`, `semester`, `section`),
  KEY `fk_offering_course` (`course_id`),
  CONSTRAINT `fk_offering_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='학기별 개설강좌';

-- -----------------------------------------------------------
-- 8. course_schedules (강의시간)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `course_schedules`;
CREATE TABLE `course_schedules` (
  `schedule_id`   INT          NOT NULL AUTO_INCREMENT,
  `offering_id`   INT          NOT NULL COMMENT '개설강좌 FK',
  `day_of_week`   VARCHAR(10)  NOT NULL COMMENT '월/화/수/목/금',
  `start_time`    TIME         NOT NULL COMMENT '시작시간',
  `end_time`      TIME         NOT NULL COMMENT '종료시간',
  `classroom`     VARCHAR(100) DEFAULT NULL COMMENT '강의실',
  PRIMARY KEY (`schedule_id`),
  KEY `fk_sched_offering` (`offering_id`),
  CONSTRAINT `fk_sched_offering` FOREIGN KEY (`offering_id`) REFERENCES `course_offerings` (`offering_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='강의시간';

-- -----------------------------------------------------------
-- 9. course_keywords (과목 키워드)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `course_keywords`;
CREATE TABLE `course_keywords` (
  `keyword_id`         INT            NOT NULL AUTO_INCREMENT,
  `offering_id`        INT            NOT NULL COMMENT '개설강좌 FK',
  `keyword`            VARCHAR(100)   NOT NULL COMMENT '추출 키워드',
  `keyword_source`     VARCHAR(20)    NOT NULL COMMENT 'AI 또는 USER',
  `confidence_score`   DECIMAL(5,2)   DEFAULT NULL COMMENT 'AI 키워드 신뢰도 (0~100)',
  `keyword_category`   VARCHAR(50)    DEFAULT NULL COMMENT '키워드 분야',
  `weight`             DECIMAL(5,2)   DEFAULT NULL COMMENT '키워드 중요도',
  `source_text`        TEXT           DEFAULT NULL COMMENT '키워드 추출 근거',
  PRIMARY KEY (`keyword_id`),
  KEY `fk_kw_offering` (`offering_id`),
  CONSTRAINT `fk_kw_offering` FOREIGN KEY (`offering_id`) REFERENCES `course_offerings` (`offering_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='과목 키워드';

-- -----------------------------------------------------------
-- 10. student_course_history (이수내역)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `student_course_history`;
CREATE TABLE `student_course_history` (
  `history_id`            INT           NOT NULL AUTO_INCREMENT,
  `student_id`            INT           NOT NULL COMMENT '학생 FK',
  `course_id`             INT           NOT NULL COMMENT '과목 FK',
  `academic_year`         INT           DEFAULT NULL COMMENT '이수연도',
  `semester`              VARCHAR(10)   DEFAULT NULL COMMENT '이수학기',
  `earned_credit`         DECIMAL(3,1)  NOT NULL COMMENT '취득학점',
  `completion_status`     VARCHAR(20)   NOT NULL COMMENT '이수/미이수',
  `is_retake`             BOOLEAN       NOT NULL DEFAULT FALSE COMMENT '재수강 여부',
  `attempt_no`            INT           NOT NULL DEFAULT 1 COMMENT '수강 시도 횟수',
  `original_history_id`   INT           DEFAULT NULL COMMENT '최초 이수내역 FK',
  `credit_counted`        BOOLEAN       NOT NULL DEFAULT TRUE COMMENT '졸업학점 반영 여부',
  PRIMARY KEY (`history_id`),
  KEY `fk_hist_student` (`student_id`),
  KEY `fk_hist_course` (`course_id`),
  KEY `fk_hist_original` (`original_history_id`),
  CONSTRAINT `fk_hist_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  CONSTRAINT `fk_hist_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`course_id`),
  CONSTRAINT `fk_hist_original` FOREIGN KEY (`original_history_id`) REFERENCES `student_course_history` (`history_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='이수내역';

-- -----------------------------------------------------------
-- 11. academic_events (학사일정)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `academic_events`;
CREATE TABLE `academic_events` (
  `event_id`       INT          NOT NULL AUTO_INCREMENT,
  `academic_year`  INT          NOT NULL COMMENT '학년도',
  `semester`       VARCHAR(10)  DEFAULT NULL COMMENT '학기',
  `event_name`     VARCHAR(200) NOT NULL COMMENT '일정명',
  `event_type`     VARCHAR(50)  NOT NULL COMMENT 'TUITION_PAYMENT/PRE_REGISTRATION/COURSE_REGISTRATION/FINAL_COURSE_EVALUATION 등',
  `start_date`     DATE         NOT NULL COMMENT '시작일',
  `end_date`       DATE         DEFAULT NULL COMMENT '종료일',
  `is_mandatory`   BOOLEAN      DEFAULT FALSE COMMENT '필수 일정 여부',
  `description`    TEXT         DEFAULT NULL COMMENT '일정 상세내용',
  `source_url`     TEXT         NOT NULL COMMENT '공식 출처 주소',
  PRIMARY KEY (`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='학사일정';

-- -----------------------------------------------------------
-- 12. notices (공지사항)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `notices`;
CREATE TABLE `notices` (
  `notice_id`     INT          NOT NULL AUTO_INCREMENT,
  `source_board`  VARCHAR(100) NOT NULL COMMENT '공지사항 게시판',
  `title`         VARCHAR(300) NOT NULL COMMENT '공지 제목',
  `category`      VARCHAR(50)  DEFAULT NULL COMMENT '학사/장학/취업/행사 등',
  `posted_date`   DATE         NOT NULL COMMENT '게시일',
  `notice_url`    TEXT         NOT NULL COMMENT '공지 주소',
  `content`       TEXT         DEFAULT NULL COMMENT '공지 내용',
  PRIMARY KEY (`notice_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='공지사항';

-- -----------------------------------------------------------
-- 13. users (사용자 계정)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `user_id`        INT          NOT NULL AUTO_INCREMENT,
  `login_id`       VARCHAR(50)  NOT NULL COMMENT '로그인 아이디',
  `password_hash`  VARCHAR(255) NOT NULL COMMENT '암호화된 비밀번호',
  `role`           VARCHAR(20)  NOT NULL COMMENT 'STUDENT / ADMIN',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_login_id` (`login_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='사용자 계정';

-- -----------------------------------------------------------
-- 14. student_programs (학생 전공과정 연결)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `student_programs`;
CREATE TABLE `student_programs` (
  `student_program_id`  INT          NOT NULL AUTO_INCREMENT,
  `student_id`          INT          NOT NULL COMMENT '학생 FK',
  `program_id`          INT          NOT NULL COMMENT '전공과정 FK',
  `program_role`        VARCHAR(20)  NOT NULL COMMENT 'PRIMARY / ADDITIONAL',
  `selected_year`       INT          DEFAULT NULL COMMENT '특화/융합전공 선택연도',
  `completion_status`   VARCHAR(20)  DEFAULT NULL COMMENT '이수중/충족/미충족',
  `created_at`          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일시',
  PRIMARY KEY (`student_program_id`),
  KEY `fk_sp_student` (`student_id`),
  KEY `fk_sp_program` (`program_id`),
  CONSTRAINT `fk_sp_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  CONSTRAINT `fk_sp_program` FOREIGN KEY (`program_id`) REFERENCES `programs` (`program_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='학생 전공과정 연결';

-- -----------------------------------------------------------
-- 15. user_interests (관심분야)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `user_interests`;
CREATE TABLE `user_interests` (
  `user_interest_id`  INT          NOT NULL AUTO_INCREMENT,
  `user_id`           INT          NOT NULL COMMENT '사용자 FK',
  `interest_type`     VARCHAR(30)  NOT NULL COMMENT 'COURSE / EVENT',
  `keyword`           VARCHAR(100) NOT NULL COMMENT '사용자가 선택한 키워드',
  `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '관심분야 선택일시',
  PRIMARY KEY (`user_interest_id`),
  UNIQUE KEY `uk_interest` (`user_id`, `interest_type`, `keyword`),
  KEY `fk_ui_user` (`user_id`),
  CONSTRAINT `fk_ui_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='관심분야';

-- -----------------------------------------------------------
-- 16. course_recommendations (과목 추천 결과)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `course_recommendations`;
CREATE TABLE `course_recommendations` (
  `recommendation_id`  INT           NOT NULL AUTO_INCREMENT,
  `student_id`         INT           NOT NULL COMMENT '학생 FK',
  `offering_id`        INT           NOT NULL COMMENT '개설강좌 FK',
  `match_score`        DECIMAL(5,2)  NOT NULL COMMENT '관심사 적합도 (0~100)',
  `reason`             TEXT          DEFAULT NULL COMMENT '추천 이유',
  `generated_at`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '추천 생성일시',
  PRIMARY KEY (`recommendation_id`),
  KEY `fk_rec_student` (`student_id`),
  KEY `fk_rec_offering` (`offering_id`),
  CONSTRAINT `fk_rec_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  CONSTRAINT `fk_rec_offering` FOREIGN KEY (`offering_id`) REFERENCES `course_offerings` (`offering_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='과목 추천 결과';

-- -----------------------------------------------------------
-- 17. chat_sessions (챗봇 대화방)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `chat_sessions`;
CREATE TABLE `chat_sessions` (
  `session_id`  INT      NOT NULL AUTO_INCREMENT,
  `user_id`     INT      NOT NULL COMMENT '사용자 FK',
  `created_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '대화 시작일시',
  `updated_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '최근 대화일시',
  PRIMARY KEY (`session_id`),
  UNIQUE KEY `uk_session_user` (`user_id`),
  KEY `fk_cs_user` (`user_id`),
  CONSTRAINT `fk_cs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='챗봇 대화방';

-- -----------------------------------------------------------
-- 18. chat_messages (챗봇 메시지)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `chat_messages`;
CREATE TABLE `chat_messages` (
  `message_id`    INT          NOT NULL AUTO_INCREMENT,
  `session_id`    INT          NOT NULL COMMENT '대화방 FK',
  `sender_type`   VARCHAR(20)  NOT NULL COMMENT 'USER / ASSISTANT',
  `message_text`  TEXT         NOT NULL COMMENT '메시지 내용',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '메시지 전송일시',
  PRIMARY KEY (`message_id`),
  KEY `fk_cm_session` (`session_id`),
  CONSTRAINT `fk_cm_session` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='챗봇 메시지';

-- -----------------------------------------------------------
-- 19. program_policies (전공과정 정책)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `program_policies`;
CREATE TABLE `program_policies` (
  `policy_id`       INT          NOT NULL AUTO_INCREMENT,
  `program_id`      INT          NOT NULL COMMENT '전공과정 FK',
  `policy_name`     VARCHAR(100) NOT NULL COMMENT '정책명',
  `policy_text`     TEXT         NOT NULL COMMENT '정책 내용',
  `effective_year`  INT          DEFAULT NULL COMMENT '적용연도',
  PRIMARY KEY (`policy_id`),
  KEY `fk_pp_program` (`program_id`),
  CONSTRAINT `fk_pp_program` FOREIGN KEY (`program_id`) REFERENCES `programs` (`program_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='전공과정 정책';

-- -----------------------------------------------------------
-- 20. program_scholarships (전공과정 장학금)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `program_scholarships`;
CREATE TABLE `program_scholarships` (
  `scholarship_id`    INT          NOT NULL AUTO_INCREMENT,
  `program_id`        INT          NOT NULL COMMENT '전공과정 FK',
  `scholarship_name`  VARCHAR(100) NOT NULL COMMENT '장학금명',
  `description`       TEXT         DEFAULT NULL COMMENT '장학금 설명',
  `amount`            VARCHAR(50)  DEFAULT NULL COMMENT '장학금액',
  `criteria`          TEXT         DEFAULT NULL COMMENT '선발기준',
  PRIMARY KEY (`scholarship_id`),
  KEY `fk_ps_program` (`program_id`),
  CONSTRAINT `fk_ps_program` FOREIGN KEY (`program_id`) REFERENCES `programs` (`program_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='전공과정 장학금';

-- -----------------------------------------------------------
-- 21. course_equivalencies (과목 동일인정)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `course_equivalencies`;
CREATE TABLE `course_equivalencies` (
  `equivalence_id`      INT          NOT NULL AUTO_INCREMENT,
  `primary_course_id`   INT          NOT NULL COMMENT '대표과목 FK',
  `equivalent_course_id` INT         NOT NULL COMMENT '동일과목 FK',
  `program_id`          INT          DEFAULT NULL COMMENT '전공과정 FK (NULL이면 공통)',
  `note`                TEXT         DEFAULT NULL COMMENT '비고',
  PRIMARY KEY (`equivalence_id`),
  KEY `fk_eq_primary` (`primary_course_id`),
  KEY `fk_eq_equiv` (`equivalent_course_id`),
  KEY `fk_eq_program` (`program_id`),
  CONSTRAINT `fk_eq_primary` FOREIGN KEY (`primary_course_id`) REFERENCES `courses` (`course_id`),
  CONSTRAINT `fk_eq_equiv` FOREIGN KEY (`equivalent_course_id`) REFERENCES `courses` (`course_id`),
  CONSTRAINT `fk_eq_program` FOREIGN KEY (`program_id`) REFERENCES `programs` (`program_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='과목 동일인정';

-- -----------------------------------------------------------
-- 22. course_relationships (과목 이수흐름)
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `course_relationships`;
CREATE TABLE `course_relationships` (
  `relationship_id`   INT          NOT NULL AUTO_INCREMENT,
  `from_course_id`    INT          NOT NULL COMMENT '선행과목 FK',
  `to_course_id`      INT          NOT NULL COMMENT '후속과목 FK',
  `relationship_type` VARCHAR(30)  NOT NULL COMMENT 'PREREQUISITE / COREQUISITE / SEQUENCE',
  `program_id`        INT          DEFAULT NULL COMMENT '전공과정 FK (NULL이면 공통)',
  `note`              TEXT         DEFAULT NULL COMMENT '비고',
  PRIMARY KEY (`relationship_id`),
  KEY `fk_cr_from` (`from_course_id`),
  KEY `fk_cr_to` (`to_course_id`),
  KEY `fk_cr_program` (`program_id`),
  CONSTRAINT `fk_cr_from` FOREIGN KEY (`from_course_id`) REFERENCES `courses` (`course_id`),
  CONSTRAINT `fk_cr_to` FOREIGN KEY (`to_course_id`) REFERENCES `courses` (`course_id`),
  CONSTRAINT `fk_cr_program` FOREIGN KEY (`program_id`) REFERENCES `programs` (`program_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='과목 이수흐름';

SET FOREIGN_KEY_CHECKS = 1;
