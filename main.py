import asyncio
import argparse
import shutil
from pathlib import Path
from tqdm import tqdm
from typing import List

# Feature imports
from features.collection import AsyncPaperManager, AsyncPDFManager
from features.organization import PaperOrganizer
from features.shared.database import init_db, Paper
from config.settings import Settings

async def flush_pdfs():
    """Delete all PDFs and reset processed status in database"""
    # Clear PDF directory
    if Settings.PDF_DIR.exists():
        shutil.rmtree(Settings.PDF_DIR)
        Settings.PDF_DIR.mkdir(parents=True)
        print("Cleared PDF directory")
    
    # Reset database
    session = init_db()
    try:
        # Delete all existing records
        deleted = session.query(Paper).delete()
        session.commit()
        print(f"Deleted {deleted} papers from database")
    except Exception as e:
        session.rollback()
        print(f"Error resetting database: {e}")
    finally:
        session.close()

async def download_with_progress(pdf_manager: AsyncPDFManager, papers: List[Paper]):
    """Download PDFs with progress bar"""
    if not papers:
        print("No new papers to download")
        return
    
    print(f"\nDownloading {len(papers)} PDFs...")
    progress_bar = tqdm(total=len(papers), desc="Downloading PDFs")
    
    # Create a new session and refresh paper objects
    db_session = pdf_manager.SessionMaker()
    try:
        # Refresh papers in the session
        papers_to_download = []
        for paper in papers:
            merged_paper = db_session.merge(paper)
            if merged_paper.url:  # Check URL after merging
                papers_to_download.append(merged_paper)
        
        async def download_and_update(aio_session, paper):
            result = await pdf_manager.download_pdf(aio_session, paper)
            progress_bar.update(1)
            return result
        
        async with pdf_manager.get_session() as aio_session:
            tasks = [
                download_and_update(aio_session, paper)
                for paper in papers_to_download
            ]
            
            results = await asyncio.gather(*tasks)
            successful = sum(1 for r in results if r)
        
        progress_bar.close()
        print(f"\nSuccessfully downloaded {successful} PDFs")
    finally:
        db_session.close()

async def sync_db():
    """Sync database with actual PDF files"""
    print("Syncing database with PDF files...")
    session = init_db()
    try:
        # Get all papers marked as processed
        processed_papers = session.query(Paper).filter(Paper.processed == 1).all()
        
        updates = 0
        for paper in tqdm(processed_papers, desc="Checking PDFs"):
            if paper.pdf_path:
                pdf_exists = Path(paper.pdf_path).exists()
                if not pdf_exists:
                    paper.processed = 0
                    paper.pdf_path = None
                    updates += 1
        
        session.commit()
        print(f"Reset {updates} papers that were missing PDF files")
        
    except Exception as e:
        session.rollback()
        print(f"Error syncing database: {e}")
    finally:
        session.close()

async def export_db():
    """Export database contents to CSV"""
    import pandas as pd
    print("Exporting database to CSV...")
    session = init_db()
    try:
        # Get all papers
        papers = session.query(Paper).all()
        
        # Convert to list of dicts with safe attribute access
        paper_data = []
        for p in papers:
            paper_dict = {
                'id': p.id,
                'title': p.title,
                'authors': p.authors,
                'abstract': p.abstract,
                'url': p.url,
                'pdf_path': p.pdf_path,
                'processed': p.processed,
                'organized': p.organized if hasattr(p, 'organized') else 0
            }
            # Safely add metadata fields
            if hasattr(p, 'processed_metadata'):
                paper_dict['metadata'] = p.processed_metadata
            if hasattr(p, 'date_added'):
                paper_dict['date_added'] = p.date_added
                
            paper_data.append(paper_dict)
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(paper_data)
        csv_path = Settings.DATA_DIR / 'papers.csv'
        df.to_csv(csv_path, index=False)
        print(f"Exported {len(papers)} papers to {csv_path}")
        
    except Exception as e:
        print(f"Error exporting database: {e}")
    finally:
        session.close()

async def view_db():
    """View database contents"""
    session = init_db()
    try:
        # Get all papers
        papers = session.query(Paper).all()
        
        print(f"\nTotal papers in database: {len(papers)}")
        print("\nLatest 10 papers:")
        print("-" * 80)
        
        for paper in papers[-10:]:
            print(f"Title: {paper.title[:70]}...")
            print(f"Authors: {paper.authors[:70]}...")
            print(f"Has PDF: {'Yes' if paper.pdf_path and Path(paper.pdf_path).exists() else 'No'}")
            print(f"Organized: {'Yes' if getattr(paper, 'organized', 0) == 1 else 'No'}")
            print("-" * 80)
        
    except Exception as e:
        print(f"Error viewing database: {e}")
    finally:
        session.close()

async def organize_papers():
    """Organize papers and create knowledge management structure"""
    print("Starting paper organization...")
    organizer = PaperOrganizer(Settings.BASE_DIR)
    session = init_db()
    
    try:
        # Get unorganized papers that have been processed (PDFs downloaded)
        papers = session.query(Paper).filter_by(
            processed=1, 
            organized=0
        ).all()
        
        if not papers:
            print("No new papers to organize")
            return
        
        print(f"Organizing {len(papers)} papers...")
        progress_bar = tqdm(total=len(papers), desc="Organizing papers")
        
        for paper in papers:
            try:
                metadata = await organizer.organize_paper(paper)
                paper.processed_metadata = metadata
                paper.organized = 1
                session.merge(paper)
                progress_bar.update(1)
            except Exception as e:
                print(f"\nError organizing paper {paper.title}: {e}")
        
        session.commit()
        progress_bar.close()
        print("\nPaper organization complete")
        
    except Exception as e:
        session.rollback()
        print(f"Error during organization: {e}")
    finally:
        session.close()

async def main():
    parser = argparse.ArgumentParser(description='Collect and organize research papers')
    parser.add_argument('--force', action='store_true',
                       help='Overwrite existing papers with same titles')
    parser.add_argument('--papers-per-category', type=int, default=100,
                       help='Number of papers to collect per category (default: 100)')
    parser.add_argument('--flush', action='store_true',
                       help='Delete all downloaded PDFs and reset processed status')
    parser.add_argument('--sync', action='store_true',
                       help='Sync database with actual PDF files')
    parser.add_argument('--export', action='store_true',
                       help='Export database contents to CSV')
    parser.add_argument('--view', action='store_true',
                       help='View database contents')
    parser.add_argument('--organize', action='store_true',
                       help='Organize collected papers')
    parser.add_argument('--organize-only', action='store_true',
                       help='Only organize papers without collecting new ones')
    args = parser.parse_args()
    
    if args.export:
        await export_db()
        return
    
    if args.view:
        await view_db()
        return
    
    if args.sync:
        await sync_db()
        return
    
    if args.flush:
        await flush_pdfs()
        await sync_db()  # Add sync after flush
        return
    
    if args.organize_only:
        await organize_papers()
        return
    
    # Update Settings
    Settings.PAPERS_PER_CATEGORY = args.papers_per_category
    Settings.FORCE_UPDATE = args.force
    
    # Ensure directories exist
    for path in [Settings.DATA_DIR, Settings.PDF_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    
    # Initialize managers
    paper_manager = AsyncPaperManager()
    pdf_manager = AsyncPDFManager()
    
    # Collect papers
    print(f"Collecting papers from arXiv ({args.papers_per_category} per category) and Zotero...")
    total_papers, new_papers = await paper_manager.collect_all()
    print(f"Successfully collected {total_papers} papers")
    
    # Download PDFs with progress bar (only for new papers)
    await download_with_progress(pdf_manager, new_papers)
    
    # Organize papers if requested
    if args.organize:
        await organize_papers()

if __name__ == "__main__":
    asyncio.run(main())