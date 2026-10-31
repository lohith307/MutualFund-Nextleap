"""
crawler.py — URL Fetcher & Scraper (Phase 2)

Fetches HTML pages and downloads PDFs from the curated source URL list
defined in data/metadata.json. Saves raw content to data/raw/.

Responsibilities:
- Load URLs from metadata.json
- Fetch HTML with requests + BeautifulSoup (respecting robots.txt)
- Download PDFs as binary streams
- Apply rate limiting between requests
- Handle retries with exponential backoff (via tenacity)
- Log failed URLs without halting the pipeline
"""

# TODO (Phase 2): Implement crawl_all(), fetch_html(), download_pdf()

