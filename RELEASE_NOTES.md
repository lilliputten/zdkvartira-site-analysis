# Release v0.0.3: Automatic Broken & Redirected Page Exclusion

**Release Date:** April 25, 2026

## What's New

This release introduces intelligent filtering to automatically exclude broken links and redirected pages from analysis, ensuring cleaner results focused only on valid, accessible content.

## Key Features

### Automatic Broken Link Exclusion
The analyzer now automatically detects and excludes pages that returned HTTP error status codes:
- **404 Not Found** - Pages that don't exist
- **500 Internal Server Error** - Pages with server errors
- Total excluded: **26 broken links** from `analyze-sources/broken-links.yaml`

### Automatic Redirect Exclusion
Pages that redirect to other URLs are now excluded from analysis:
- **301 Moved Permanently** - Permanent redirects
- **302 Found** - Temporary redirects
- Total excluded: **20 redirected pages** from `analyze-sources/redirected-pages.yaml`

### Smart URL Matching
The system constructs URLs from file paths and compares them against the exclusion list:
```python
# File: analyze-sources/zdkvartira.ru/news/some-article/index.html
# Constructed URL: https://zdkvartira.ru/news/some-article/
# If in exclusion set → Skip this file
```

### Enhanced Progress Reporting
Clear statistics displayed during execution:
```
Loading excluded URLs...
Loaded 26 broken links to exclude
Loaded redirected pages to exclude (total excluded: 46)
Total URLs to exclude: 46

Начинаю анализ страниц...
Найдено 1328 HTML файлов (46 excluded)
```

## Technical Improvements

### New Function: load_excluded_urls()
Added a dedicated function to load and merge exclusion lists from YAML files:
- Reads `analyze-sources/broken-links.yaml`
- Reads `analyze-sources/redirected-pages.yaml`
- Returns a unified set of URLs to exclude
- Includes error handling with warnings if files can't be loaded
- Located at lines 1197-1238 in `analyze-pages.py`

### Modified File Collection Logic
Enhanced the main file scanning loop to filter out excluded URLs:
- Constructs URL from each HTML file path before processing
- Checks against exclusion set using efficient hash lookup
- Tracks skipped count for reporting
- Only adds valid files to the processing queue

### Robust Error Handling
- Graceful fallback if YAML files are missing or corrupted
- Warning messages instead of crashes
- Continues analysis with available data

## Impact Statistics

- **Total URLs Excluded:** 46 (26 broken + 20 redirected)
- **Pages Analyzed:** ~1,328 (down from 1,374)
- **Analysis Quality:** Improved - no wasted processing on invalid pages
- **Result Accuracy:** Higher - only valid, accessible pages included
- **Processing Time:** Slightly faster due to fewer pages

## Benefits

### For Developers
✅ **Cleaner Data** - No broken pages polluting the analysis  
✅ **Faster Processing** - Fewer pages to parse and analyze  
✅ **Accurate Statistics** - Real counts of working pages only  

### For Content Managers
✅ **Relevant Results** - Focus on pages users can actually access  
✅ **Better Planning** - Understand actual site structure without dead ends  

### For SEO Specialists
✅ **Valid Pages Only** - Analysis reflects crawlable, indexable content  
✅ **Redirect Awareness** - Clear visibility into which pages redirect  

### For QA Teams
✅ **Quality Assurance** - Identifies problematic pages automatically  
✅ **Actionable Insights** - Shows exactly which URLs need fixing  

## Example Usage

### Before (v0.0.2)
```
Начинаю анализ страниц...
Найдено 1374 HTML файлов
Обработано 50/1374 страниц...
Обработано 100/1374 страниц...
...
Проанализировано 1374 страниц
```
*Note: Included 46 broken/redirected pages in analysis*

### After (v0.0.3)
```
Loading excluded URLs...
Loaded 26 broken links to exclude
Loaded redirected pages to exclude (total excluded: 46)
Total URLs to exclude: 46

Начинаю анализ страниц...
Найдено 1328 HTML файлов (46 excluded)
Обработано 50/1328 страниц...
Обработано 100/1328 страниц...
...
Проанализировано 1328 страниц
```
*Note: Automatically filtered out 46 problematic pages*

## Updated Files

### Core Files
- [`analyze-pages.py`](analyze-pages.py): 
  - Added `load_excluded_urls()` function (lines 1197-1238)
  - Modified `main()` function to use exclusion logic (lines 1263-1305)
  - Updated module docstring to document exclusion feature

### Configuration
- [`CHANGELOG.md`](CHANGELOG.md): Detailed v0.0.3 release notes
- [`RELEASE_NOTES.md`](RELEASE_NOTES.md): This comprehensive release announcement

### Generated Results
All output files will reflect the filtered page set:
- `results/pages.txt`: Reduced page count (excludes broken/redirected)
- `results/pages.csv`: Cleaner CSV with only valid pages
- `results/types.yaml`: Updated type distributions
- `results/page-types/*.md`: Documentation for actual working pages
- `results/page-lists/*.txt`: Accurate page lists by type

## Migration Guide

### For Existing Users
No migration needed! The script automatically uses the exclusion files if they exist:
1. Ensure `analyze-sources/broken-links.yaml` is present (from crawl-site output)
2. Ensure `analyze-sources/redirected-pages.yaml` is present (from crawl-site output)
3. Run `python analyze-pages.py` as usual
4. Exclusion happens automatically

### For New Users
The exclusion files are generated by the `crawl-site` tool:
```bash
# In crawl-site directory
pnpm scan --site-url=https://zdkvartira.ru
pnpm crawl --dest=./crawl-dest

# Copy to site-analysis
cp -r ../crawl-site/crawl-dest ./analyze-sources/zdkvartira.ru/
# Also copy the YAML reports
cp ../crawl-site/broken-links.yaml ./analyze-sources/
cp ../crawl-site/redirected-pages.yaml ./analyze-sources/

# Run analysis
python analyze-pages.py
```

## Known Limitations

- Exclusion relies on accurate crawl data from `crawl-site` tool
- If YAML files are missing, analysis continues without exclusions (with warning)
- URL matching is exact - trailing slashes must match between file paths and exclusion list

## Future Enhancements

Potential improvements for future releases:
- Configurable exclusion patterns (regex support)
- Manual exclusion list via command-line arguments
- Export of excluded pages report for review
- Integration with site health monitoring tools

## Use Cases

This release makes the tool more valuable for:

1. **Site Audits**: Focus analysis on working pages only
2. **Content Inventory**: Accurate counts of accessible content
3. **Migration Planning**: Understand actual vs. intended site structure
4. **Performance Testing**: Exclude error pages from load analysis
5. **SEO Analysis**: Crawl budget optimization insights
6. **Quality Metrics**: Track ratio of broken/redirected pages over time

## Links

- [Full Changelog](CHANGELOG.md)
- [Previous Release Notes (v0.0.2)](RELEASE_NOTES.md)
- [Documentation](README.md)
- [Project Setup Guide](QUICK_START.md)

**Full Commit History:** [View all changes](https://github.com/your-repo/compare/v0.0.2...v0.0.3)

---

## Summary

Version 0.0.3 delivers a significant quality improvement by automatically filtering out problematic pages. This ensures your analysis focuses on real, accessible content, making the generated documentation more accurate and actionable. The implementation is transparent, robust, and requires no configuration - it just works! 🚀