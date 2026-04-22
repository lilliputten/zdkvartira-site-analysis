# Release v0.0.2: Smart Block Titles & Enhanced Element Detection

**Release Date:** April 22, 2026

## What's New

This release focuses on improving the readability and accuracy of block analysis by eliminating meaningless CSS class-based titles and adding detection for previously missing page elements.

## Key Features

### Smart Title Generation
Blocks now use meaningful headings or descriptions instead of technical CSS class names. For example:
- **Before:** "Bg White" (from `.bg-white.py-2.py-4`)
- **After:** "Текстовый информационный блок" (from description)

### Page Title Detection
Automatically detects and documents page titles (`p.caption`) across all page types, providing better context for page structure.

### Realty Card Detection
Added support for realty object cards (`.newhousing-item`) in new buildings list pages, capturing:
- Property name (`.newhousing-item__caption`)
- Location/type (`.newhousing-item__type`)
- Price information (`.newhousing-item__price`)
- Completion date (`.newhousing-item__release`)

### Enhanced Parent Selectors
Improved DOM context visibility with more specific parent selector generation, showing the actual HTML hierarchy instead of generic `html > body` paths.

### Cleaner Output
- All descriptions are now capitalized for consistency
- Removed redundant "CSS селектор:" references from descriptions
- Eliminated duplicate Heading/Description lines when used as titles
- Smart text wrapping at 90 characters for better readability

## Technical Improvements

### Intelligent Fallback Logic
When no heading exists, the system now uses description text as the title with smart filtering:
- Detects and skips generic patterns
- Caps title length at 80 characters
- Extracts first meaningful sentence from description

### CSS Utility Class Detection
Implemented regex-based detection to identify CSS utility classes (e.g., `.bg-white`, `.py-2`, `.pt-4`) and prevent them from generating meaningless titles.

### Enhanced Element Search
Added 'p' tag to the element search list, enabling detection of page title elements that were previously missed.

### Deduplication Logic
Automatic suppression of duplicate fields:
- No separate "**Heading:**" line when heading is used as title
- No separate "**Description:**" line when description becomes the title

## Impact Statistics

- **Pages Re-analyzed:** 1,374 HTML pages
- **Page Types:** 23 categories with improved documentation
- **Output Formats:** TXT, CSV, YAML, Markdown (all updated)
- **Documentation Quality:** Significantly improved readability and usefulness

## Example Improvements

### Before (v0.0.1)
```markdown
### 5. Bg White
- **Selector:** `.bg-white.py-2.py-4`
- **Parent:** `html > body`
- **Description:** Текстовый информационный блок
- **Пример содержимого:** В 97% случаев...
```

### After (v0.0.2)
```markdown
### 5. Текстовый информационный блок
- **Selector:** `.bg-white.py-2.py-4`
- **Parent:** `html > body`
- **Пример содержимого:** В 97% случаев...
```

## Updated Files

### Core Files
- [`analyze-pages.py`](analyze-pages.py): Core analysis engine improvements
  - Enhanced `generate_human_readable_title()` function
  - Added page title and realty card detection
  - Improved Markdown output logic

### Configuration
- [`package.json`](package.json): Version bump to 0.0.2
- [`CHANGELOG.md`](CHANGELOG.md): Detailed v0.0.2 release notes
- [`README.md`](README.md): Updated features section

### Generated Results
- `results/types.yaml`: Complete structured data regenerated
- `results/page-types/*.md`: All 23 page type documentation files updated
- `results/pages.txt` & `results/pages.csv`: Page lists (unchanged format)
- `results/page-lists/*.txt`: Organized page lists by type

## Use Cases

This release makes the generated documentation significantly more useful for:

1. **Frontend Developers**: Understanding page structure with meaningful block names
2. **Content Managers**: Identifying where specific content appears on pages
3. **SEO Specialists**: Analyzing page title placement and structure
4. **QA Engineers**: Verifying consistent block rendering across page types
5. **Web Scrapers**: Using accurate selectors and parent context for data extraction

## Links

- [Full Changelog](CHANGELOG.md)
- [Documentation](README.md)
- [Previous Release (v0.0.1)](https://github.com/your-repo/releases/tag/v0.0.1)

**Full Commit History:** [View all changes](https://github.com/your-repo/compare/v0.0.1...v0.0.2)
