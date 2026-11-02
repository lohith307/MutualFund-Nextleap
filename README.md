---
title: Groww Mutual Fund FAQ Assistant
emoji: 📈
colorFrom: green
colorTo: emerald
sdk: streamlit
sdk_version: "1.40.1"
app_file: src/ui/app.py
pinned: false
license: mit
---

# Groww Mutual Fund FAQ Assistant (Facts-Only RAG Chatbot)

> **⚠️ Disclaimer:** *Facts-only. No investment advice.*  
> This assistant answers factual queries about mutual fund schemes strictly using official Groww scheme documentation. It does not provide investment advice, fund ratings, return calculations, performance comparisons, or personal recommendations.

[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40-FF4B4B.svg)](https://streamlit.io/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5.18-orange.svg)](https://www.trychroma.com/)
[![Groq](https://img.shields.io/badge/Groq-qwen--2.5--27b-f55036.svg)](https://groq.com/)
[![Scheduler](https://img.shields.io/badge/Scheduler-10%3A00%20AM%20IST-00D09C.svg)]()
[![Tests](https://img.shields.io/badge/Tests-149%20Passed-brightgreen.svg)]()
[![Live Demo](https://img.shields.io/badge/Live%20App-Streamlit%20Cloud-00D09C.svg)](https://mutualfund-nextleap.streamlit.app)
[![Deploy to Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://mutualfund-nextleap.streamlit.app)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/lohith307/MutualFund-Nextleap)

---

## 1. Project Overview

The **Mutual Fund FAQ Assistant** is a production-grade, compliance-first Retrieval-Augmented Generation (RAG) system built in the context of **Groww**. It serves factual and verifiable information for 15 prominent mutual fund schemes while deterministically blocking advisory questions, performance comparisons, and personally identifiable information (PII).

### What It Does
- Answers objective factual queries regarding:
  - **Expense Ratio (TER)** and annual fund charges
  - **Exit Load** structures, redemption slabs, and holding windows
  - **Minimum Investment Amounts** (SIP and Lumpsum)
  - **Lock-in Periods** (e.g., ELSS 3-year statutory lock-in)
  - **Riskometer Ratings** (Low, Moderate, Very High)
  - **Benchmark Indices** (e.g., Nifty Smallcap 250 TRI, Nifty 50 TRI)
  - **Fund Management Details** (fund manager names, tenure start date)
- Enforces concise answers (**≤ 3 sentences**).
- Appends an exact **source URL citation** and a `Last updated from sources: <YYYY-MM-DD>` footer.
- Politely refuses investment advice, comparative evaluations, and performance projections with educational references to [AMFI India](https://www.amfiindia.com/investor-corner).

### What It Does NOT Do
- ❌ **No Investment Advice:** Refuses questions like *"Should I invest in this fund?"* or *"Is this fund good for retirement?"*.
- ❌ **No Fund Comparisons:** Refuses *"Which fund is better between X and Y?"*.
- ❌ **No Return Calculations:** Refuses requests to calculate SIP maturity or historical returns.
- ❌ **Zero PII Exposure:** Automatically detects and refuses queries containing PAN, Aadhaar, OTPs, or bank account numbers without logging or storing them.
- ❌ **No Aggregator / Blog Scraping:** Operates exclusively over official Groww scheme documentation.

---

## 2. Selected Corpus (15 Groww Schemes)

The knowledge base covers 15 curated scheme pages across 11 Asset Management Companies (AMCs) and diverse categories:

| # | Scheme Name | AMC | Category | Official Source |
|---|---|---|---|---|
| 1 | **Bandhan Small Cap Fund** – Direct Growth | Bandhan Mutual Fund | Small Cap | [Groww Link](https://groww.in/mutual-funds/bandhan-small-cap-fund-direct-growth) |
| 2 | **Axis Silver FOF** – Direct Growth | Axis Mutual Fund | Fund of Funds | [Groww Link](https://groww.in/mutual-funds/axis-silver-fof-direct-growth) |
| 3 | **Parag Parikh Long Term Value Fund** – Direct Growth | PPFAS Mutual Fund | Flexi Cap / Value | [Groww Link](https://groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth) |
| 4 | **Motilal Oswal Most Focused Midcap 30 Fund** – Direct Growth | Motilal Oswal Mutual Fund | Mid Cap | [Groww Link](https://groww.in/mutual-funds/motilal-oswal-most-focused-midcap-30-fund-direct-growth) |
| 5 | **Kotak Silver ETF FOF** – Direct Growth | Kotak Mutual Fund | Fund of Funds | [Groww Link](https://groww.in/mutual-funds/kotak-silver-etf-fof-direct-growth) |
| 6 | **HDFC Mid Cap Fund** – Direct Growth | HDFC Mutual Fund | Mid Cap | [Groww Link](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth) |
| 7 | **JioBlackRock Flexi Cap Fund** – Direct Growth | JioBlackRock Mutual Fund | Flexi Cap | [Groww Link](https://groww.in/mutual-funds/jioblackrock-flexi-cap-fund-direct-growth) |
| 8 | **HDFC Silver ETF FOF** – Direct Growth | HDFC Mutual Fund | Fund of Funds | [Groww Link](https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth) |
| 9 | **SBI Nifty Next 50 Index Fund** – Direct Growth | SBI Mutual Fund | Index Fund | [Groww Link](https://groww.in/mutual-funds/sbi-nifty-next-50-index-fund-direct-growth) |
| 10 | **SBI PSU Fund** – Direct Growth | SBI Mutual Fund | Thematic / PSU | [Groww Link](https://groww.in/mutual-funds/sbi-psu-fund-direct-growth) |
| 11 | **Nippon India Growth Mid Cap Fund** – Direct Growth | Nippon India Mutual Fund | Mid Cap | [Groww Link](https://groww.in/mutual-funds/nippon-india-growth-mid-cap-fund-direct-growth) |
| 12 | **Bank of India Small Cap Fund** – Direct Growth | Bank of India Mutual Fund | Small Cap | [Groww Link](https://groww.in/mutual-funds/bank-of-india-small-cap-fund-direct-growth) |
| 13 | **ICICI Prudential Large Cap Fund** – Direct Growth | ICICI Prudential Mutual Fund | Large Cap | [Groww Link](https://groww.in/mutual-funds/icici-prudential-large-cap-fund-direct-growth) |
| 14 | **Bank of India Flexi Cap Fund** – Direct Growth | Bank of India Mutual Fund | Flexi Cap | [Groww Link](https://groww.in/mutual-funds/bank-of-india-flexi-cap-fund-direct-growth) |
| 15 | **Axis Liquid Direct Fund** – Growth | Axis Mutual Fund | Debt / Liquid | [Groww Link](https://groww.in/mutual-funds/axis-liquid-direct-fund-growth) |

---

## 3. Architecture & Tech Stack

```
               User Query (HTTP / Streamlit)
                           │
                           ▼
          ┌───────────────────────────────────┐
          │     Query Intent Classifier       │
          │   (PII / Advisory / Comparative)  │
          └─────────────────┬─────────────────┘
             Non-Factual    │        Factual Query
          ┌─────────────────┴─────────────────┐
          ▼                                   ▼
┌──────────────────┐               ┌─────────────────────────────────┐
│ Refusal Handler  │               │ Two-Stage Scheme-Aware Hybrid   │
│  + AMFI link     │               │           Retriever             │
└─────────┬────────┘               └────────────────┬────────────────┘
          │                                         │ Top Chunks
          │                                         ▼
          │                        ┌─────────────────────────────────┐
          │                        │     Deterministic Groq LLM      │
          │                        │ (llama-3.3-70b, temp=0, max=200)│
          │                        └────────────────┬────────────────┘
          │                                         │
          │                                         ▼
          │                        ┌─────────────────────────────────┐
          │                        │   Response Formatter & Guard    │
          │                        │ (≤ 3 sentences, citation, date) │
          │                        └────────────────┬────────────────┘
          │                                         │
          └─────────────────┬───────────────────────┘
                            ▼
              Client Response (FastAPI / UI)
```

| Component | Technology | Rationale |
|---|---|---|
| **LLM Provider** | **Groq Cloud** (`qwen/qwen3.8-27b`) | Sub-500ms deterministic inference (temp=0.0) with automatic multi-model fallback (`llama-3.1-8b`, `llama-3.3-70b`). |
| **Embeddings** | **BAAI/bge-small-en-v1.5** via `fastembed` | 100% free, runs locally on CPU via ONNX runtime, 384 dimensions, MTEB leader. |
| **Vector Database** | **ChromaDB 0.5.18** (Persistent, Local) | Fast metadata filtering with HNSWlib bounds protection preventing array errors. |
| **Chunking Engine** | **Section-Aware Chunker** | 135 atomic chunks enriched with verified Total Expense Ratios (TER) across 9 factual sections. |
| **API Backend** | **FastAPI** + **SlowAPI** | High-throughput async REST API with IP rate limiting and schema validation. |
| **User Interface** | **Streamlit 1.40+** (Groww Fintech Theme) | 4 interactive tabs, top KPI metric grid, and interactive sidebar scheme explorer with instant factsheets & 1-click action chips. |

*For complete details, see [`Docs/architecture.md`](Docs/architecture.md) and [`Docs/edge-cases.md`](Docs/edge-cases.md).*

---

## 4. Setup & Installation

### Prerequisites
- Python **3.9**, **3.10**, or **3.11**
- Free Groq API Key (from [console.groq.com](https://console.groq.com)) or Gemini / OpenAI key

### Step 1: Clone Repository
```bash
git clone https://github.com/lohith307/MutualFund-Nextleap.git
cd MutualFund-Nextleap
```

### Step 2: Set Up Virtual Environment
```powershell
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env` and insert your API key:
```bash
cp .env.example .env
```
Inside `.env`:
```env
# Primary LLM (Groq)
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_PROVIDER=groq
LLM_MODEL=qwen/qwen3.8-27b

# Embeddings (Local, Free)
EMBEDDING_PROVIDER=bge
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DEVICE=cpu

# Vector Store
VECTOR_STORE_PATH=corpus/vector_store
VECTOR_STORE_COLLECTION=mutual_fund_faq
```

### Step 5: Run Ingestion Pipeline (One-Time Setup)
All 15 Groww schemes are already indexed in `corpus/vector_store/`. If you want to re-run ingestion from scratch:
```powershell
# 1. Fetch raw HTML
python -m src.ingestion.fetch

# 2. Parse factual sections
python -m src.ingestion.parse

# 3. Create section-aware chunks
python -m src.ingestion.chunker

# 4. Embed into ChromaDB
python -m src.ingestion.embedder
```

---

## 5. Usage & Running the Services

### Start the FastAPI Backend
```powershell
.\venv\Scripts\uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)
- Schemes list: [http://localhost:8000/schemes](http://localhost:8000/schemes)

#### Example API Request
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the exit load for Parag Parikh Flexi Cap Fund?"}'
```

#### Example API Response
```json
{
  "answer": "Parag Parikh Flexi Cap Fund levies an exit load of 2.0% if redeemed within 365 days, and 1.0% if redeemed between 366 and 730 days of investment. No exit load applies after 730 days.\n\nSource: https://groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth\nLast updated from sources: 2026-10-31",
  "source": "https://groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth",
  "source_url": "https://groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth",
  "last_updated": "2026-10-31",
  "intent": "factual",
  "status": "success",
  "retrieved_chunks": 5
}
```

---

### Start the Presentation Streamlit UI
```powershell
.\venv\Scripts\streamlit run src/ui/app.py
```
Opens in your browser at `http://localhost:8501`. Features include:
- **Interactive Sidebar Scheme Navigator:** Search and select any mutual fund from the dropdown to reveal an instant factsheet card (TER, Exit Load, Manager, Min SIP) and 4 one-click query buttons (`⚡ TER`, `🚪 Exit Load`, `👤 Manager`, `💰 Min SIP`).
- **Tab 1: 💬 AI Chat Assistant:** Top KPI metric cards, category filter chips (Small Cap, Mid Cap, Flexi Cap, Large Cap, Debt), dynamic 1-click prompt cards, and conversational message thread with verified citation pills (`↗`).
- **Tab 2: 🏢 Scheme Directory & Factsheets:** Searchable 15-fund factsheet grid with stats table and 3 direct query buttons per card.
- **Tab 3: ⏰ Daily Ingestion Scheduler:** Real-time scheduler countdown (10:00 AM IST daily), pipeline flow diagram, and 1-click manual sync execution button.
- **Tab 4: ⚖️ Regulatory Compliance:** SEBI/AMFI compliance guardrail breakdown and educational investor links.

---

### Run the Daily Ingestion Scheduler (Phase 7)
The automated scheduler synchronizes scheme factsheets and the ChromaDB index daily at **10:00 AM IST** (`Asia/Kolkata`):

```powershell
# Check current schedule and last execution telemetry
.\venv\Scripts\python -m src.scheduler --status

# Trigger ingestion pipeline immediately
.\venv\Scripts\python -m src.scheduler --now

# Run scheduler as a continuous foreground daemon service
.\venv\Scripts\python -m src.scheduler --daemon
```

FastAPI scheduler REST endpoints:
- `GET /scheduler/status` — Returns schedule, next fire time (10:00 AM IST), and last execution statistics.
- `POST /scheduler/trigger` — Triggers an asynchronous re-ingestion task in the background.

---

### Cloud Deployment & Live Production URL

The application is deployed live with zero cold-start delay:

1. **Live Streamlit Community Cloud Dashboard:**
   - **Production URL:** **[`https://mutualfund-nextleap.streamlit.app`](https://mutualfund-nextleap.streamlit.app)**
   - Pre-indexed ChromaDB vector store with self-healing cold-start loading.
2. **FastAPI + Standalone Web UI on Render:**
   - Deployable via `render.yaml` or Docker Compose.
3. **24/7 Always-On (Zero Sleep):**
   - GitHub Actions workflow [`.github/workflows/keep_alive.yml`](.github/workflows/keep_alive.yml) pings `/health` every 12 minutes to keep free-tier instances awake 24/7.
   - For complete step-by-step instructions, see [`Docs/deployment.md`](Docs/deployment.md) and [`Docs/deployment-plan.md`](Docs/deployment-plan.md).

---

## 6. Testing & Quality Assurance

The project includes an automated test suite with **149 tests** covering all phases:

```powershell
.\venv\Scripts\pytest tests/ --no-cov -v
```

### Test Suite Structure
| Test File | Description | Test Count |
|---|---|---|
| [`tests/test_classifier.py`](tests/test_classifier.py) | Intent classification (Factual, Advisory, Comparative, PII, Returns) | 26 |
| [`tests/test_retriever.py`](tests/test_retriever.py) | Two-stage hybrid retriever, scheme isolation, section boost | 8 |
| [`tests/test_formatter.py`](tests/test_formatter.py) | ≤ 3 sentences truncation, single URL citation, footer format | 8 |
| [`tests/test_refusal.py`](tests/test_refusal.py) | Refusal responses and AMFI educational guidance link | 7 |
| [`tests/test_api.py`](tests/test_api.py) | FastAPI endpoints (`/health`, `/schemes`, `/query`) & validations | 13 |
| [`tests/test_scheduler.py`](tests/test_scheduler.py) | Daily 10:00 AM IST scheduler, triggers, persistence & API endpoints | 12 |
| [`tests/test_e2e.py`](tests/test_e2e.py) | 10 official end-to-end representative queries | 10 |
| [`tests/test_compliance.py`](tests/test_compliance.py) | 7-point regulatory compliance verification suite | 7 |
| [`tests/test_chunker.py`](tests/test_chunker.py) | Section-aware chunking rules & token boundaries | 33 |
| [`tests/test_embedder.py`](tests/test_embedder.py) | BGE-small embeddings & ChromaDB persistent indexing | 3 |
| [`tests/test_ingestion.py`](tests/test_ingestion.py) | Web scraping, HTML parsing, metadata integrity | 16 |
| [`tests/test_pipeline.py`](tests/test_pipeline.py) | End-to-end pipeline orchestration | 6 |
| **Total** | | **149 Passed** |

---

## 7. Known Limitations

1. **Static Corpus:** The vector database reflects information scraped from Groww as of October 2026. Changes made by AMCs after the fetch date require re-running `fetch.py` and `embedder.py`.
2. **No Real-time NAV:** The assistant does not serve real-time NAV tickers; users are referred to the official Groww scheme page.
3. **15 Scheme Scope:** Only queries pertaining to the 15 indexed schemes are answered factually; other schemes trigger polite out-of-corpus fallbacks.
4. **English Language Only:** Queries in other languages are not supported in this version.

---

## 8. Regulatory Compliance Sign-Off

- [x] **No Investment Advice:** No response ever recommends buying, selling, or holding a fund.
- [x] **No Performance Calculations:** No calculations or comparisons of historical returns.
- [x] **Verified Citations:** Every factual answer includes exactly one official Groww scheme URL.
- [x] **Footer Timestamp:** Every factual answer appends `Last updated from sources: <date>`.
- [x] **Educational Refusal:** Every non-factual query receives a polite refusal pointing to AMFI India.
- [x] **PII Protection:** PAN, Aadhaar, and OTPs are rejected on input and never stored or echoed.
- [x] **Persistent Disclaimer:** Displayed prominently in the UI and in all refusal messages.

---

## 9. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
