import asyncio
import aiohttp
from pathlib import Path
from tqdm import tqdm
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from features.shared.database import Paper, Base  # Updated import path
from config.settings import Settings
from contextlib import asynccontextmanager

class AsyncPDFManager:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent downloads

    async def download_pdf(self, session: aiohttp.ClientSession, paper: Paper) -> Optional[str]:
        """Download PDF for paper using provided session"""
        if not paper.url:
            print(f"No URL available for paper: {paper.title[:50]}...")
            return None

        pdf_path = Settings.PDF_DIR / f"{paper.id}.pdf"
        
        try:
            async with self.semaphore:
                if paper.source == 'zotero':
                    # For Zotero papers, try to get PDF from attachment or URL
                    if paper.url.startswith('http'):
                        async with session.get(paper.url) as response:
                            if response.status == 200:
                                content = await response.read()
                                pdf_path.write_bytes(content)
                                return str(pdf_path)
                else:
                    # Handle ArXiv papers
                    async with session.get(paper.url) as response:
                        if response.status == 200:
                            content = await response.read()
                            pdf_path.write_bytes(content)
                            return str(pdf_path)
            
            print(f"Failed to download PDF for: {paper.title[:50]}...")
            return None
            
        except Exception as e:
            print(f"Error downloading PDF for {paper.title[:50]}: {e}")
            return None