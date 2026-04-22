u# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-22

### Added
- Initial release of zdkvartira.ru website crawler and analyzer
- Comprehensive page analysis for 1,374 HTML pages
- Automatic page type classification into 23 categories
- Multiple output formats (TXT, CSV, YAML, Markdown)
- Block structure extraction with CSS selectors
- Detailed documentation for each page type
- Virtual environment setup with required dependencies
- Package configuration files (package.json, README.md, CHANGELOG.md)

### Features
- **pages.txt**: Tab-delimited list of all pages
- **pages.csv**: CSV format with UTF-8 BOM and quoted fields
- **types.yaml**: Complete structured data with page types and blocks
- **page-types/*.md**: Individual Markdown documentation for each page type
  - Line wrapping at 90 characters for readability
  - Plain text descriptions without quotes
  - Main page includes header/footer; others exclude common blocks
- **page-lists/{type}.txt**: Page lists organized by type
  - Tab-delimited format: `{url}\t{title}`
  - Clean filenames without `-pages` suffix
  - Example: `news-article.txt`, `00-main.txt`
- Main page (`00-main`) includes `mainheader` and `footer` blocks
- Other page types exclude common blocks for cleaner documentation
- Text cleaning: removal of line breaks and multiple spaces
- English dash-case IDs for all page types
- Ordered output with main page first
- Preserved block order matching HTML document structure
- Enhanced block detection:
  - Filter forms (`#filter`) on any element type
  - Content lists (`.container` with card items)
  - Pagination navigation (`nav` elements)
- Duplicate block prevention (unique block IDs per page)

### Technical Details
- Python 3.6+ implementation
- BeautifulSoup4 for HTML parsing
- PyYAML for YAML generation
- Automated block detection and classification
- Support for Cyrillic content and URLs
- Clean, readable output formatting
- UTF-8 encoding support for Windows console
- Document-order preservation for content blocks

### Project Structure
```
crawl-site/
├── analyze-sources/zdkvartira.ru/    # Source HTML files from crawl-site
├── results/                   # Analysis output directory
│   ├── pages.txt             # All pages (TAB-delimited)
│   ├── pages.csv             # All pages (CSV with quotes)
│   ├── types.yaml            # Complete type definitions
│   ├── page-types/           # Type descriptions (23 .md files)
│   │   ├── 00-main.md        # Main page (12 blocks)
│   │   ├── analytics.md      # Analytics (4 blocks)
│   │   ├── news-list.md      # News list (5 blocks with pagination)
│   │   └── ...               # 20 more page types
│   └── page-lists/           # Page lists by type (23 .txt files)
│       ├── 00-main.txt       # TAB: {url}\t{title}
│       ├── news-article.txt  # 1,246 pages listed
│       └── ...               # 21 more type files
├── .venv/                     # Python virtual environment
├── analyze-pages.py          # Main analysis script
├── package.json              # NPM package configuration
├── README.md                 # Project documentation
│                             # Includes crawl-site integration guide
├── CHANGELOG.md              # This file
└── TODO.md                   # Development task list
```

## [Unreleased]

### Planned
- Add support for incremental crawling
- Implement change detection for updated pages
- Add visualization tools for site structure
- Export to additional formats (JSON, XML)
- Add API endpoint for programmatic access
- Implement caching mechanism for faster re-runs
