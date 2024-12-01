from datetime import datetime
import json
from typing import Dict, Union
from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, validates
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config.settings import Settings

Base = declarative_base()

# Create async engine and session maker
engine = create_async_engine(Settings.DB_URL)
AsyncSessionMaker = async_sessionmaker(engine, class_=AsyncSession)

async def init_db():
    """Initialize database and return async session"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return AsyncSessionMaker()

class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, unique=True, nullable=False)
    authors = Column(JSON, nullable=False)
    abstract = Column(String)
    url = Column(String)
    pdf_path = Column(String)
    source = Column(String, nullable=False)  # 'arxiv' or 'zotero'
    date = Column(DateTime)  # Publication date
    doi = Column(String)  # DOI if available
    journal = Column(String)  # Journal/Publication name
    paper_metadata = Column(JSON, nullable=False)  # Source-specific extra data
    processed_metadata = Column(JSON)  # For analysis results
    added_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)
    organized = Column(Integer, default=0)
    organized_paths = Column(JSON)

    @validates('paper_metadata')
    def validate_metadata(self, key: str, metadata: Union[Dict, str]) -> Dict:
        """Normalize metadata format"""
        try:
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            normalized = {}
            
            # Common fields moved to main columns, store source-specific extras here
            if self.source == 'arxiv':
                normalized.update({
                    'arxiv_id': metadata.get('arxiv_id'),
                    'categories': metadata.get('categories', []),
                    'comments': metadata.get('comments'),
                    'report_no': metadata.get('report-no')
                })
            elif self.source == 'zotero':
                normalized.update({
                    'zotero_key': metadata.get('zotero_key'),
                    'volume': metadata.get('volume'),
                    'issue': metadata.get('issue'),
                    'pages': metadata.get('pages'),
                    'tags': metadata.get('tags', [])
                })
            
            return normalized
            
        except Exception as e:
            print(f"ERROR: Metadata normalization failed: {e}")
            return {}
