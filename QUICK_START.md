# Quick Start Guide

## First Time Setup

### Windows
```bash
setup.bat
```

### Linux/Mac
```bash
chmod +x setup.sh
./setup.sh
```

## Running the Analysis

After setup, activate the virtual environment and run the script:

### Windows
```bash
.venv\Scripts\activate
python analyze-pages.py
```

### Linux/Mac
```bash
source .venv/bin/activate
python analyze-pages.py
```

## Output Files

The script generates the following files in the `results/` directory:

- **pages.txt**: Tab-delimited list of all pages (URL, type ID, title)
- **pages.csv**: CSV format with quoted fields and UTF-8 BOM encoding (URL, type ID, title)
- **types.yaml**: Complete structured data for all page types
- **page-types/*.md**: Individual Markdown documentation per page type (23 types)
- **page-lists/*-pages.txt**: Page lists organized by type

## Page Type IDs

Page types are stored as English dash-case IDs instead of Russian text:
- `00-main` - Главная страница
- `property-catalog` - Каталог объектов недвижимости
- `news-article` - Страница новости
- `news-list` - Список новостей
- `property-detail` - Детальная страница объекта
- And 18 more types...

See `results/types.yaml` for complete type definitions.

## Prerequisites

- Python 3.6+
- Node.js 18+ and pnpm (for crawling, if needed)

## Dependencies

All Python dependencies are listed in `requirements.txt`. The setup script will install them automatically.
