"""
retriever.py — Two-Stage Scheme-Aware Hybrid Retriever (Phase 3)

Retrieves the most relevant factual context chunks from ChromaDB for a given
user query while eliminating cross-scheme contamination.

Features:
  1. Scheme Resolution: Identifies target scheme from KNOWN_SCHEMES.
     - Known scheme     → Scopes vector search to where={"scheme": matched_scheme}
     - Out-of-corpus    → Flags out_of_corpus (e.g. Quant Small Cap)
     - Missing scheme   → Flags ambiguous if question requires a specific fund
  2. BGE Embedding Search:
     - Uses BGE-small with query instruction prefix
  3. Section Re-Ranking:
     - Boosts chunks matching detected section (e.g. expense_ratio)
  4. Threshold Guardrail:
     - Flags below_threshold if max similarity < 0.65 (avoids hallucination)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from src.ingestion.embedder import get_chroma_client, get_embedding_function, get_or_create_collection
from src.pipeline.classifier import KNOWN_SCHEMES, detect_scheme, detect_section

logger = logging.getLogger(__name__)

# Minimum similarity threshold to prevent hallucinated answers (R-01)
DEFAULT_THRESHOLD = float(os.getenv("RETRIEVER_SIMILARITY_THRESHOLD", "0.65"))
DEFAULT_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "3"))


class RetrievalResult:
    """Encapsulates retrieved chunks and metadata for the LLM prompt builder."""

    def __init__(
        self,
        chunks: List[Dict[str, Any]],
        status: str = "success",
        scheme: Optional[str] = None,
        section: Optional[str] = None,
        source_url: Optional[str] = None,
        last_updated: Optional[str] = None,
        max_score: float = 0.0,
    ):
        self.chunks = chunks
        self.status = status  # "success", "out_of_corpus", "ambiguous", "below_threshold"
        self.scheme = scheme
        self.section = section
        self.source_url = source_url
        self.last_updated = last_updated
        self.max_score = max_score

    @property
    def has_context(self) -> bool:
        return self.status == "success" and len(self.chunks) > 0

    def get_combined_context(self) -> str:
        """Format retrieved chunk texts into a coherent context block for LLM."""
        if not self.chunks:
            return ""
        return "\n\n---\n\n".join(c["text"] for c in self.chunks)


def _is_unrecognized_scheme_query(query: str, detected_scheme: Optional[str]) -> bool:
    """
    Check if the user is asking about an explicit fund scheme that is NOT
    in our 15 curated schemes (edge case C-04).
    """
    if detected_scheme:
        return False

    q_lower = query.lower()
    common_amc_brands = [
        "quant", "mirae", "tata", "franklin", "uti", "dsp", "edelweiss",
        "canara robeco", "invesco", "sundaram", "pgim", "navi", "whiteoak",
    ]
    has_amc = any(b in q_lower for b in common_amc_brands)
    has_fund_word = any(w in q_lower for w in ["fund", "scheme", "etf", "direct growth", "regular"])

    return has_amc and has_fund_word


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    threshold: float = DEFAULT_THRESHOLD,
    collection: Optional[Any] = None,
    embedding_fn: Optional[Any] = None,
) -> RetrievalResult:
    """
    Perform Two-Stage Scheme-Aware Hybrid Retrieval for a query.

    Args:
        query: User input query string.
        top_k: Number of chunks to retrieve.
        threshold: Minimum cosine similarity score.
        collection: Optional Chroma collection override (for testing).
        embedding_fn: Optional embedding function override (for testing).

    Returns:
        RetrievalResult instance.
    """
    if not query or not query.strip():
        return RetrievalResult(chunks=[], status="below_threshold")

    matched_scheme = detect_scheme(query)
    matched_section = detect_section(query)

    # ── Check for explicit out-of-corpus fund queries ─────────────────────────
    if _is_unrecognized_scheme_query(query, matched_scheme):
        logger.info("Out-of-corpus fund query detected: '%s'", query)
        return RetrievalResult(chunks=[], status="out_of_corpus")

    # ── Check if query asks for fund-specific facts without a fund name ───────
    needs_specific_fund = matched_section in (
        "expense_ratio", "exit_load", "minimum_investment", "fund_management", "benchmark",
    )
    if not matched_scheme and needs_specific_fund and "download" not in query.lower():
        logger.info("Ambiguous fund query: missing scheme name in '%s'", query)
        return RetrievalResult(chunks=[], status="ambiguous", section=matched_section)

    # ── ChromaDB Retrieval ────────────────────────────────────────────────────
    if collection is None:
        collection = get_or_create_collection()

    if embedding_fn is None:
        embedding_fn = get_embedding_function()

    query_embedding = embedding_fn.embed_query(query)

    # Apply scheme scope filter when target scheme is known
    where_filter = {"scheme": matched_scheme} if matched_scheme else None

    # Fetch extra candidates if re-ranking, capped to scheme chunk bounds
    fetch_k = top_k * 2 if matched_section else top_k
    target_k = min(fetch_k, 5) if where_filter else min(fetch_k, collection.count() or 1)

    try:
        query_res = collection.query(
            query_embeddings=[query_embedding],
            n_results=target_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.warning("Filtered ChromaDB query failed (%s), querying without where clause", exc)
        query_res = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count() or 1),
            include=["documents", "metadatas", "distances"],
        )

    docs = query_res.get("documents", [[]])[0]
    metas = query_res.get("metadatas", [[]])[0]
    dists = query_res.get("distances", [[]])[0]

    if not docs:
        return RetrievalResult(chunks=[], status="below_threshold")

    candidates = []
    for doc, meta, dist in zip(docs, metas, dists):
        sim = 1.0 - dist if dist is not None else 0.0

        # Section boost: if chunk matches detected topic, apply slight score bump
        if matched_section and meta.get("section") == matched_section:
            sim += 0.05

        candidates.append({
            "text": doc,
            "scheme": meta.get("scheme", ""),
            "section": meta.get("section", ""),
            "source_url": meta.get("source_url", ""),
            "last_updated": meta.get("last_updated", ""),
            "score": sim,
        })

    # Sort by boosted score
    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected_chunks = candidates[:top_k]

    max_score = selected_chunks[0]["score"] if selected_chunks else 0.0

    if max_score < threshold:
        logger.info("Top chunk similarity (%.3f) below threshold (%.2f)", max_score, threshold)
        return RetrievalResult(
            chunks=[],
            status="below_threshold",
            max_score=max_score,
            scheme=matched_scheme,
        )

    # Primary source URL & date from the rank-1 chunk
    primary_source = selected_chunks[0].get("source_url")
    primary_date = selected_chunks[0].get("last_updated")

    return RetrievalResult(
        chunks=selected_chunks,
        status="success",
        scheme=matched_scheme or selected_chunks[0].get("scheme"),
        section=matched_section,
        source_url=primary_source,
        last_updated=primary_date,
        max_score=max_score,
    )
