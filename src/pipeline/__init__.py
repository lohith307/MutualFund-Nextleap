"""
src.pipeline — Mutual Fund FAQ Assistant RAG Pipeline

Exports:
    - query_pipeline(query: str) -> dict: End-to-end question answering pipeline
    - classify, QueryIntent, refusal_response
    - retrieve, RetrievalResult
    - generate
    - validate_and_format
    - build_prompt, SYSTEM_PROMPT
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from src.pipeline.classifier import QueryIntent, classify, refusal_response
from src.pipeline.formatter import validate_and_format
from src.pipeline.llm import generate
from src.pipeline.prompt import SYSTEM_PROMPT, build_prompt
from src.pipeline.retriever import retrieve

logger = logging.getLogger(__name__)


def query_pipeline(query: str) -> Dict[str, Any]:
    """
    Execute the full end-to-end RAG query pipeline for a user question.

    Steps:
      1. Classify intent (PII, Advisory, Comparative, Returns, Out of Scope, Factual)
      2. If non-factual: return standardized refusal directly
      3. Retrieve scheme-scoped chunks from ChromaDB (with BGE embeddings)
      4. If out-of-corpus / ambiguous / below threshold: return compliant fallback
      5. Construct prompt with retrieved chunks
      6. Infer facts-only answer from LLM
      7. Validate and format output (max 3 sentences + citation + footer)

    Returns:
      {
        "answer": str,
        "intent": str,
        "source_url": str,
        "last_updated": str,
        "status": "success" | "refusal" | "fallback",
        "retrieved_chunks": int,
      }
    """
    # ── Step 1: Query Intent Classification ───────────────────────────────────
    intent = classify(query)

    if intent != QueryIntent.FACTUAL:
        refusal_text = refusal_response(intent, query)
        return {
            "answer": refusal_text,
            "intent": intent.value,
            "source_url": "https://www.amfiindia.com/investor-corner",
            "last_updated": "date unavailable",
            "status": "refusal",
            "retrieved_chunks": 0,
        }

    # ── Step 2: Scheme-Aware Hybrid Retrieval ─────────────────────────────────
    res = retrieve(query)

    if res.status == "out_of_corpus":
        return {
            "answer": (
                "I could not find information about this scheme in the official documents.\n\n"
                "Source: https://groww.in/mutual-funds\n"
                "Last updated from sources: date unavailable"
            ),
            "intent": intent.value,
            "source_url": "https://groww.in/mutual-funds",
            "last_updated": "date unavailable",
            "status": "fallback",
            "retrieved_chunks": 0,
        }

    if res.status == "ambiguous":
        return {
            "answer": (
                "Please specify which mutual fund scheme you are inquiring about "
                "(for example: 'HDFC Mid Cap Fund' or 'Bandhan Small Cap Fund').\n\n"
                "Source: https://groww.in/mutual-funds\n"
                "Last updated from sources: date unavailable"
            ),
            "intent": intent.value,
            "source_url": "https://groww.in/mutual-funds",
            "last_updated": "date unavailable",
            "status": "fallback",
            "retrieved_chunks": 0,
        }

    if not res.has_context:
        return {
            "answer": (
                "I could not find this information in the official documents.\n\n"
                "Source: https://groww.in/mutual-funds\n"
                "Last updated from sources: date unavailable"
            ),
            "intent": intent.value,
            "source_url": "https://groww.in/mutual-funds",
            "last_updated": "date unavailable",
            "status": "fallback",
            "retrieved_chunks": 0,
        }

    # ── Step 3: Context Assembly & Prompt Construction ────────────────────────
    context_text = res.get_combined_context()
    user_prompt = build_prompt(context=context_text, question=query)

    # ── Step 4: LLM Inference ─────────────────────────────────────────────────
    raw_response = generate(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

    # ── Step 5: Validation & Formatting ───────────────────────────────────────
    final_answer = validate_and_format(
        raw_response=raw_answer if (raw_answer := raw_response) else "",
        source_url=res.source_url,
        last_updated=res.last_updated,
        max_sentences=3,
    )

    return {
        "answer": final_answer,
        "intent": intent.value,
        "source_url": res.source_url or "https://groww.in/mutual-funds",
        "last_updated": res.last_updated or "date unavailable",
        "status": "success",
        "retrieved_chunks": len(res.chunks),
    }


__all__ = [
    "query_pipeline",
    "classify",
    "QueryIntent",
    "refusal_response",
    "retrieve",
    "generate",
    "validate_and_format",
    "build_prompt",
    "SYSTEM_PROMPT",
]
