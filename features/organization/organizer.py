from pathlib import Path
from typing import Dict
from features.shared.database import Paper
from .analyzer import ContentAnalyzer
from .obsidian import ObsidianManager

class PaperOrganizer:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.analyzer = ContentAnalyzer()
        self.obsidian = ObsidianManager(base_dir / "notes")
        
        # Create directory structure
        self.dirs = {
            'by_topic': base_dir / "papers" / "by_topic",
            'by_year': base_dir / "papers" / "by_year",
            'by_author': base_dir / "papers" / "by_author",
            'metadata': base_dir / "metadata"
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def organize_paper(self, paper: Paper) -> Dict:
        """Organize a single paper"""
        # Basic implementation for now
        return {
            'status': 'organized',
            'path': str(self.dirs['by_topic'] / f"{paper.id}")
        }