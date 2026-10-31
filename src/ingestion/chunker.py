"""
chunker.py — Section-Aware Hybrid Text Chunker

Reads parsed JSON files from data/cleaned/<slug>.json (output of parse.py)
and produces chunks ready for embedding into the vector store.

Chunking Strategy: Section-Aware Hybrid
----------------------------------------
Since parse.py tags every line into one of 9 named sections, we exploit
that structure to keep factually coherent content together:

  • PRIMARY  — 1 section = 1 chunk (for sections ≤ MAX_LINES_PER_CHUNK)
               Keeps "expense ratio", "exit load", "fund manager" facts intact.
  • FALLBACK — RecursiveCharacterTextSplitter within sections > MAX_LINES_PER_CHUNK
               Applies only to large "overview" sections.
  • SKIP     — "_unclassified" section is never embedded (noise).

Chunk metadata schema:
  {
    "chunk_id":    "<slug>_<section>_<index>",  # stable upsert key
    "scheme":      "HDFC Mid Cap Fund",
    "amc":         "HDFC Mutual Fund",
    "category":    "Mid Cap",
    "section":     "expense_ratio",             # enables retrieval filtering
    "source_url":  "https://groww.in/...",
    "last_updated": "2026-10-29",
    "text":        "Expense Ratio: 1.45%..."
  }

Usage:
    python -m src.ingestion.chunker            # chunk all cleaned files
    python -m src.ingestion.chunker --slug hdfc-mid-cap-fund-direct-growth
    python -m src.ingestion.chunker --dry-run  # print chunks without saving

Output:
    data/chunks/<slug>.json  — list of chunk dicts, ready for embedder.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
CLEANED_DIR = ROOT / "data" / "cleaned"
CHUNKS_DIR = ROOT / "data" / "chunks"

# ── Chunking parameters (from implementation plan §2.4) ───────────────────────
MAX_LINES_PER_CHUNK = 80        # sections with more lines are split further
FALLBACK_CHUNK_SIZE = 1600      # ~400 tokens × ~4 chars/token
FALLBACK_CHUNK_OVERLAP = 200    # ~50 tokens overlap
SKIP_SECTIONS = {"_unclassified"}  # never embed these

# Sections that must ALWAYS remain as a single chunk (never split)
# These are factual units where splitting destroys answer quality.
ATOMIC_SECTIONS = {
    "expense_ratio",
    "exit_load",
    "minimum_investment",
    "benchmark",
    "fund_management",
    "tax",
    "investment_objective",
    "fund_house",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── LangChain splitter (used only for large overview sections) ────────────────
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=FALLBACK_CHUNK_SIZE,
    chunk_overlap=FALLBACK_CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_chunk_id(slug: str, section: str, index: int) -> str:
    """
    Generate a stable, unique chunk ID used as the ChromaDB upsert key.
    Format: <slug>_<section>_<zero-padded-index>
    """
    return f"{slug}__{section}__{index:03d}"


def _make_content_hash(text: str) -> str:
    """Short SHA-256 hash of chunk text for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _build_chunk(
    slug: str,
    section: str,
    index: int,
    text: str,
    meta: dict,
) -> dict:
    """
    Assemble a single chunk dict with text and all required metadata.

    Args:
        slug:    File slug (e.g. 'hdfc-mid-cap-fund-direct-growth')
        section: Section name (e.g. 'expense_ratio')
        index:   Position within this section's chunks (0-based)
        text:    Chunk text content
        meta:    Source metadata from the parsed document

    Returns:
        Chunk dict with chunk_id, text, and all metadata fields.
    """
    return {
        "chunk_id": _make_chunk_id(slug, section, index),
        "content_hash": _make_content_hash(text),
        "text": text.strip(),
        # ── Source metadata ───────────────────────────────────────────────
        "scheme": meta.get("scheme", ""),
        "amc": meta.get("amc", ""),
        "category": meta.get("category", ""),
        "section": section,
        "source_url": meta.get("url", ""),
        "last_updated": meta.get("parsed_at", "")[:10],  # YYYY-MM-DD only
        "slug": slug,
    }


# ── Core chunking logic ───────────────────────────────────────────────────────

def chunk_section(
    slug: str,
    section: str,
    lines: list[str],
    meta: dict,
) -> list[dict]:
    """
    Produce one or more chunks from a single named section.

    Decision tree:
      1. Skip if section is in SKIP_SECTIONS (e.g. '_unclassified')
      2. Atomic sections → always 1 chunk regardless of length
      3. Lines ≤ MAX_LINES_PER_CHUNK → 1 chunk
      4. Lines > MAX_LINES_PER_CHUNK → split with RecursiveCharacterTextSplitter

    Args:
        slug:    Document slug
        section: Section name
        lines:   List of text lines belonging to this section
        meta:    Document-level metadata

    Returns:
        List of chunk dicts (empty list if section is skipped or empty)
    """
    # ── 1. Skip unwanted sections ─────────────────────────────────────────────
    if section in SKIP_SECTIONS:
        logger.debug("Skipping section '%s' for %s", section, slug)
        return []

    if not lines:
        return []

    full_text = "\n".join(lines)

    # ── 2. Atomic sections — always one chunk ─────────────────────────────────
    if section in ATOMIC_SECTIONS:
        logger.debug(
            "Atomic section '%s' → 1 chunk (%d lines) for %s",
            section, len(lines), slug,
        )
        return [_build_chunk(slug, section, 0, full_text, meta)]

    # ── 3. Small non-atomic section — single chunk ────────────────────────────
    if len(lines) <= MAX_LINES_PER_CHUNK:
        logger.debug(
            "Small section '%s' → 1 chunk (%d lines) for %s",
            section, len(lines), slug,
        )
        return [_build_chunk(slug, section, 0, full_text, meta)]

    # ── 4. Large section — split with RecursiveCharacterTextSplitter ──────────
    logger.info(
        "Large section '%s' (%d lines) → splitting for %s",
        section, len(lines), slug,
    )
    split_texts = _splitter.split_text(full_text)
    chunks = []
    for i, text in enumerate(split_texts):
        if text.strip():
            chunks.append(_build_chunk(slug, section, i, text, meta))
    return chunks


def chunk_document(parsed_doc: dict) -> list[dict]:
    """
    Produce all chunks for a single parsed document.

    Args:
        parsed_doc: Dict loaded from data/cleaned/<slug>.json

    Returns:
        List of chunk dicts across all sections.
    """
    slug = parsed_doc.get("slug", "unknown")
    sections = parsed_doc.get("sections", {})

    if not sections:
        logger.warning("No sections found in parsed doc: %s", slug)
        return []

    meta = {
        "scheme": parsed_doc.get("scheme", ""),
        "amc": parsed_doc.get("amc", ""),
        "category": parsed_doc.get("category", ""),
        "url": parsed_doc.get("url", ""),
        "parsed_at": parsed_doc.get("parsed_at", ""),
    }

    all_chunks: list[dict] = []
    section_summary: dict[str, int] = {}

    for section, lines in sections.items():
        chunks = chunk_section(slug, section, lines, meta)
        all_chunks.extend(chunks)
        if chunks:
            section_summary[section] = len(chunks)

    logger.info(
        "%s → %d chunks across sections: %s",
        slug,
        len(all_chunks),
        section_summary,
    )
    return all_chunks


def save_chunks(slug: str, chunks: list[dict]) -> Path:
    """Save chunk list to data/chunks/<slug>.json."""
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CHUNKS_DIR / f"{slug}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d chunks → %s", len(chunks), out_path.relative_to(ROOT))
    return out_path


# ── Pipeline runner ───────────────────────────────────────────────────────────

def chunk_all(dry_run: bool = False) -> list[dict]:
    """
    Chunk all cleaned JSON files in data/cleaned/.

    Args:
        dry_run: If True, print chunks without writing to disk.

    Returns:
        Flat list of all chunks across all documents.
    """
    cleaned_files = sorted(CLEANED_DIR.glob("*.json"))

    if not cleaned_files:
        logger.warning(
            "No cleaned JSON files found in %s. Run parse.py first.",
            CLEANED_DIR,
        )
        return []

    all_chunks: list[dict] = []
    total_docs = 0
    skipped_docs = 0

    for path in cleaned_files:
        with open(path, encoding="utf-8") as f:
            try:
                parsed_doc = json.load(f)
            except json.JSONDecodeError as exc:
                logger.error("Failed to parse JSON %s: %s", path.name, exc)
                skipped_docs += 1
                continue

        slug = parsed_doc.get("slug", path.stem)
        chunks = chunk_document(parsed_doc)

        if not chunks:
            logger.warning("No chunks produced for: %s", slug)
            skipped_docs += 1
            continue

        if dry_run:
            print(f"\n{'='*60}")
            print(f"Document: {slug}  ({len(chunks)} chunks)")
            print(f"{'='*60}")
            for c in chunks:
                print(f"\n  [{c['section']}] chunk_id={c['chunk_id']}")
                print(f"  {c['text'][:200]}{'...' if len(c['text']) > 200 else ''}")
        else:
            save_chunks(slug, chunks)

        all_chunks.extend(chunks)
        total_docs += 1

    logger.info(
        "Chunking complete — docs: %d | skipped: %d | total chunks: %d",
        total_docs,
        skipped_docs,
        len(all_chunks),
    )

    # Print section distribution summary
    from collections import Counter
    section_counts = Counter(c["section"] for c in all_chunks)
    logger.info("Chunks by section: %s", dict(section_counts.most_common()))

    return all_chunks


def chunk_single(slug: str, dry_run: bool = False) -> list[dict]:
    """Chunk a single document by slug."""
    path = CLEANED_DIR / f"{slug}.json"
    if not path.exists():
        logger.error("Cleaned file not found: %s", path)
        return []

    with open(path, encoding="utf-8") as f:
        parsed_doc = json.load(f)

    chunks = chunk_document(parsed_doc)

    if dry_run:
        for c in chunks:
            print(f"[{c['section']}] {c['chunk_id']}: {c['text'][:120]}...")
    else:
        if chunks:
            save_chunks(slug, chunks)

    return chunks


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Chunk cleaned JSON files using section-aware hybrid strategy."
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        help="Process a single slug (e.g. hdfc-mid-cap-fund-direct-growth). "
             "Omit to process all cleaned files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print chunks to stdout without writing to disk.",
    )
    args = parser.parse_args()

    if args.slug:
        chunk_single(args.slug, dry_run=args.dry_run)
    else:
        chunk_all(dry_run=args.dry_run)
