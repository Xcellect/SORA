import arxiv
from pyzotero import zotero
import asyncio
from tqdm import tqdm
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from features.shared.database import Paper, Base
from config.settings import Settings
from typing import List
from contextlib import asynccontextmanager
from pathlib import Path
class PaperCollector:
    def __init__(self):
        self.engine = create_engine(Settings.DB_URL)
        self.SessionMaker = sessionmaker(bind=self.engine)
        self.session = self.SessionMaker()
        self.zot = zotero.Zotero(
            Settings.ZOTERO_LIBRARY_ID,
            Settings.ZOTERO_LIBRARY_TYPE,
            Settings.ZOTERO_API_KEY
        )
    
    async def collect_from_arxiv(self) -> List[Paper]:
        collected = []
        for category in Settings.ARXIV_CATEGORIES:
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=Settings.PAPERS_PER_CATEGORY,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            for result in tqdm(search.results(), desc=f"Collecting {category}"):
                paper = Paper(
                    title=result.title,
                    authors=[str(a) for a in result.authors],
                    abstract=result.summary,
                    url=result.pdf_url,
                    source='arxiv',
                    paper_metadata={
                        'arxiv_id': result.entry_id,
                        'categories': result.categories,
                        'published': str(result.published)
                    }
                )
                collected.append(paper)
                await self.add_to_zotero(paper)
        
        return collected
    
    async def collect_from_zotero(self) -> List[Paper]:
        collected = []
        items = await asyncio.to_thread(self.zot.top, limit=100)
        
        for item in tqdm(items, desc="Collecting from Zotero"):
            if item['data']['itemType'] == 'journalArticle':
                paper = Paper(
                    title=item['data'].get('title'),
                    authors=item['data'].get('creators', []),
                    abstract=item['data'].get('abstractNote'),
                    url=item['data'].get('url'),
                    source='zotero',
                    paper_metadata={
                        'zotero_key': item['key'],
                        'date': item['data'].get('date'),
                        'doi': item['data'].get('DOI'),
                        'tags': item['data'].get('tags', [])
                    }
                )
                collected.append(paper)
        
        return collected
    
    async def add_to_zotero(self, paper: Paper) -> None:
        template = {
            'itemType': 'journalArticle',
            'title': paper.title,
            'creators': [{'creatorType': 'author', 'name': author} 
                        for author in paper.authors],
            'abstractNote': paper.abstract,
            'url': paper.url,
            'tags': [{'tag': 'AI Research'}]
        }
        
        if paper.paper_metadata.get('categories'):
            template['tags'].append({'tag': paper.paper_metadata['categories'][0]})
        
        try:
            await asyncio.to_thread(self.zot.create_items, [template])
        except Exception as e:
            print(f"Error adding to Zotero: {e}")


class AsyncPaperManager:
    def __init__(self):
        self.collector = PaperCollector()
        self.engine = create_engine(Settings.DB_URL)
        Base.metadata.create_all(self.engine)
        self.SessionMaker = sessionmaker(bind=self.engine)
    
    @asynccontextmanager
    async def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.SessionMaker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def get_existing_papers(self) -> dict:
        """Get dict of papers with their processing status"""
        async with self.session_scope() as session:
            papers = session.query(Paper).all()
            return {
                paper.title: {
                    'has_pdf': bool(paper.pdf_path and Path(paper.pdf_path).exists()),
                    'processed': paper.processed
                }
                for paper in papers
            }
    
    async def store_papers(self, papers: List[Paper], existing_papers: dict) -> List[Paper]:
        stored_papers = []
        async with self.session_scope() as session:
            for paper in papers:
                try:
                    paper_status = existing_papers.get(paper.title)
                    
                    # Add paper if it's new or if it exists but has no PDF
                    if not paper_status or not paper_status['has_pdf']:
                        if paper_status:  # Paper exists but no PDF, delete old entry
                            session.query(Paper).filter_by(title=paper.title).delete()
                            session.flush()
                        
                        session.add(paper)
                        session.flush()
                        stored_papers.append(paper)
                    else:
                        print(f"Skipping duplicate paper (with PDF): {paper.title[:50]}...")
                except Exception as e:
                    session.rollback()
                    print(f"Error storing paper {paper.title[:50]}...: {e}")
                    continue
            
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"Error committing papers: {e}")
                return []
            
        return stored_papers

    async def collect_all(self) -> tuple[int, List[Paper]]:
        # Get existing papers with their status
        existing_papers = await self.get_existing_papers()
        
        # Collect new papers
        arxiv_papers = await self.collector.collect_from_arxiv()
        zotero_papers = await self.collector.collect_from_zotero()
        
        # Deduplicate before storing
        all_papers = self.deduplicate_papers(arxiv_papers + zotero_papers)
        
        # Store papers with existing check
        stored_papers = await self.store_papers(all_papers, existing_papers)
        
        return len(all_papers), stored_papers
    
    def deduplicate_papers(self, papers: List[Paper]) -> List[Paper]:
        seen_titles = set()
        unique_papers = []
        
        for paper in papers:
            if paper.title not in seen_titles:
                seen_titles.add(paper.title)
                unique_papers.append(paper)
        
        return unique_papers