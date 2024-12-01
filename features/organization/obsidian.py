from pathlib import Path
from typing import Dict
from features.shared.database import Paper
import re
from datetime import datetime

class ObsidianManager:
    def __init__(self, notes_dir: Path):
        self.notes_dir = notes_dir
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Create index file if it doesn't exist
        self.index_path = self.notes_dir / "Research Papers.md"
        if not self.index_path.exists():
            self._create_index()
    
    async def create_note(self, paper: Paper, metadata: Dict) -> Path:
        """Create an Obsidian note for the paper"""
        note_path = self.notes_dir / self._generate_note_filename(paper)
        
        # Extract analysis data
        analysis = metadata.get('analysis', {})
        llm_analysis = analysis.get('llm_analysis', {})
        
        # Create note content
        content = self._generate_note_content(paper, llm_analysis)
        
        # Write note file
        note_path.write_text(content)
        
        # Update index
        self._update_index(paper)
        
        return note_path

    def _generate_note_filename(self, paper: Paper) -> str:
        """Generate a descriptive filename for the note"""
        try:
            # Get first 4 words of title
            title_words = paper.title.split()[:4]
            title_part = "-".join(word.lower() for word in title_words)
            
            # Get first author
            first_author = paper.authors[0] if isinstance(paper.authors, list) and paper.authors else "unknown"
            first_author = first_author.replace(" ", "-").lower()
            
            # Get year
            year = getattr(paper, 'year', datetime.now().year)
            
            # Combine parts
            filename = f"{title_part}-{first_author}-{year}"
            
            # Clean filename of invalid characters
            filename = re.sub(r'[^\w\-]', '', filename)
            
            return f"{filename}.md"
            
        except Exception as e:
            print(f"DEBUG: Error generating filename: {e}")
            return f"{paper.id}.md"  # Fallback to ID-based filename

    def _generate_note_content(self, paper: Paper, analysis: Dict) -> str:
        """Generate formatted note content"""
        # Helper function to safely get metadata attributes
        def get_metadata(obj, key: str, default: str = "N/A") -> str:
            return obj.paper_metadata.get(key, default) if hasattr(obj, 'paper_metadata') else default
        
        # Format PDF link to prefer ArXiv
        arxiv_id = get_metadata(paper, 'arxiv_id')
        pdf_link = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id != "N/A" else paper.pdf_path
        
        content = [
            f"# {paper.title}",
            "",
            "## Metadata",
            f"- **Authors**: {paper.authors}",
            f"- **Published**: {get_metadata(paper, 'published')}",
            f"- **ArXiv ID**: {get_metadata(paper, 'arxiv_id')}",
            f"- **PDF**: {pdf_link}",
            "",
            "## Research Context",
            self._format_section(analysis.get('Research Context', {})),
            "",
            "## Key Methods and Technologies",
            self._format_section(analysis.get('Key Methods and Technologies', {})),
            "",
            "## Technical Contributions",
            self._format_section(analysis.get('Technical Contributions', {})),
            "",
            "## Implementation Details",
            self._format_section(analysis.get('Implementation Details', {})),
            "",
            "## Research Impact",
            self._format_section(analysis.get('Research Impact', {})),
            "",
            "## Tags",
            self._format_tags(analysis.get('Relevant Tags', [])),
            "",
            f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ]
        
        return "\n".join(content)
    
    def _format_section(self, section_data: Dict) -> str:
        """Format a section of the analysis"""
        if not section_data:
            return "No data available"
            
        content = []
        for key, value in section_data.items():
            if isinstance(value, list):
                content.append(f"### {key}")
                content.extend([f"- {item}" for item in value])
            else:
                content.append(f"### {key}")
                content.append(str(value))
            content.append("")
        
        return "\n".join(content)
    
    def _format_tags(self, tags: list) -> str:
        """Format tags for Obsidian"""
        if not tags:
            return "No tags available"
        return " ".join([f"#{tag.replace(' ', '_')}" for tag in tags])
    
    def _create_index(self) -> None:
        """Create the research papers index"""
        content = [
            "# Research Papers Index",
            "",
            "## Recent Papers",
            "",
            "## By Topic",
            "",
            "## By Year",
            "",
            "## By Author",
            ""
        ]
        self.index_path.write_text("\n".join(content))
    
    def _update_index(self, paper: Paper) -> None:
        """Update the index with a new paper"""
        current_content = self.index_path.read_text().split("\n")
        
        # Add to Recent Papers section
        recent_index = current_content.index("## Recent Papers") + 2
        paper_link = f"- [[{paper.id}]] {paper.title}"
        current_content.insert(recent_index, paper_link)
        
        # Write updated content
        self.index_path.write_text("\n".join(current_content))