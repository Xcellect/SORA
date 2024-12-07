import asyncio
import argparse
import shutil
from pathlib import Path
import aiohttp
from tqdm import tqdm
from typing import List
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

# Feature imports
from features.collection import AsyncPaperManager, AsyncPDFManager
from features.organization import PaperOrganizer
from features.shared.database import Base, Paper, init_db
from config.settings import Settings

# Create async session maker
engine = create_async_engine(Settings.DB_URL)
AsyncSessionMaker = async_sessionmaker(engine, class_=AsyncSession)

async def flush_pdfs():
    """Delete all PDFs and reset processed status in database"""
    # Clear PDF directory
    if Settings.PDF_DIR.exists():
        shutil.rmtree(Settings.PDF_DIR)
        Settings.PDF_DIR.mkdir(parents=True)
        print("Cleared PDF directory")
    
    # Reset database
    async with AsyncSessionMaker() as session:
        try:
            stmt = delete(Paper)
            result = await session.execute(stmt)
            await session.commit()
            print("Deleted all papers from database")
        except Exception as e:
            await session.rollback()
            print(f"Error resetting database: {e}")

async def download_with_progress(pdf_manager: AsyncPDFManager, papers: List[Paper]):
    """Download PDFs with progress bar"""
    if not papers:
        return
    
    print(f"\nDownloading {len(papers)} PDFs...")
    progress = tqdm(total=len(papers), desc="Downloading PDFs")
    
    async def download_and_update(paper: Paper, session: aiohttp.ClientSession):
        try:
            result = await pdf_manager.download_pdf(session, paper)
            if result:
                async with AsyncSessionMaker() as db_session:
                    paper.pdf_path = result
                    paper.processed = 1
                    merged_paper = await db_session.merge(paper)
                    await db_session.commit()
            progress.update(1)
            return result
        except Exception as e:
            print(f"\nError downloading {paper.title[:50]}: {e}")
            progress.update(1)
            return None

    async with aiohttp.ClientSession() as session:
        tasks = [download_and_update(paper, session) for paper in papers]
        results = await asyncio.gather(*tasks)
    
    progress.close()
    return results

async def sync_db():
    """Sync database with PDF files"""
    print("Syncing database with PDF files...")
    
    async with AsyncSessionMaker() as session:
        try:
            # Create tables if they don't exist
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Get all papers marked as processed
            result = await session.execute(
                Paper.__table__.select().where(Paper.processed == 1)
            )
            processed_papers = result.fetchall()
            
            updates = 0
            for paper in tqdm(processed_papers, desc="Checking PDFs"):
                if paper.pdf_path:
                    pdf_exists = Path(paper.pdf_path).exists()
                    if not pdf_exists:
                        paper.processed = 0
                        paper.pdf_path = None
                        updates += 1
                        session.add(paper)
            
            await session.commit()
            print(f"Reset {updates} papers that were missing PDF files")
            
        except Exception as e:
            await session.rollback()
            print(f"Error syncing database: {e}")

async def export_db():
    """Export database contents to CSV"""
    print("Exporting database to CSV...")
    try:
        import pandas as pd
        
        async with AsyncSessionMaker() as session:
            # Use select statement instead of query
            result = await session.execute(
                select(Paper)
            )
            papers = result.scalars().all()
            
            # Convert to list of dicts for DataFrame
            paper_data = []
            for paper in papers:
                paper_dict = {
                    'id': paper.id,
                    'title': paper.title,
                    'authors': ', '.join(paper.authors) if isinstance(paper.authors, list) else paper.authors,
                    'abstract': paper.abstract,
                    'url': paper.url,
                    'source': paper.source,
                    'date': paper.date,
                    'doi': paper.doi,
                    'journal': paper.journal,
                    'pdf_path': paper.pdf_path,
                    'processed': paper.processed,
                    'organized': paper.organized
                }
                
                # Add metadata if available
                if paper.paper_metadata:
                    for key, value in paper.paper_metadata.items():
                        paper_dict[f'metadata_{key}'] = str(value)
                
                paper_data.append(paper_dict)
            
            # Create DataFrame and export
            df = pd.DataFrame(paper_data)
            export_path = Settings.DATA_DIR / 'papers_export.csv'
            df.to_csv(export_path, index=False)
            print(f"Exported {len(paper_data)} papers to {export_path}")
            
    except Exception as e:
        print(f"Error exporting database: {e}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")

async def view_db():
    """View database contents"""
    try:
        async with AsyncSessionMaker() as session:
            result = await session.execute(
                select(Paper).order_by(Paper.id)
            )
            papers = result.scalars().all()
            
            if not papers:
                print("No papers in database")
                return
                
            print("\nDatabase contents:")
            print("-" * 80)
            for paper in papers:
                print(f"ID: {paper.id}")
                print(f"Title: {paper.title[:100]}...")
                print(f"Source: {paper.source}")
                print(f"Processed: {paper.processed}")
                print(f"Organized: {paper.organized}")
                print("-" * 80)
            
            print(f"\nTotal papers: {len(papers)}")
            
    except Exception as e:
        print(f"Error viewing database: {e}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")

async def organize_papers(source: str = None):
    """Organize papers and create knowledge management structure"""
    print("Starting paper organization...")
    organizer = PaperOrganizer(Settings.BASE_DIR)
    
    async with AsyncSessionMaker() as session:
        try:
            # Get unorganized papers that have been processed (PDFs downloaded)
            query = select(Paper).where(
                Paper.processed == 1,
                Paper.organized == 0
            )
            
            # Add source filter if specified
            if source:
                query = query.where(Paper.source == source)
                
            result = await session.execute(query)
            papers = result.scalars().all()
            
            if not papers:
                print(f"No new papers to organize{f' from {source}' if source else ''}")
                return
            
            print(f"Organizing {len(papers)} papers{f' from {source}' if source else ''}...")
            progress_bar = tqdm(total=len(papers), desc="Organizing papers")
            
            for paper in papers:
                try:
                    result = await organizer.organize_paper(paper)
                    if result['status'] == 'organized':
                        paper.organized = 1
                        paper.organized_paths = result['paths']
                        session.add(paper)
                    progress_bar.update(1)
                except Exception as e:
                    print(f"\nError organizing paper {paper.title}: {e}")
            
            await session.commit()
            progress_bar.close()
            print("\nPaper organization complete")
            
        except Exception as e:
            await session.rollback()
            print(f"Error during organization: {e}")


async def flush_organization():
    """Delete all organization-related files and directories"""
    paths_to_flush = [
        Settings.BASE_DIR / "notes",
        Settings.BASE_DIR / "papers" / "by_year",
        Settings.BASE_DIR / "papers" / "metadata"
    ]
    
    for path in paths_to_flush:
        if path.exists():
            shutil.rmtree(path)
            path.mkdir(parents=True)
            print(f"Cleared {path}")

async def main():
    parser = argparse.ArgumentParser(description='Collect and organize research papers')
    parser.add_argument('--force', action='store_true',
                       help='Overwrite existing papers with same titles')
    parser.add_argument('--get', type=int, default=None,
                       help='Number of papers to collect')
    parser.add_argument('--source', choices=['arxiv', 'zotero'], default='arxiv',
                       help='Source to collect papers from (default: arxiv)')
    parser.add_argument('--flush', action='store_true',
                       help='Delete all downloaded PDFs and reset processed status')
    parser.add_argument('--sync', action='store_true',
                       help='Sync database with actual PDF files')
    parser.add_argument('--export', action='store_true',
                       help='Export database contents to CSV')
    parser.add_argument('--view', action='store_true',
                       help='View database contents')
    parser.add_argument('--organize', type=int, default=None,
                       help='Collect and organize specified number of papers')
    parser.add_argument('--organize-only', action='store_true',
                       help='Only organize papers without collecting new ones')
    parser.add_argument('--flush-org', action='store_true',
                       help='Flush organization directories (notes, by_year, metadata)')
    
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
        await sync_db()
        return
    
    if args.organize_only:
        await organize_papers(source=args.source)  # Pass source to organize_papers
        return
    
    if args.flush_org:
        await flush_organization()
        return
    
    # Update Settings
    Settings.FORCE_UPDATE = args.force
    
    # Ensure directories exist
    for path in [Settings.DATA_DIR, Settings.PDF_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    
    # Initialize managers
    paper_manager = AsyncPaperManager()
    await paper_manager.initialize()
    pdf_manager = AsyncPDFManager()
    
    # Handle paper collection and organization
    if args.get is not None or args.organize is not None:
        papers_to_get = args.get if args.get is not None else args.organize
        Settings.PAPERS_PER_CATEGORY = papers_to_get
        
        # Collect papers from specified source
        print(f"Collecting {papers_to_get} papers from {args.source}...")
        total_papers, new_papers = await paper_manager.collect_all(source=args.source)
        print(f"Successfully collected {total_papers} papers")
        
        # Download PDFs with progress bar (only for new papers)
        await download_with_progress(pdf_manager, new_papers)
        
        # Organize if requested
        if args.organize is not None:
            await organize_papers(source=args.source)

if __name__ == "__main__":
    asyncio.run(main())