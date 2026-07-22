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