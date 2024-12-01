import arxiv
from pyzotero import zotero
import asyncio
from tqdm import tqdm
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from features.shared.database import Paper, Base
from config.settings import Settings
from typing import List, Optional
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine as create_engine
from sqlalchemy import select

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
        
        # Create collections if they don't exist
        self.automated_collection_key = self._get_or_create_collection("Automated Collection")
        self.organic_collection_key = self._get_or_create_collection("Organic Collection")

    def _get_or_create_collection(self, name: str) -> str:
        """Get collection key or create if doesn't exist"""
        collections = self.zot.collections()
        for collection in collections:
            if collection['data']['name'] == name:
                return collection['key']
        
        # Create new collection if not found
        resp = self.zot.create_collections([{'name': name}])
        return resp['successful']['0']['key']
    

    async def add_to_zotero(self, paper: Paper) -> None:
        """Add paper to Automated Collection in Zotero"""
        template = {
            'itemType': 'journalArticle',
            'title': paper.title,
            'creators': [{'creatorType': 'author', 'name': author} 
                        for author in paper.authors],
            'abstractNote': paper.abstract,
            'url': paper.url,
            'tags': [{'tag': 'AI Research'}],
            'collections': [self.automated_collection_key]  # Add to Automated Collection
        }
        
        if paper.paper_metadata.get('categories'):
            template['tags'].append({'tag': paper.paper_metadata['categories'][0]})
        
        try:
            await asyncio.to_thread(self.zot.create_items, [template])
            print(f"Added paper to Zotero: {paper.title}")
        except Exception as e:
            print(f"Error adding to Zotero: {e}")

    async def collect_from_arxiv(self) -> List[Paper]:
        """Collect papers from ArXiv with deduplication"""
        collected = set()
        seen_titles = set()
        
        for category in Settings.ARXIV_CATEGORIES:
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=Settings.PAPERS_PER_CATEGORY,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            for result in tqdm(search.results(), desc=f"Collecting {category}"):
                if result.title in seen_titles:
                    continue
                    
                seen_titles.add(result.title)
                
                # Extract metadata safely with fallbacks
                metadata = {
                    'arxiv_id': result.entry_id.split('/')[-1],  # Get clean arxiv ID
                    'categories': result.categories,
                    'comments': getattr(result, 'comment', None),
                    'primary_category': result.primary_category,
                    'published': result.published.strftime('%Y-%m-%d') if result.published else None,
                    'updated': result.updated.strftime('%Y-%m-%d') if result.updated else None,
                    'journal_ref': getattr(result, 'journal_ref', None)
                }
                
                paper = Paper(
                    title=result.title,
                    authors=[str(a) for a in result.authors],
                    abstract=result.summary,
                    url=result.pdf_url,
                    source='arxiv',
                    date=result.published,
                    doi=getattr(result, 'doi', None),
                    journal=getattr(result, 'journal_ref', None),
                    paper_metadata=metadata
                )
                collected.add(paper)
                await self.add_to_zotero(paper)
        
        return list(collected)
    
    def _extract_authors(self, creators: List[dict]) -> List[str]:
        """Extract author names from creators list"""
        authors = []
        for creator in creators:
            if creator.get('creatorType') == 'author':
                if 'name' in creator:
                    authors.append(creator['name'])
                elif 'firstName' in creator and 'lastName' in creator:
                    full_name = f"{creator['lastName']}, {creator['firstName']}"
                    authors.append(full_name)
        return authors or ["Unknown Author"]

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string into datetime object"""
        if not date_str:
            return datetime.now()
            
        try:
            for fmt in ['%Y-%m-%d', '%Y-%m', '%Y']:
                try:
                    return datetime.strptime(date_str[:len(fmt)], fmt)
                except ValueError:
                    continue
        except Exception as e:
            print(f"Warning: Could not parse date '{date_str}': {e}")
        return datetime.now()

    async def collect_from_zotero(self) -> List[Paper]:
        """Collect papers from Organic Collection only"""
        collected = []
        items = await asyncio.to_thread(
            self.zot.collection_items, 
            self.organic_collection_key, 
            limit=100
        )
        
        for item in tqdm(items, desc="Collecting from Zotero"):
            if item['data']['itemType'] == 'journalArticle':
                # Get PDF attachment if available
                attachments = await asyncio.to_thread(
                    self.zot.children, 
                    item['key']
                )
                
                pdf_url = None
                for attachment in attachments:
                    if attachment['data'].get('contentType') == 'application/pdf':
                        pdf_url = attachment['data'].get('url')
                        break
                
                # If no attachment URL, try the main URL
                if not pdf_url:
                    pdf_url = item['data'].get('url')

                paper = Paper(
                    title=item['data'].get('title'),
                    authors=self._extract_authors(item['data'].get('creators', [])),
                    abstract=item['data'].get('abstractNote'),
                    url=pdf_url,  # Use PDF URL if available
                    source='zotero',
                    date=self._parse_date(item['data'].get('date')),
                    doi=item['data'].get('DOI'),
                    journal=item['data'].get('publicationTitle'),
                    paper_metadata={
                        'zotero_key': item['key'],
                        'volume': item['data'].get('volume'),
                        'issue': item['data'].get('issue'),
                        'pages': item['data'].get('pages'),
                        'tags': item['data'].get('tags', [])
                    }
                )
                collected.append(paper)
        
        return collected

    async def collect_papers(self, source: str = 'arxiv') -> List[Paper]:
        """Collect papers from specified source only"""
        if source.lower() == 'arxiv':
            papers = await self.collect_from_arxiv()
            # Papers are already added to Zotero in collect_from_arxiv
            return papers
        elif source.lower() == 'zotero':
            return await self.collect_from_zotero()
        else:
            raise ValueError(f"Unknown source: {source}")
    

class AsyncPaperManager:
    def __init__(self):
        self.collector = PaperCollector()
        # Use async engine instead of sync engine
        self.engine = create_engine(Settings.DB_URL, future=True)
        # Don't create tables in __init__ - move to async init method
        self.SessionMaker = sessionmaker(bind=self.engine)

    async def initialize(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def store_papers(self, papers: List[Paper], existing_papers: dict) -> List[Paper]:
        """Store papers in database with deduplication"""
        stored_papers = []
        seen_titles = set()  # Track titles within this batch
        
        async with self.session_scope() as session:
            for paper in papers:
                try:
                    # Skip if we've seen this title in current batch
                    if paper.title in seen_titles:
                        continue
                    
                    seen_titles.add(paper.title)
                    paper_status = existing_papers.get(paper.title)
                    
                    # Add paper if it's new or if it exists but has no PDF
                    if not paper_status or (not paper_status['has_pdf'] and Settings.FORCE_UPDATE):
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

    async def collect_all(self, source: str = 'arxiv') -> tuple[int, List[Paper]]:
        """Collect papers from specified source"""
        # Get existing papers with their status
        existing_papers = await self.get_existing_papers()
        
        # Collect new papers from specified source only
        if source.lower() == 'arxiv':
            papers = await self.collector.collect_papers(source='arxiv')
        elif source.lower() == 'zotero':
            papers = await self.collector.collect_papers(source='zotero')
        else:
            raise ValueError(f"Unknown source: {source}")
        
        # Store papers with existing check
        stored_papers = await self.store_papers(papers, existing_papers)
        
        return len(papers), stored_papers
    
    def deduplicate_papers(self, papers: List[Paper]) -> List[Paper]:
        """Remove duplicate papers based on title"""
        seen_titles = set()
        unique_papers = []
        
        for paper in papers:
            if paper.title not in seen_titles:
                seen_titles.add(paper.title)
                unique_papers.append(paper)
        
        return unique_papers

    async def get_unprocessed_papers(self, limit: int = None) -> List[Paper]:
        """Get papers that haven't been processed yet"""
        async with self.session_scope() as session:
            query = session.query(Paper).filter_by(processed=0)
            if limit:
                query = query.limit(limit)
            return query.all()
        
    async def get_existing_papers(self) -> dict:
        """Get existing papers and their status from database"""
        existing_papers = {}
        
        async with self.session_scope() as session:
            papers = await session.execute(select(Paper))
            papers = papers.scalars().all()
            
            for paper in papers:
                existing_papers[paper.title] = {
                    'id': paper.id,
                    'has_pdf': paper.pdf_path is not None,
                    'processed': paper.processed
                }
        
        return existing_papers