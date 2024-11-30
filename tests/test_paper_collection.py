import asyncio
import pytest
from pathlib import Path
from features.collection.collector import AsyncPaperManager
from features.collection.pdf_manager import AsyncPDFManager
from features.shared.database import init_db, Paper
from config.settings import Settings

async def test_paper_collection():
    # Ensure test directories exist
    for path in [Settings.DATA_DIR, Settings.PDF_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    
    # Test paper collection
    manager = AsyncPaperManager()
    total_papers = await manager.collect_all()
    print(f"Collected {total_papers} papers")
    assert total_papers > 0, "No papers were collected"
    
    # Test database storage
    session = init_db()
    papers = session.query(Paper).all()
    assert len(papers) > 0, "No papers stored in database"
    print(f"Found {len(papers)} papers in database")
    
    # Test PDF download for first paper
    pdf_manager = AsyncPDFManager()
    results = await pdf_manager.download_pdfs()
    successful_downloads = sum(1 for r in results if r)
    print(f"Downloaded {successful_downloads} PDFs")
    assert successful_downloads > 0, "No PDFs were downloaded"

if __name__ == "__main__":
    asyncio.run(test_paper_collection())