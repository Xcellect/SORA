# SORA (Superintelligent Obsidian Research Automation)

SORA is an advanced research automation system that streamlines the collection, organization, and analysis of academic papers. It integrates with Zotero and Obsidian to create a seamless research workflow.

## Features

- **Automated Paper Collection**
  - ArXiv integration for AI/ML research papers
  - Zotero integration for reference management
  - Automatic PDF downloads
  - Deduplication and metadata extraction

- **Intelligent Organization**
  - Automated categorization and tagging
  - Smart folder structure
  - Citation network mapping
  - Metadata extraction and organization

- **Obsidian Integration**
  - Automatic note generation
  - Knowledge graph creation
  - Citation management
  - Research workflow automation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Xcellect/SORA.git
cd sora
```

2. Create and activate a virtual environment using UV:
```bash
uv venv sora
source .sora/bin/activate  # On Unix/macOS
```
or
```bash
.sora\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
uv pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

6. Edit .env with your Zotero credentials


## Usage

### Basic Commands

- Collect papers from ArXiv:
```bash
python main.py --get 5 --source arxiv
```

- Collect papers from Zotero:
```bash
python main.py --get 5 --source zotero
```

- Organize collected papers and generate notes:
```bash
python main.py --organize
```

- Organize papers from a specific source:
```bash
python main.py --organize-only --source zotero
```

### Database Management

- View database contents:
```bash
python main.py --view
```

- Export database to CSV:
```bash
python main.py --export
```

- Sync database with PDF files:
```bash
python main.py --sync
```

### Cleanup Operations

- Clear collected papers and reset database:
```bash
python main.py --flush
```

- Clear paper metadata and Obsidian notes:
```bash
python main.py --flush-org
```

### Additional Options

- `--force`: Overwrite existing papers and notes
- `--source`: Specify source (arxiv or zotero)
- `--organize-only`: Run organization without collection
- `--get N`: Collect N papers per category

### Example Workflows

1. Collect and organize new papers:
```bash
python main.py --get 5 --source arxiv --organize
```

2. Update existing paper organization:
```bash
python main.py --organize-only --source zotero
```

3. Fresh start with new papers:
```bash
python main.py --flush
python main.py --get 10 --source arxiv --organize
```

4. Export database after collection:
```bash
python main.py --get 5 --source zotero
python main.py --export
```

### Generated Content

Each organized paper includes:
- PDF file in year-based directory
- Detailed metadata JSON with analysis
- Obsidian note with:
  - Paper metadata and URL
  - Research context
  - Key methods
  - Technical contributions
  - Implementation details
  - Research impact
  - Document structure
  - Figures and tables summary
  - Auto-generated tags

## Project Structure
```bash
sora/
├── config/             # Configuration settings
├── features/
│ ├── collection/       # Paper collection functionality
│ ├── organization/     # Organization and analysis
│ └── shared/           # Shared utilities and models
├── notes/                        # Automated Obsidian notes by LLMs
│ ├── Research Papers.md          # Index file
│ ├── paper-title-author-year.md  # Individual paper notes
├── notebooks           # For advanced analysis on ipynb
├── data/               # Database and exported data
├── papers/             # Papers organized by publication year
│ ├── by_year/ 
│   ├── 2024/
│   ├── 2023/
│   ├── ...
│ ├── metadata/         # JSON metadata for further analysis
│ ├── pdf/              # Original PDFs
└── tests/              # Test suite

```

## Configuration

### ArXiv Categories
Default categories (can be modified in `config/settings.py`):
- cs.AI (Artificial Intelligence)
- cs.LG (Machine Learning)
- cs.NE (Neural Computing)
- stat.ML (Statistics/Machine Learning)

### Zotero Integration
Required environment variables:
- `ZOTERO_LIBRARY_ID`
- `ZOTERO_API_KEY`

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
This project uses `ruff` for linting:
```bash
ruff check .
```

## Dependencies

- Python ≥ 3.10
- Key packages:
  - arxiv
  - pyzotero
  - sqlalchemy
  - aiohttp
  - spacy
  - scikit-learn
  - networkx

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- ArXiv API for providing access to research papers
- Zotero for reference management capabilities
- Obsidian for knowledge management features

## Contact

Aishik S. - [@xcellect](https://x.com/xcellect)
