from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from config.settings import Settings

Base = declarative_base()
SessionMaker = sessionmaker()

class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, unique=True, nullable=False)
    authors = Column(JSON, nullable=False)
    abstract = Column(String)
    url = Column(String)
    pdf_path = Column(String)
    paper_metadata = Column(JSON, nullable=False)
    source = Column(String, nullable=False)
    added_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)
    organized: bool = False  # Add this field to track organization status

def init_db() -> Session:
    engine = create_engine(Settings.DB_URL)
    Base.metadata.create_all(engine)
    SessionMaker.configure(bind=engine)
    return SessionMaker()