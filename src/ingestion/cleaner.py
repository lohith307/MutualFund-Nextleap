"""
cleaner.py — Document Cleaner: HTML / PDF → Plain Text (Phase 2)

Converts raw downloaded files from data/raw/ into clean plain text
and writes them to data/cleaned/.

Responsibilities:
- Strip HTML tags, nav/footer boilerplate (BeautifulSoup)
- Extract text from PDFs (PyMuPDF / pdfplumber)
- Normalize whitespace and remove empty lines
- Detect and skip empty documents post-cleaning
"""

# TODO (Phase 2): Implement clean_html(), clean_pdf(), clean_all()

