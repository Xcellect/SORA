import asyncio
import aiohttp
from pathlib import Path
from tqdm import tqdm
from typing import List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from features.shared.database import Paper, Base  # Updated import path
from config.settings import Settings
from contextlib import asynccontextmanager

class AsyncPDFManager:
    def __init__(self):
        self.engine = create_engine(Settings.DB_URL)
        self.SessionMaker = sessionmaker(bind=self.engine)
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent downloads
    
    @asynccontextmanager
    async def get_session(self):
        """Create aiohttp session context manager"""
        async with aiohttp.ClientSession() as session:
            yield session
    
    async def download_pdf(self, aio_session: aiohttp.ClientSession, paper: Paper) -> bool:
        """Download a single PDF file"""
        async with self.semaphore:
            try:
                pdf_path = Settings.PDF_DIR / f"{paper.id}.pdf"
                async with aio_session.get(paper.url) as response:
                    if response.status == 200:
                        content = await response.read()
                        pdf_path.write_bytes(content)
                        
                        # Update paper in database
                        db_session = self.SessionMaker()
                        try:
                            paper.pdf_path = str(pdf_path)
                            paper.processed = 1
                            db_session.merge(paper)
                            db_session.commit()
                            return True
                        except Exception as e:
                            print(f"Error updating database for {paper.title}: {e}")
                            db_session.rollback()
                            return False
                        finally:
                            db_session.close()
                return False
            except Exception as e:
                print(f"Error downloading PDF for {paper.title}: {e}")
                return False