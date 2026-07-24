# app/models.py
from sqlalchemy import Column, Integer, String, Text, Float, Boolean
from app.database import Base

class CourseOffering(Base):
    __tablename__ = "course_offerings"

    offering_id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, nullable=False)
    academic_year = Column(Integer, nullable=False)
    semester = Column(String(20), nullable=False)
    section = Column(String(10))
    professor_name = Column(String(50))
    syllabus_url = Column(Text, nullable=True)

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    user_id = Column(Integer, primary_key=True, index=True)
    login_id = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="STUDENT")

class Student(Base):
    __tablename__ = "students"
    __table_args__ = {'extend_existing': True}

    student_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    student_number = Column(String(20), unique=True, nullable=False)
    admission_year = Column(Integer, nullable=False)
    current_grade = Column(Integer, nullable=False)

class Course(Base):
    __tablename__ = "courses"
    __table_args__ = {'extend_existing': True}  # 중복 정의 방지

    course_id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(50), nullable=False)
    course_name = Column(String(100), nullable=False)
    credit = Column(Float, nullable=False, default=3.0)
    theory_hours = Column(Float, nullable=True)
    practice_hours = Column(Float, nullable=True)
    course_description = Column(Text, nullable=True)
    source_url = Column(Text, nullable=False, default="")


class StudentCourseHistory(Base):
    __tablename__ = "student_course_history"
    __table_args__ = {'extend_existing': True}

    history_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, nullable=False)
    course_id = Column(Integer, nullable=False)
    semester_taken = Column(String(20), nullable=True)
    grade = Column(String(10), nullable=True)
    earned_credit = Column(Float, nullable=False, default=3.0)
    completion_status = Column(String(20), nullable=False, default="이수")
    is_retake = Column(Boolean, nullable=False, default=False)
    course_type = Column(String(50), nullable=True, default="일반선택")