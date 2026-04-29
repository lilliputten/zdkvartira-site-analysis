# ZDKvartira.ru Website Crawler & Analyzer

A Python-based web crawler and analyzer for the
zdkvartira.ru real estate website. This tool extracts
page structures, identifies content blocks, and generates
comprehensive documentation of the website's architecture.

## Results

- [results/](results/) - All results folder
- [results/pages.txt](results/pages.txt) - All pages list (TAB-delimited)
- [results/pages.csv](results/pages.csv) - All pages list (CSV format with quotes)
- [results/types.yaml](results/types.yaml) - Complete structured data for all types
- [results/page-types/](results/page-types/) - Page type descriptions (Markdown files)
- [results/page-lists/](results/page-lists/) - Page lists organized by type (Markdown files)

## Features

- **Comprehensive Page Analysis**: Analyzes all HTML pages
  from the crawled website
- **Block Structure Extraction**: Identifies and documents
  content blocks with CSS selectors, parent context, and content snippets
- **Page Type Classification**: Automatically classifies
  pages into 24 different types including:
  - Home page, news articles, service pages
  - Property catalog (listing pages with filters and maps)
  - Property object (individual property detail pages with custom sections)
  - Staff profiles, promotions, FAQ, reviews, and more
- **Custom Section Extraction**: Specialized section detection for Property Object and Property Catalog pages
- **Multiple Output Formats**: Generates results in TXT,
  CSV, YAML, and Markdown formats
- **Structured Documentation**: Creates detailed
  documentation for each page type
- **Smart Title Generation**: Uses meaningful headings or descriptions instead of technical CSS class names
- **Enhanced Block Detection**: Detects page titles, realty cards, breadcrumbs, and other specialized elements
- **Human-Readable Output**: Capitalized descriptions, deduplicated fields, and clean formatting
- **Intelligent Filtering**: Automatically excludes broken links (404, 500) and redirected pages (301, 302) from analysis
- **Smart Directory Cleanup**: Recursively cleans output directory while gracefully handling locked temp files

## Requirements

- Python 3.6+
- BeautifulSoup4
- PyYAML

## Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install beautifulsoup4 pyyaml
# Or install from `requirements.txt`:
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the analysis script:

```bash
python analyze-pages.py
```

### Configuration

The script uses the following environment variables:

- **`ZDKVARTIRA_BASE_URL`**: Base URL for the website (default: `https://zdkvartira.ru`)

Example with custom base URL:

```bash
# Linux/Mac
export ZDKVARTIRA_BASE_URL="https://example.com"
python analyze-pages.py

# Windows (PowerShell)
$env:ZDKVARTIRA_BASE_URL="https://example.com"
python analyze-pages.py

# Windows (CMD)
set ZDKVARTIRA_BASE_URL=https://example.com
python analyze-pages.py
```

## Creating Crawled Site with crawl-site

Before running the analyzer, you need to crawl the target
website. We use the [crawl-site](https://github.com/lilliputten/crawl-site) project for this purpose.

### Prerequisites

- Node.js 18+ and pnpm installed
- Git (optional, for cloning the repository)

### Step-by-Step Guide

#### 1. Clone or Navigate to crawl-site Project

```bash
git clone https://github.com/lilliputten/crawl-site
# Navigate to the crawl-site project directory
cd ...\crawl-site
```

#### 2. Install Dependencies

```bash
# Install required packages
pnpm install
```

#### 3. Configure the Crawler

Create or edit `.env.local` file in the crawl-site
directory:

```env
# Target website URL
SITE_URL=https://zdkvartira.ru

# Crawl settings
CRAWL_DELAY=1000
MAX_RETRIES=3
RETRY_DELAY_BASE=2000
REQUEST_TIMEOUT=30000

# Output directory (where HTML files will be saved)
DEST=./crawl-dest

# State directory (for resume capability)
STATE_DIR=./crawl-state

# Realistic browser User-Agent
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
  AppleWebKit/537.36 (KHTML, like Gecko) \
  Chrome/120.0.0.0 Safari/537.36

# Use full browser headers to impersonate a real browser
USE_BROWSER_HEADERS=true

# Respect robots.txt
RESPECT_ROBOTS_TXT=true

# Maximum pages to crawl (0 = unlimited)
MAX_PAGES=0

# Log level: debug, info, warn, error
LOG_LEVEL=info
```

#### 4. Scan the Website Structure

First, discover all pages on the website:

```bash
# Basic scan (uses homepage to find links)
pnpm scan

# Or specify custom site URL
pnpm scan --site-url=https://zdkvartira.ru
```

This creates:
- `sitemap.yaml` - List of discovered pages
- `internal-links.yaml` - Internal link structure
- `link-relations.yaml` - Page relationship map
- Other analysis files in `STATE_DIR`

#### 5. Crawl and Download Pages

Download all discovered pages as HTML files:

```bash
# Basic crawl (downloads all discovered pages)
pnpm crawl

# With custom output directory
pnpm crawl --dest=./crawl-dest

# Limit number of pages (for testing)
pnpm crawl --max-pages=100

# Resume from previous crawl (automatic)
pnpm crawl
```

The crawler will:
- Download HTML content for each page
- Preserve original directory structure
- Handle Cyrillic URLs properly
- Save state periodically for resume capability
- Retry failed pages automatically

#### 6. Verify Crawled Content

Check the output directory:

```bash
# List crawled results
ls crawl-dest/
```

You should see:
- `crawl-dest/` - HTML files with site structure
- `crawl-dest/crawl-state.yaml` - Crawl progress state
- Various analysis YAML files

#### 7. Move Crawled Content to Analyzer

Copy or move the crawled content to the analyzer's
expected location:

```bash
# From the crawl-site directory
# The analyzer expects files in:
# sources/zdkvartira.ru/

# Example (adjust paths as needed):
cp -r ../crawl-site/crawl-dest \
  ./sources/zdkvartira.ru/
```

#### 8. Run the Analyzer

Now you can analyze the crawled pages:

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# Run analysis
python analyze-pages.py
```

### Key Features of crawl-site

- **Two-stage process**: Scan (discover URLs) then Crawl
  (download content)
- **Resume capability**: Continue from where you left off
- **Smart retry**: Automatic retry of failed pages
- **Cyrillic URL support**: Proper handling of unicode
  characters
- **Browser impersonation**: Avoid detection with realistic
  headers
- **robots.txt respect**: Optional compliance with robots.txt
- **State management**: Track progress and resume later

### Useful Commands

```bash
# View help and all options
pnpm scan --help
pnpm crawl --help

# Clean up crawled data
pnpm clean

# Run both scan and crawl sequentially
pnpm start

# Development mode with auto-reload
pnpm dev
```

### Troubleshooting

**Issue: Crawler gets blocked**
- Enable `USE_BROWSER_HEADERS=true`
- Increase `CRAWL_DELAY` to 2000-3000ms
- Check if respecting robots.txt

**Issue: Missing pages**
- Try scanning without sitemaps first
- Check `broken-links.yaml` for errors

**Issue: Slow crawling**
- Reduce `CRAWL_DELAY` (but risk being blocked)
- Increase `REQUEST_TIMEOUT` if pages load slowly

For more information, see:
- [crawl-site GitHub Repository](https://github.com/lilliputten/crawl-site)

## Output Structure

The analysis results are saved to the `results/` directory:

```
results/
├── pages.txt          # All pages list (TAB-delimited)
│                      # Format: {url}\t{type}\t{title}
├── pages.csv          # All pages list (CSV format with quotes)
│                      # Format: "url","type","title"
├── types.yaml         # Complete structured data for all types
├── page-types/        # Page type descriptions (Markdown)
│   ├── 00-main.md     # Main page (includes header/footer)
│   ├── property-catalog.md   # Property listing pages (23 pages)
│   ├── property-object.md    # Individual property details (36 pages)
│   ├── analytics.md   # Analytics page (4 blocks)
│   ├── news-list.md   # News list (5 blocks with pagination)
│   └── ...            # 21 more page type descriptions
└── page-lists/        # Page lists organized by type
    ├── 00-main.txt    # TAB-delimited: {url}\t{title}
    ├── property-catalog.txt  # 23 property listing pages
    ├── property-object.txt   # 36 individual property pages
    ├── news-article.txt  # 1,246 news article pages
    ├── about.txt      # About page listings
    └── ...            # 21 more type-specific page lists
```

## Output Formats

### pages.txt
Tab-delimited file with all pages:
```
{url}\t{type}\t{title}
```

### pages.csv
CSV format with UTF-8 BOM encoding, all fields quoted:
```csv
"url","type","title"
```

### types.yaml
Complete YAML structure containing:
- Page type ID (dash-case English)
- Description in Russian
- Example URL and title
- Total page count
- Content blocks (excluding common blocks except for main page)
- Block details (ID, selector, heading, description)
- Blocks ordered as they appear in HTML document

### page-types/*.md
Markdown documentation for each page type:
- Metadata (ID, example URL, title, total pages)
- Content blocks with selectors and descriptions
- Plain text format without wrapping quotes
- Lines wrapped at 90 characters for readability
- Main page includes `mainheader` and `footer` blocks
- Other pages exclude common blocks (header/footer)

### page-lists/{type}.txt
Tab-delimited page lists for each type:
```
{url}\t{title}
```

**Key features:**
- Clean filenames without `-pages` suffix
- Example files: `news-article.txt`, `00-main.txt`
- Sorted by URL for easy navigation
- One file per page type (23 total files)

## Page Types

The analyzer identifies 24 page types:

1. **Home Page** (00-main) - Main homepage
2. **Property Catalog** (property-catalog) - Property listing pages with filters, maps, and object lists (23 pages)
3. **Property Object** (property-object) - Individual property detail pages with breadcrumbs, gallery, agent info, mortgage calculator, and similar objects (36 pages)
4. **News Article** (news-article) - Individual news articles (1,246 pages)
5. **News List** (news-list) - News listing pages
6. **Service Page** (service-page) - Service description pages
7. **Service List** (service-list) - Service listing pages
8. **Contacts** (contacts) - Contact page
9. **About** (about) - About company page
10. **Vacancies** (vacancies) - Vacancies page
11. **Staff List** (staff-list) - Staff listing page
12. **Staff Profile** (staff-profile) - Individual staff profiles
13. **Promotions List** (promotions-list) - Promotions listing
14. **Promotion Detail** (promotion-detail) - Individual promotion pages
15. **FAQ List** (faq-list) - FAQ listing page
16. **Reviews List** (reviews-list) - Customer reviews
17. **Analytics** (analytics) - Analytics page
18. **New Buildings List** (new-buildings-list) - New buildings listing
19. **New Building Detail** (new-building-detail) - Individual new building pages
20. **Search Results** (search-results) - Search results pages
21. **User Account** (user-account) - User account pages (favorites, comparisons)
22. **System Page** (system-page) - System/utility pages
23. **Other Pages** (other-pages) - Other miscellaneous pages
24. Additional specialized page types as needed

### Property Page Classification

The analyzer distinguishes between two types of property pages with custom section extraction:

**Property Catalog** - Listing pages that show multiple properties (14 pages):
- City/area-based listings (e.g., `/arenda-kvartir-balashiha/`, `/kvartiri-v-balashihe/`)
- Category listings (e.g., `/1k-kvartira-zheleznodorozhnyy/`, `/студии-balashiha/`)
- Objects directory category pages (e.g., `/объекты/городская-недвижимость/`)
- Include filters, search forms, maps, and property card lists
- **Custom sections extracted**:
  - Breadcrumbs (`.breadcrumbs`)
  - Filters (`#search-inner`)
  - View control (`#search-gray > .sub-search`)
  - Map widget (`#map`)
  - Objects list (`.result-map__list`)

**Property Object** - Individual property detail pages (36 pages):
- Specific property URLs (e.g., `/объекты/городская-недвижимость/1-комнатная-квартира-в-г-балашиха-41/`)
- Include breadcrumbs, property details, image gallery, agent information, mortgage calculator, and similar properties
- **Custom sections extracted**:
  - Breadcrumbs (`.breadcrumbs`)
  - ID and view statistics (element containing "ID:" text)
  - Title (`.object-info__head`)
  - Address with badges (`.object-info__address`)
  - Gallery - main image and thumbnails (`.slick-gallery`)
  - Details - price, area, floor, links (`.object-characters__section`)
  - Realtor agent with contacts (`.object-characters__section`)
  - Mortgage calculator (`.ion-calc`)
  - Object description (`.object-info__text`)
  - Nearby infrastructure (`.object-info__infrastructure`)
  - Location map (`.serial-section > #map`)
  - Similar objects (`.object__similars`)

## Special Features

- **Main Page Handling**: The main page (`00-main`) includes
  `mainheader` and `footer` blocks, while other page types
  exclude these common blocks
- **Text Cleaning**: All text fields are cleaned of line
  breaks and multiple spaces
- **Ordered Output**: Main page always appears first in
  listings
- **Clean Formatting**: Markdown files use plain text without
  quotes for better readability
- **Line Wrapping**: Long lines in Markdown files are wrapped
  at 90 characters for improved readability
- **Block Order Preservation**: Content blocks maintain their
  order as they appear in the HTML document
- **Enhanced Detection**: Automatic detection of filter forms,
  content lists, and pagination elements
- **Tab-Delimited Lists**: Page list files use tabs as
  delimiters for easy parsing
- **Clean Filenames**: Page list files use simple `{type}.txt`
  naming without `-pages` suffix
- **Smart Directory Cleanup**: Automatically cleans the results directory before each run, recursively removing all nested files while gracefully skipping locked temp files (e.g., `.swp` files from editors)

## Project Structure

```
site-analysis/
├── sources/
│   └── zdkvartira.ru/  # Crawled HTML files
├── results/            # Analysis output
├── analyze-pages.py    # Main analysis script
├── TODO.md             # Project task list
├── package.json        # NPM package configuration
├── README.md           # This file
└── CHANGELOG.md        # Version history
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit issues
and pull requests.
