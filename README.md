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
git clone https://github.com/yourusername/sora.git
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

- Collect papers:
```bash
python main.py --papers-per-category 5
```

- Organize collected papers in Obsidian:
```bash
python main.py --organize
```

- View database contents:
```bash
python main.py --view
```

### Additional Options

- `--force`: Overwrite existing papers
- `--sync`: Sync database with PDF files
- `--flush`: Clear all data and start fresh
- `--export`: Export database to CSV
- `--organize-only`: Run organization without collection

## Project Structure

sora/
├── config/             # Configuration settings
├── features/
│ ├── collection/       # Paper collection functionality
│ ├── organization/     # Organization and analysis
│ └── shared/           # Shared utilities and models
├── notebooks           # For advanced analysis
├── data/               # Database and exported data
├── papers/             # Downloaded PDFs
└── tests/              # Test suite


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

Your Name - [@xcellect](https://x.com/xcellect)
Project Link: [https://github.com/yourusername/sora](https://github.com/xcellect/sora)