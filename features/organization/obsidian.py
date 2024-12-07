from pathlib import Path
from typing import Dict
from features.shared.database import Paper
from config.settings import Settings
import re
from datetime import datetime

class ObsidianManager:
    def __init__(self):
        self.notes_dir = Path(Settings.OBSIDIAN_VAULT_PATH)
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
        content = self._generate_note_content(paper, llm_analysis, metadata)
        
        # Write note file
        note_path.write_text(content)
        print(f"DEBUG: Created note at {note_path}")
        
        # Update index
        self._update_index(paper)
        
        return note_path

    def _generate_note_filename(self, paper: Paper) -> str:
        """Generate a safe filename for the note"""
        try:
            # Basic sanitization of the title
            safe_title = "".join(c for c in paper.title[:50] if c.isalnum() or c in (' ', '-'))
            safe_title = safe_title.replace(' ', '-').lower()
            
            return f"{paper.id}_{safe_title}.md"
        except Exception as e:
            print(f"DEBUG: Error generating filename: {e}")
            return f"paper-{paper.id}.md"

    def _generate_note_content(self, paper: Paper, analysis: Dict, metadata: Dict) -> str:
        """Generate formatted note content"""
        # Helper function to format section content
        def format_section(section_data: Dict, key: str) -> str:
            if not section_data or key not in section_data:
                return "No data available"
            
            content = []
            for subkey, value in section_data[key].items():
                content.append(f"### {subkey}")
                if isinstance(value, list):
                    content.extend([f"- {item}" for item in value if item])
                else:
                    content.append(str(value))
                content.append("")
            return "\n".join(content)

        # Helper function to format tags
        def format_tags(tags_data: Dict) -> str:
            if not tags_data or 'Relevant Tags' not in tags_data:
                return "No tags available"
            
            all_tags = []
            for category, tags in tags_data['Relevant Tags'].items():
                if isinstance(tags, list):
                    all_tags.extend(tags)
            
            return " ".join([f"#{tag.replace(' ', '_')}" for tag in all_tags if tag])

        # Get document structure
        doc_structure = metadata.get('document_structure', {})
        figures_tables = metadata.get('figures_tables', {})
        
        # Get the appropriate URL based on source
        if paper.source == 'zotero':
            paper_url = paper.url if paper.url and paper.url.startswith('http') else 'No URL available'
        else:  # arxiv
            arxiv_id = paper.paper_metadata.get('arxiv_id', '')
            paper_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else (paper.url or 'No URL available')
            
        # Get publication date
        pub_date = None
        if paper.date:
            pub_date = paper.date.year
        elif paper.paper_metadata and 'published' in paper.paper_metadata:
            pub_date = paper.paper_metadata['published'][:4]  # Get year from YYYY-MM-DD
            
        content = [
            f"# {paper.title}",
            "",
            "## Metadata",
            f"- **Authors**: {', '.join(paper.authors) if isinstance(paper.authors, list) else paper.authors}",
            f"- **Year**: {pub_date or 'N/A'}",
            f"- **Source**: {paper.source}",
            f"- **URL**: {paper_url}",
            f"- **Pages**: {doc_structure.get('total_pages', 'N/A')}",
            "",
            "## Research Context",
            format_section(analysis, 'Research Context'),
            "",
            "## Key Methods and Technologies",
            format_section(analysis, 'Key Methods and Technologies'),
            "",
            "## Technical Contributions",
            format_section(analysis, 'Technical Contributions'),
            "",
            "## Implementation Details",
            format_section(analysis, 'Implementation Details'),
            "",
            "## Research Impact",
            format_section(analysis, 'Research Impact'),
            "",
            "## Document Structure",
            "### Sections",
            self._format_sections(doc_structure.get('sections', [])),
            "",
            "### Figures and Tables",
            self._format_figures_tables(figures_tables),
            "",
            "## Tags",
            format_tags(analysis),
            "",
            f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ]
        
        return "\n".join(content)

    def _format_sections(self, sections: list) -> str:
        """Format document sections"""
        if not sections:
            return "No section information available"
        
        formatted = []
        for section in sections:
            formatted.append(f"- {section['name']} (Page {section['page']})")
        return "\n".join(formatted)

    def _format_figures_tables(self, figures_tables: Dict) -> str:
        """Format figures and tables information"""
        content = []
        
        # Format figures
        figures = figures_tables.get('figures', [])
        if figures:
            content.append("### Figures")
            for fig in figures:
                content.append(f"- Figure {fig['number']} (Page {fig['page']}): {fig['caption']}")
        
        # Format tables
        tables = figures_tables.get('tables', [])
        if tables:
            content.append("\n### Tables")
            for table in tables:
                content.append(f"- Table {table['number']} (Page {table['page']}): {table['caption']}")
        
        return "\n".join(content) if content else "No figures or tables information available"

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
        paper_link = f"- [[{self._generate_note_filename(paper)[:-3]}|{paper.title}]]"
        current_content.insert(recent_index, paper_link)
        
        # Write updated content
        self.index_path.write_text("\n".join(current_content))