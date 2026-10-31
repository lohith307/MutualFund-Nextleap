# Mutual Fund FAQ Assistant

> **Facts-only. No investment advice.**

A lightweight RAG-based chatbot that answers factual queries about mutual fund schemes using official public sources. Built in the context of **Groww**.

---

## What It Does

- Answers objective, verifiable queries about mutual fund schemes (expense ratio, exit load, SIP amount, lock-in period, riskometer, benchmark, fund manager details, etc.)
- Retrieves information exclusively from official Groww scheme pages
- Returns concise responses (≤ 3 sentences) with a source citation and last-updated date
- Politely refuses investment advice, performance comparisons, and advisory queries

## What It Does NOT Do

- ❌ Provide investment advice or recommendations
- ❌ Compare fund performance or calculate returns
- ❌ Access or store any personal information (PAN, Aadhaar, OTP, etc.)
- ❌ Use third-party blogs or aggregator websites

---

## Selected Schemes (Corpus)

15 mutual fund scheme pages from Groww across 11 AMCs:

| # | Scheme | AMC | Category |
|---|---|---|---|
| 1 | Bandhan Small Cap Fund – Direct Growth | Bandhan MF | Small Cap |
| 2 | Axis Silver FOF – Direct Growth | Axis MF | Fund of Funds |
| 3 | Parag Parikh Long Term Value Fund – Direct Growth | PPFAS MF | Value / Flexi Cap |
| 4 | Motilal Oswal Most Focused Midcap 30 Fund – Direct Growth | Motilal Oswal MF | Mid Cap |
| 5 | Kotak Silver ETF FOF – Direct Growth | Kotak MF | Fund of Funds |
| 6 | HDFC Mid Cap Fund – Direct Growth | HDFC MF | Mid Cap |
| 7 | JioBlackRock Flexi Cap Fund – Direct Growth | JioBlackRock MF | Flexi Cap |
| 8 | HDFC Silver ETF FOF – Direct Growth | HDFC MF | Fund of Funds |
| 9 | SBI Nifty Next 50 Index Fund – Direct Growth | SBI MF | Index Fund |
| 10 | SBI PSU Fund – Direct Growth | SBI MF | Thematic / PSU |
| 11 | Nippon India Growth Mid Cap Fund – Direct Growth | Nippon India MF | Mid Cap |
| 12 | Bank of India Small Cap Fund – Direct Growth | BOI MF | Small Cap |
| 13 | ICICI Prudential Large Cap Fund – Direct Growth | ICICI Prudential MF | Large Cap |
| 14 | Bank of India Flexi Cap Fund – Direct Growth | BOI MF | Flexi Cap |
| 15 | Axis Liquid Direct Fund – Growth | Axis MF | Liquid / Debt |

---

## Architecture Overview (RAG)

```
User Query
    │
    ▼
Query Classifier ──► (advisory / PII) ──► Refusal Handler
    │
    ▼ (factual)
Retriever (ChromaDB semantic search)
    │
    ▼
LLM (facts-only prompt, temperature=0)
    │
    ▼
Response Formatter (≤3 sentences + citation + footer)
    │
    ▼
User
```

See [`Docs/architecture.md`](Docs/architecture.md) for the full system design.

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- An OpenAI API key **or** a Google Gemini API key

### 1. Clone the repository

```bash
git clone <repo-url>
cd MutualFund-Nextleap
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API key(s)
```

### 5. Run the data ingestion pipeline *(Phase 2)*

```bash
python -m src.ingestion.crawler
python -m src.ingestion.cleaner
python -m src.ingestion.chunker
python -m src.ingestion.embedder
```

### 6. Start the API backend *(Phase 4)*

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Launch the chat UI *(Phase 4)*

```bash
streamlit run src/ui/app.py
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
MutualFund-Nextleap/
├── data/
│   ├── raw/               # Downloaded HTML/PDF files (auto-generated)
│   ├── cleaned/           # Cleaned plain-text files (auto-generated)
│   └── metadata.json      # Corpus URL registry
├── corpus/
│   └── vector_store/      # ChromaDB index (auto-generated)
├── src/
│   ├── ingestion/         # Crawler, cleaner, chunker, embedder
│   ├── pipeline/          # Classifier, retriever, prompt, LLM, formatter
│   ├── api/               # FastAPI backend
│   └── ui/                # Streamlit chat interface
├── tests/                 # Unit & integration tests
├── Docs/                  # Project documentation
├── .env.example           # Environment variable template
├── requirements.txt       # Python dependencies
└── pyproject.toml         # Ruff + Black + pytest config
```

---

## Known Limitations

| Limitation | Details |
|---|---|
| Static corpus | Data reflects the state at last ingestion; not real-time |
| No live NAV | Cannot serve real-time NAV; directs users to official source |
| PDF parsing | Tables and charts in PDFs may not parse perfectly |
| Single-region corpus | Only 15 Groww scheme pages; not comprehensive across all AMCs |
| English only | Non-English queries are not supported |

---

## Disclaimer

> **Facts-only. No investment advice.**
>
> This assistant provides factual information about mutual fund schemes sourced from official public pages. It does not provide investment advice, recommendations, or performance projections. Always consult a SEBI-registered financial advisor before making investment decisions.

