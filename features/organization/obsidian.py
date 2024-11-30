from pathlib import Path
from typing import Dict
from features.shared.database import Paper

class ObsidianManager:
    def __init__(self, notes_dir: Path):
        self.notes_dir = notes_dir
        self.notes_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_note(self, paper: Paper, metadata: Dict) -> Path:
        """Create an Obsidian note for the paper"""
        # Basic implementation for now
        return self.notes_dir / f"{paper.id}.md"