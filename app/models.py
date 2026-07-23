# app/models.py
from sqlalchemy import Column, Integer, String, Text
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
    # app/models.py 맨 아래에 추가

# app/models.py 맨 아래쪽

class Course(Base):
    __tablename__ = "courses"
    __table_args__ = {'extend_existing': True}  # 중복 정의 방지

    course_id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(50))
    course_name = Column(String(100))


class StudentCourseHistory(Base):
    __tablename__ = "student_course_history"
    __table_args__ = {'extend_existing': True}

    history_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=False)
    course_id = Column(Integer, nullable=False)
    semester_taken = Column(String(20), nullable=True)
    grade = Column(String(10), nullable=True)