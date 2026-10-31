"""
formatter.py — Response Validator & Formatter (Phase 3)

Enforces the output contract on every LLM-generated response:
  - Max 3 sentences for the main answer
  - Exactly one citation URL
  - Footer: "Last updated from sources: <date>"
  - Strips/redacts any echoed PII
  - Filters out unauthorized advisory phrases

Edge cases handled:
  - F-01: Missing citation URL injected from metadata
  - F-02: Multiple citations reduced to exactly one
  - F-03: Sentence count truncated to 3
  - F-04: Missing last_updated handled gracefully
  - F-06: PII echoed in response redacted
  - F-08: Advisory language detected and rejected
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# PII patterns to redact from LLM responses (F-06)
PII_REDACTIONS = [
    (re.compile(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b"), "[REDACTED_PAN]"),
    (re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"), "[REDACTED_AADHAAR]"),
    (re.compile(r"\b\d{6}\b"), "[REDACTED_OTP]"),
]

# Prohibited advisory phrases that cannot appear in answers (F-08)
ADVISORY_BLOCKLIST = [
    r"\brecommend\b",
    r"\bsuggest\b",
    r"\byou should invest\b",
    r"\bshould invest\b",
    r"\bbetter fund\b",
    r"\bgood choice\b",
    r"\bworth buying\b",
    r"\bbest option\b",
    r"\bstrong buy\b",
]

URL_REGEX = re.compile(r"https?://[^\s)\]]+")


def _split_into_sentences(text: str) -> list[str]:
    """
    Split text into individual sentences based on standard sentence-ending punctuation.
    Avoids splitting on common abbreviations like 'Rs.', 'vs.', 'e.g.', 'Dr.'.
    """
    cleaned = text.strip()
    # Protect common abbreviations from being treated as sentence ends
    protected = re.sub(r"\b(Rs|rs|Dr|Mr|Mrs|Ms|vs|e\.g|i\.e)\.", r"\1<DOT>", cleaned)
    # Split on . ! ? followed by whitespace or end of string
    parts = re.split(r"(?<=[.!?])\s+", protected)
    # Restore protected dots
    sentences = [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]
    return sentences


def _clean_body_text(text: str) -> str:
    """Strip any source or footer lines already produced by the LLM."""
    lines = text.splitlines()
    body_lines = []
    for line in lines:
        l_lower = line.lower().strip()
        if l_lower.startswith("source:") or l_lower.startswith("last updated from sources:"):
            continue
        if l_lower.startswith("disclaimer:"):
            continue
        body_lines.append(line)
    return " ".join(body_lines).strip()


def redact_pii(text: str) -> str:
    """Redact any PII numbers echoed in the text."""
    redacted = text
    for pattern, replacement in PII_REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def contains_advisory_language(text: str) -> bool:
    """Return True if text contains prohibited advisory advice keywords."""
    t_lower = text.lower()
    return any(re.search(pat, t_lower) for pat in ADVISORY_BLOCKLIST)


def validate_and_format(
    raw_response: str,
    source_url: Optional[str] = None,
    last_updated: Optional[str] = None,
    max_sentences: int = 3,
) -> str:
    """
    Validate, sanitize, and format an LLM response into the exact required contract.

    Output Contract:
        <Answer in ≤ 3 sentences>

        Source: <single URL>
        Last updated from sources: <YYYY-MM-DD or 'date unavailable'>

    Args:
        raw_response: Raw text returned by the LLM.
        source_url: Fallback or canonical citation URL from chunk metadata.
        last_updated: Last-updated date string from chunk metadata.
        max_sentences: Maximum allowed sentences in answer body (default 3).

    Returns:
        Formatted compliant response string.
    """
    if not raw_response or not raw_response.strip():
        raw_response = "I could not find this information in the official documents."

    # 1. Redact any PII (F-06)
    sanitized = redact_pii(raw_response)

    # 2. Check for prohibited advisory language (F-08)
    if contains_advisory_language(sanitized):
        logger.warning("Advisory phrase detected in LLM output; overriding with refusal.")
        return (
            "I cannot provide opinions or investment recommendations.\n\n"
            "Source: https://www.amfiindia.com/investor-corner\n"
            f"Last updated from sources: {last_updated or 'date unavailable'}"
        )

    # 3. Clean existing source/footer markers from raw text
    body = _clean_body_text(sanitized)

    # 4. Truncate to maximum sentences (F-03)
    sentences = _split_into_sentences(body)
    if len(sentences) > max_sentences:
        logger.info("Truncating response from %d to %d sentences.", len(sentences), max_sentences)
        sentences = sentences[:max_sentences]

    answer_text = " ".join(sentences).strip()

    # If the answer ended without punctuation, append period
    if answer_text and answer_text[-1] not in (".", "!", "?"):
        answer_text += "."

    # 5. Determine canonical citation URL (F-01, F-02)
    # If the text itself contained a URL, extract it
    extracted_urls = URL_REGEX.findall(sanitized)
    if source_url and source_url.strip():
        citation = source_url.strip()
    elif extracted_urls:
        citation = extracted_urls[0]
    else:
        citation = "https://groww.in/mutual-funds"

    # 6. Format footer date (F-04)
    date_str = last_updated.strip() if last_updated and last_updated.strip() else "date unavailable"

    # Assemble final output contract
    formatted = f"{answer_text}\n\nSource: {citation}\nLast updated from sources: {date_str}"
    return formatted
