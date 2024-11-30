from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, unique=True, nullable=False)
    authors = Column(JSON, nullable=False)
    abstract = Column(String)
    url = Column(String)
    pdf_path = Column(String)
    paper_metadata = Column(JSON, nullable=False)
    processed_metadata = Column(JSON)
    source = Column(String, nullable=False)
    added_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)
    organized = Column(Integer, default=0)