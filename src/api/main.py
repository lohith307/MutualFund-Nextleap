"""
main.py — FastAPI Application (Phase 4)

Exposes REST endpoints consumed by the Streamlit frontend and external callers:
  POST /query   — Accepts a user question and returns a facts-only answer.
  GET  /health  — Health check (verifies API, ChromaDB vector store, and scheme metadata).
  GET  /schemes — Lists the 15 covered Groww mutual fund schemes.

Security & Resilience:
  - Rate limiting via slowapi (60 req/minute per IP)
  - Input validation (Pydantic schema, length bounds, whitespace check)
  - CORS middleware configured for Streamlit UI
  - Stack trace protection (no internal errors leaked)
"""

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.pipeline import query_pipeline

load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mutual_fund_faq.api")

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Mutual Fund FAQ Assistant API",
    description="Compliant, facts-only RAG assistant for 15 Groww mutual fund schemes.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows Streamlit UI on any local/network port
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Request / Response Schemas ────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The mutual fund question to answer.",
        examples=["What is the expense ratio of Nippon India Small Cap Fund?"],
    )


class QueryResponse(BaseModel):
    answer: str = Field(..., description="The facts-only answer or refusal message.")
    source: str = Field(..., description="URL citation for the answer.")
    source_url: str = Field(..., description="Alias for source URL citation.")
    last_updated: str = Field(..., description="Source last updated timestamp.")
    intent: str = Field(..., description="Detected query intent.")
    status: str = Field(..., description="Status: 'success', 'refusal', or 'fallback'.")
    retrieved_chunks: int = Field(default=0, description="Number of retrieved context chunks.")


class HealthResponse(BaseModel):
    status: str
    vector_store: str
    chunks_indexed: int
    schemes_available: int
    llm_provider: str
    llm_model: str


class SchemeInfo(BaseModel):
    name: str
    category: str
    url: str
    last_updated: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=FileResponse, tags=["UI"])
def serve_ui():
    """
    Serve the Stitch-grade Groww RAG Chat web interface directly from FastAPI.
    """
    from pathlib import Path
    ui_path = Path("src/ui/index.html")
    if ui_path.exists():
        return FileResponse(ui_path)
    return HTMLResponse("<h1>Groww Mutual Fund FAQ Assistant</h1><p>Visit /docs for API documentation.</p>")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    """
    Check the operational status of the service, vector store, and metadata.
    """
    import json
    from pathlib import Path
    import chromadb

    db_path = os.getenv("VECTOR_STORE_PATH", "corpus/vector_store")
    collection_name = os.getenv("VECTOR_STORE_COLLECTION", "mutual_fund_faq")
    metadata_path = Path("data/metadata.json")

    chunks_count = 0
    vector_store_status = "unavailable"

    try:
        if os.path.exists(db_path):
            client = chromadb.PersistentClient(path=db_path)
            collection = client.get_collection(name=collection_name)
            chunks_count = collection.count()
            vector_store_status = "ready"
    except Exception as exc:
        logger.warning("Vector store health check issue: %s", exc)
        vector_store_status = f"degraded: {str(exc)}"

    schemes_count = 0
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                if isinstance(meta, dict) and "sources" in meta:
                    schemes_count = len(meta["sources"])
                elif isinstance(meta, dict):
                    schemes_count = len(meta)
        except Exception:
            pass

    return HealthResponse(
        status="ok",
        vector_store=vector_store_status,
        chunks_indexed=chunks_count,
        schemes_available=schemes_count,
        llm_provider=os.getenv("LLM_PROVIDER", "groq"),
        llm_model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
    )


@app.get("/schemes", response_model=List[SchemeInfo], tags=["Schemes"])
def list_schemes() -> List[SchemeInfo]:
    """
    Return all 15 Groww mutual fund schemes covered by the knowledge base.
    """
    import json
    from pathlib import Path

    metadata_path = Path("data/metadata.json")
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Scheme metadata not found.")

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        result: List[SchemeInfo] = []
        sources = data.get("sources", []) if isinstance(data, dict) else []
        for item in sources:
            result.append(
                SchemeInfo(
                    name=item.get("scheme", "Unknown Scheme"),
                    category=item.get("category", "Equity"),
                    url=item.get("url", "https://groww.in/mutual-funds"),
                    last_updated=item.get("last_fetched", "date unavailable"),
                )
            )
        return sorted(result, key=lambda s: s.name)
    except Exception as exc:
        logger.error("Failed to read scheme metadata: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve schemes.")


@app.post("/query", response_model=QueryResponse, tags=["RAG"])
@limiter.limit("60/minute")
def query_faq(request: Request, body: QueryRequest) -> QueryResponse:
    """
    Process a mutual fund question via the RAG pipeline.

    - Returns factual answers with citations for valid queries.
    - Returns standardized refusal with AMFI link for advisory or PII queries.
    - Strictly avoids investment advice or performance promises.
    """
    question = body.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or purely whitespace.",
        )

    try:
        logger.info("Processing query: %s", question[:80])
        result = query_pipeline(question)

        source = result.get("source_url") or "https://groww.in/mutual-funds"
        return QueryResponse(
            answer=result["answer"],
            source=source,
            source_url=source,
            last_updated=result.get("last_updated") or "date unavailable",
            intent=result.get("intent", "unknown"),
            status=result.get("status", "success"),
            retrieved_chunks=result.get("retrieved_chunks", 0),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unhandled error processing query '%s': %s", question[:50], exc, exc_info=True)
        # Avoid exposing raw stack trace to caller
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request. Please try again later.",
        )
