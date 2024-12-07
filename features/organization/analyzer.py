import fitz
import openai
import re
from typing import Dict, List
from pathlib import Path
from features.shared.database import Paper
from config.settings import Settings
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class ContentAnalyzer:
    """Analyzes paper content using LLM for intelligent extraction"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=Settings.OPENAI_API_KEY,
            http_client=httpx.AsyncClient()  # Explicitly disable proxies
        )
        
        self.system_prompt = """You are a multidisciplinary research paper analysis assistant. Analyze the provided paper and return a JSON response with the following structure:
            {
                "Key Methods and Technologies": {
                    "Primary methods used": ["<string>"],
                    "Technical frameworks and tools": ["<string>"],
                    "Novel techniques or approaches": ["<string>"]
                },
                "Research Context": {
                    "Main research area": "<string>",
                    "Related fields and interdisciplinary connections": ["<string>"],
                    "Problem domain and specific challenges addressed": ["<string>"]
                },
                "Technical Contributions": {
                    "Novel approaches or methodologies introduced": ["<string>"],
                    "Improvements to existing methods": ["<string>"],
                    "Key results and performance metrics": ["<string>"],
                    "Technical innovations": ["<string>"]
                },
                "Implementation Details": {
                    "Equipment and tools used": ["<string>"],
                    "Experimental setup": ["<string>"],
                    "Data collection and analysis methods": ["<string>"]
                },
                "Research Impact": {
                    "Key findings and breakthroughs": ["<string>"],
                    "Limitations and future work": ["<string>"],
                    "Potential applications": ["<string>"]
                },
                "Relevant Tags": {
                    "Technical keywords": ["<string>"],
                    "Research areas": ["<string>"],
                    "Application domains": ["<string>"],
                    "Method categories": ["<string>"]
                }
            }

            Analyze the text and return only a JSON object matching this schema."""
        
        self.analysis_prompt = "Please analyze this research paper and provide a detailed analysis in JSON format:\n\n{text}"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
    )
    async def _analyze_with_llm(self, text: str) -> Dict:
        """Analyze text using GPT-4 with automatic retries"""
        try:
            print(f"DEBUG: Starting LLM analysis, text length: {len(text)}")
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.analysis_prompt.format(text=text[:15000])}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            print("DEBUG: LLM response received")
            
            result = json.loads(response.choices[0].message.content)
            print(f"DEBUG: Parsed LLM response, keys: {result.keys()}")
            return result
            
        except Exception as e:
            print(f"DEBUG: Error in LLM analysis: {str(e)}")
            print(f"DEBUG: Error type: {type(e)}")
            import traceback
            print(f"DEBUG: Traceback:\n{traceback.format_exc()}")
            return {}

    async def analyze_paper(self, paper: Paper) -> Dict:
        """Main analysis entry point for a paper"""
        print(f"\nDEBUG: Starting analysis for paper: {paper.title}")
        
        if not paper.pdf_path or not Path(paper.pdf_path).exists():
            print(f"DEBUG: PDF not found at path: {paper.pdf_path}")
            return {}
        
        try:
            print(f"DEBUG: Opening PDF from {paper.pdf_path}")
            # Extract text content
            doc = fitz.open(paper.pdf_path)
            print(f"DEBUG: Successfully opened PDF, pages: {len(doc)}")
            
            # Get abstract and introduction for main analysis
            intro_text = ""
            for page in doc[:2]:  # First two pages usually contain abstract and intro
                intro_text += page.get_text()
            print(f"DEBUG: Extracted intro text length: {len(intro_text)}")
            
            # Get full text for citations and references
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            print(f"DEBUG: Extracted full text length: {len(full_text)}")
            
            # Analyze with LLM
            print("DEBUG: Starting LLM analysis")
            analysis = await self._analyze_with_llm(intro_text)
            print(f"DEBUG: LLM analysis complete, keys: {analysis.keys() if analysis else 'None'}")
            
            # Extract additional metadata
            print("DEBUG: Starting metadata extraction")
            metadata = {
                'llm_analysis': analysis,
                'document_structure': await self._analyze_document_structure(doc),
                'citations': await self._extract_citations(full_text),
                'references': await self._extract_references(full_text),
                'figures_tables': await self._extract_figures_tables(doc)
            }
            print(f"DEBUG: Metadata extraction complete, keys: {metadata.keys()}")
            
            return metadata
            
        except Exception as e:
            print(f"DEBUG: Error in analyze_paper: {str(e)}")
            print(f"DEBUG: Error type: {type(e)}")
            import traceback
            print(f"DEBUG: Traceback:\n{traceback.format_exc()}")
            return {}
        finally:
            if 'doc' in locals():
                doc.close()
                print("DEBUG: Closed PDF document")

    async def _analyze_document_structure(self, doc: fitz.Document) -> Dict:
        """Analyze document structure"""
        try:
            print("DEBUG: Starting document structure analysis")
            result = {
                'total_pages': len(doc),
                'sections': await self._identify_sections(doc),
                'has_abstract': bool(re.search(r'\babstract\b', doc[0].get_text(), re.IGNORECASE)),
                'has_references': bool(re.search(r'\breferences\b|\bbibliography\b', 
                                              doc[-1].get_text(), re.IGNORECASE))
            }
            print(f"DEBUG: Document structure analysis complete: {result}")
            return result
        except Exception as e:
            print(f"DEBUG: Error in document structure analysis: {str(e)}")
            return {}

        
    async def _identify_sections(self, doc: fitz.Document) -> List[Dict]:
        """Identify major sections in the paper"""
        try:
            print("DEBUG: Starting section identification")
            sections = []
            section_patterns = [
                r'\b(abstract)\b',
                r'\b(introduction)\b',
                r'\b(related\s+work)\b',
                r'\b(methodology|method|approach)\b',
                r'\b(experiment|experimental|results)\b',
                r'\b(discussion)\b',
                r'\b(conclusion)\b',
                r'\b(references|bibliography)\b'
            ]
            
            # Process each page
            for page_num in range(len(doc)):
                text = doc[page_num].get_text()
                for pattern in section_patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        sections.append({
                            'name': match.group(1),
                            'page': page_num + 1,
                            'position': match.start()
                        })
            
            print(f"DEBUG: Found {len(sections)} sections")
            return sorted(sections, key=lambda x: (x['page'], x['position']))
            
        except Exception as e:
            print(f"DEBUG: Error in section identification: {str(e)}")
            return []

    async def _extract_citations(self, text: str) -> List[Dict]:
        """Extract citations from text"""
        try:
            print("DEBUG: Starting citation extraction")
            citations = []
            
            # Citation patterns
            patterns = [
                (r'\[([\d,\s]+)\]', 'numeric'),  # [1] or [1,2,3]
                (r'\((\w+\s*et\s*al\.,\s*\d{4})\)', 'author-year'),  # (Author et al., 2023)
                (r'\[(\w+\s*et\s*al\.,\s*\d{4})\]', 'author-year-brackets'),  # [Author et al., 2023]
            ]
            
            for pattern, citation_type in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    citations.append({
                        'text': match.group(1),
                        'type': citation_type,
                        'position': match.start()
                    })
            
            print(f"DEBUG: Found {len(citations)} citations")
            return sorted(citations, key=lambda x: x['position'])
            
        except Exception as e:
            print(f"DEBUG: Error in citation extraction: {str(e)}")
            return []
        


    # references

    async def _extract_references(self, text: str) -> List[Dict]:
        """Extract references from text"""
        try:
            print("DEBUG: Starting reference extraction")
            references = []
            
            # Find references section
            ref_match = re.search(r'(?:References|Bibliography)\s*(.*?)(?:\n\s*(?:[A-Z]|\d+\.|\[|\(|$))', 
                                text, re.IGNORECASE | re.DOTALL)
            
            if not ref_match:
                print("DEBUG: References section not found")
                return references
            
            # Split references into individual entries
            ref_text = ref_match.group(1)
            ref_entries = re.split(r'\n\s*(?:\[\d+\]|\d+\.|\(\d+\))', ref_text)
            
            for idx, entry in enumerate(ref_entries):
                entry = entry.strip()
                if entry:
                    references.append({
                        'index': idx + 1,
                        'text': entry,
                        'authors': self._extract_authors_from_reference(entry),
                        'year': self._extract_year_from_reference(entry),
                        'title': self._extract_title_from_reference(entry)
                    })
            
            print(f"DEBUG: Found {len(references)} references")
            return references
            
        except Exception as e:
            print(f"DEBUG: Error in reference extraction: {str(e)}")
            return []
    
    def _extract_authors_from_reference(self, ref_text: str) -> List[str]:
        """Extract author names from reference text"""
        try:
            # Look for author patterns before year or title
            author_match = re.search(r'^(.*?)(?:\(\d{4}\)|,\s*\d{4}|\.|\"|\')', ref_text)
            if author_match:
                authors = author_match.group(1).strip()
                # Split and clean author names
                return [author.strip() for author in authors.split(',') if author.strip()]
        except Exception as e:
            print(f"DEBUG: Error extracting authors from reference: {str(e)}")
        return []
    
    def _extract_year_from_reference(self, ref_text: str) -> str:
        """Extract year from reference text"""
        try:
            year_match = re.search(r'\(?(\d{4})\)?', ref_text)
            if year_match:
                return year_match.group(1)
        except Exception as e:
            print(f"DEBUG: Error extracting year from reference: {str(e)}")
        return ""
    
    def _extract_title_from_reference(self, ref_text: str) -> str:
        """Extract paper title from reference text"""
        try:
            # Look for title patterns (usually between year and venue/journal)
            title_match = re.search(r'(?:\d{4}[.,\s]*)(.*?)(?:In\s|arXiv|Proceedings|Journal|IEEE|ACM)', ref_text)
            if title_match:
                return title_match.group(1).strip(' "\'.,')
        except Exception as e:
            print(f"DEBUG: Error extracting title from reference: {str(e)}")
        return ""
    

    # figure table

    async def _extract_figures_tables(self, doc: fitz.Document) -> Dict:
        """Extract information about figures and tables"""
        try:
            print("DEBUG: Starting figures and tables extraction")
            figures_tables = {
                'figures': [],
                'tables': []
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Find figures
                fig_matches = re.finditer(
                    r'(?:Figure|Fig\.?)\s*(\d+)[\.:]?\s*([^\n]+)', 
                    text, 
                    re.IGNORECASE
                )
                for match in fig_matches:
                    figures_tables['figures'].append({
                        'number': match.group(1),
                        'caption': match.group(2).strip(),
                        'page': page_num + 1
                    })
                
                # Find tables
                table_matches = re.finditer(
                    r'Table\s*(\d+)[\.:]?\s*([^\n]+)', 
                    text, 
                    re.IGNORECASE
                )
                for match in table_matches:
                    figures_tables['tables'].append({
                        'number': match.group(1),
                        'caption': match.group(2).strip(),
                        'page': page_num + 1
                    })
            
            print(f"DEBUG: Found {len(figures_tables['figures'])} figures and {len(figures_tables['tables'])} tables")
            return figures_tables
            
        except Exception as e:
            print(f"DEBUG: Error in figures/tables extraction: {str(e)}")
            return {'figures': [], 'tables': []}