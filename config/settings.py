# config/settings.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    # Base paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    PAPERS_DIR = BASE_DIR / "papers"
    PDF_DIR = PAPERS_DIR / "pdf"
    
    # Zotero configuration
    ZOTERO_LIBRARY_ID = os.getenv("ZOTERO_LIBRARY_ID")
    ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
    ZOTERO_LIBRARY_TYPE = "user"  # or "group"

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # ArXiv categories
    ARXIV_CATEGORIES = [
        "cs.AI",    # Artificial Intelligence
        "cs.LG",    # Machine Learning
        "cs.NE",    # Neural and Evolutionary Computing
        "stat.ML"   # Machine Learning (Statistics)
    ]
    PAPERS_PER_CATEGORY = 100  # Default value, can be overridden
    FORCE_UPDATE = False  # Default value
    # Database
    DB_URL = "sqlite+aiosqlite:///paper_collection.db"  # Change from sqlite:/// to sqlite+aiosqlite:///