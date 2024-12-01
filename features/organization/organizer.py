from pathlib import Path
from typing import Dict, List
from features.shared.database import Paper
from .analyzer import ContentAnalyzer
from .obsidian import ObsidianManager
import re
import json
import shutil
from datetime import datetime

class PaperOrganizer:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.analyzer = ContentAnalyzer()
        self.obsidian = ObsidianManager(base_dir / "notes")
        
        # Create directory structure (simplified)
        self.dirs = {
            'by_year': base_dir / "papers" / "by_year",
            'metadata': base_dir / "papers" / "metadata"
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def organize_paper(self, paper: Paper) -> Dict:
        """Organize a single paper with intelligent categorization"""
        try:
            # Analyze paper content
            analysis = await self.analyzer.analyze_paper(paper)
            if not analysis:
                return {'status': 'failed', 'error': 'Analysis failed'}
            
            # Extract year
            year = self._extract_year(paper)
            
            # Create year directory
            year_dir = self.dirs['by_year'] / year
            year_dir.mkdir(exist_ok=True)
            
            # Copy paper to year directory
            paper_filename = f"{paper.id}_{self._sanitize_filename(paper.title)}.pdf"
            year_path = year_dir / paper_filename
            
            if paper.pdf_path and Path(paper.pdf_path).exists():
                shutil.copy2(paper.pdf_path, year_path)
                print(f"DEBUG: Copied PDF to {year_path}")
            
            # Save metadata
            metadata = {
                'paper_id': paper.id,
                'title': paper.title,
                'authors': paper.authors,
                'year': year,
                'analysis': analysis,
                'organized_paths': {
                    'year': str(year_path)
                },
                'organized_date': datetime.now().isoformat()
            }
            
            metadata_path = self.dirs['metadata'] / f"{paper.id}.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))
            print(f"DEBUG: Saved metadata to {metadata_path}")
            
            # Create Obsidian note
            note_path = await self.obsidian.create_note(paper, metadata)
            print(f"DEBUG: Created note at {note_path}")
            
            return {
                'status': 'success',
                'metadata': metadata,
                'paths': {
                    'metadata': str(metadata_path),
                    'note': str(note_path),
                    'pdf': str(year_path)
                }
            }
            
        except Exception as e:
            print(f"Error organizing paper {paper.title}: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def _sanitize_filename(self, filename: str) -> str:
        """Clean filename for filesystem compatibility"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()[:100]  # Limit length
    
    def _extract_year(self, paper: Paper) -> str:
        """Extract year from paper metadata"""
        try:
            # Try to extract from arxiv ID if available
            if hasattr(paper, 'arxiv_id') and paper.arxiv_id:
                arxiv_match = re.search(r'(\d{2})\d{2}\.\d+', str(paper.arxiv_id))
                if arxiv_match:
                    year = arxiv_match.group(1)
                    return f"20{year}"
            
            # Try to find year in title
            if paper.title:
                year_match = re.search(r'(19|20)\d{2}', str(paper.title))
                if year_match:
                    return year_match.group(0)
            
            # Default to current year if no year found
            return str(datetime.now().year)
            
        except Exception as e:
            print(f"DEBUG: Error extracting year: {e}")
            return "unknown_year"