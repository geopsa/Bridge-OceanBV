# models.py
from sqlalchemy import Column, Integer, String, Text
from database import Base

class JobListing(Base):
    __tablename__ = "job_listing"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    busy = Column(String(256), nullable=False)
    time_publication = Column(Integer, nullable=False)
    how_many_people = Column(Integer, nullable=False)
    salary = Column(Text, nullable=False)
    favorites = Column(Text, nullable=False)
    question = Column(Text, nullable=False)