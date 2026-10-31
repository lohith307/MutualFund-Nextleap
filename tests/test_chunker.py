"""
test_chunker.py — Unit tests for the Section-Aware Hybrid Chunker

Tests cover:
- SKIP: _unclassified section produces no chunks
- ATOMIC: atomic sections always produce exactly 1 chunk
- SMALL: sections ≤ 80 lines produce 1 chunk
- LARGE: sections > 80 lines are split with RecursiveCharacterTextSplitter
- Metadata: each chunk carries correct scheme, section, url, last_updated
- chunk_id: stable, unique, deterministic
- content_hash: present and non-empty
- Empty document: returns empty list
- No sections: returns empty list
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from src.ingestion.chunker import (
    chunk_document,
    chunk_section,
    chunk_single,
    _make_chunk_id,
    ATOMIC_SECTIONS,
    SKIP_SECTIONS,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_META = {
    "scheme": "HDFC Mid Cap Fund",
    "amc": "HDFC Mutual Fund",
    "category": "Mid Cap",
    "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "parsed_at": "2026-10-29T10:00:00+00:00",
}

SAMPLE_DOC = {
    "slug": "hdfc-mid-cap-fund-direct-growth",
    "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "scheme": "HDFC Mid Cap Fund",
    "amc": "HDFC Mutual Fund",
    "category": "Mid Cap",
    "parsed_at": "2026-10-29T10:00:00+00:00",
    "is_scheme_specific": True,
    "sections": {
        "expense_ratio": ["Expense Ratio: 1.45%", "Direct Plan TER: 1.45%"],
        "exit_load": ["Exit Load: 1% if redeemed within 1 year", "Nil thereafter"],
        "fund_management": [
            "Fund Manager: Chirag Setalvad",
            "Managing Since: Jan 2014",
            "Experience: 20+ years",
        ],
        "benchmark": ["Benchmark: Nifty Midcap 150 TRI"],
        "minimum_investment": ["Min SIP: ₹100", "Min Lumpsum: ₹100"],
        "overview": ["NAV: ₹45.67", "AUM: ₹12,000 Cr", "Category: Mid Cap"],
        "_unclassified": ["Download the app", "Invest now", "Popular funds"],
    },
}


# ── chunk_section tests ───────────────────────────────────────────────────────

class TestSkipSections:
    def test_unclassified_produces_no_chunks(self):
        chunks = chunk_section(
            "test-slug", "_unclassified",
            ["noise line 1", "noise line 2"],
            SAMPLE_META,
        )
        assert chunks == []

    def test_empty_lines_produces_no_chunks(self):
        chunks = chunk_section("test-slug", "expense_ratio", [], SAMPLE_META)
        assert chunks == []


class TestAtomicSections:
    @pytest.mark.parametrize("section", list(ATOMIC_SECTIONS))
    def test_atomic_section_always_one_chunk(self, section):
        """All atomic sections produce exactly 1 chunk regardless of line count."""
        lines = [f"Line {i}: some financial data" for i in range(50)]
        chunks = chunk_section("test-slug", section, lines, SAMPLE_META)
        assert len(chunks) == 1

    def test_expense_ratio_is_atomic(self):
        lines = ["Expense Ratio: 1.45%", "Direct Plan TER: 1.45%"]
        chunks = chunk_section("test-slug", "expense_ratio", lines, SAMPLE_META)
        assert len(chunks) == 1
        assert "Expense Ratio" in chunks[0]["text"]

    def test_fund_management_stays_together(self):
        """Manager name + tenure + experience must be in the same chunk."""
        lines = [
            "Fund Manager: Chirag Setalvad",
            "Managing Since: Jan 2014",
            "Experience: 20+ years",
        ]
        chunks = chunk_section("test-slug", "fund_management", lines, SAMPLE_META)
        assert len(chunks) == 1
        assert "Chirag Setalvad" in chunks[0]["text"]
        assert "Jan 2014" in chunks[0]["text"]
        assert "20+ years" in chunks[0]["text"]

    def test_exit_load_terms_stay_together(self):
        lines = ["Exit Load: 1% if redeemed within 1 year", "Nil thereafter"]
        chunks = chunk_section("test-slug", "exit_load", lines, SAMPLE_META)
        assert len(chunks) == 1


class TestSmallNonAtomicSections:
    def test_small_overview_is_single_chunk(self):
        lines = [f"Overview line {i}" for i in range(10)]
        chunks = chunk_section("test-slug", "overview", lines, SAMPLE_META)
        assert len(chunks) == 1

    def test_exactly_80_lines_is_single_chunk(self):
        lines = [f"Line {i}" for i in range(80)]
        chunks = chunk_section("test-slug", "overview", lines, SAMPLE_META)
        assert len(chunks) == 1


class TestLargeSectionSplitting:
    def test_overview_over_80_lines_is_split(self):
        lines = [f"Overview data line number {i} with some content" for i in range(100)]
        chunks = chunk_section("test-slug", "overview", lines, SAMPLE_META)
        assert len(chunks) > 1

    def test_split_chunks_are_non_empty(self):
        lines = [f"Content line {i}: mutual fund data" for i in range(100)]
        chunks = chunk_section("test-slug", "overview", lines, SAMPLE_META)
        for chunk in chunks:
            assert chunk["text"].strip() != ""


# ── Chunk metadata tests ──────────────────────────────────────────────────────

class TestChunkMetadata:
    def setup_method(self):
        self.chunks = chunk_section(
            "hdfc-mid-cap-fund-direct-growth",
            "expense_ratio",
            ["Expense Ratio: 1.45%"],
            SAMPLE_META,
        )
        self.chunk = self.chunks[0]

    def test_chunk_id_format(self):
        assert self.chunk["chunk_id"] == "hdfc-mid-cap-fund-direct-growth__expense_ratio__000"

    def test_chunk_has_scheme(self):
        assert self.chunk["scheme"] == "HDFC Mid Cap Fund"

    def test_chunk_has_amc(self):
        assert self.chunk["amc"] == "HDFC Mutual Fund"

    def test_chunk_has_section(self):
        assert self.chunk["section"] == "expense_ratio"

    def test_chunk_has_source_url(self):
        assert "groww.in" in self.chunk["source_url"]

    def test_chunk_has_last_updated(self):
        assert self.chunk["last_updated"] == "2026-10-29"

    def test_chunk_has_content_hash(self):
        assert "content_hash" in self.chunk
        assert len(self.chunk["content_hash"]) == 16

    def test_chunk_id_is_stable(self):
        """Same input always produces the same chunk_id."""
        id1 = _make_chunk_id("test-slug", "expense_ratio", 0)
        id2 = _make_chunk_id("test-slug", "expense_ratio", 0)
        assert id1 == id2


# ── chunk_document tests ──────────────────────────────────────────────────────

class TestChunkDocument:
    def test_returns_list(self):
        chunks = chunk_document(SAMPLE_DOC)
        assert isinstance(chunks, list)

    def test_unclassified_not_in_chunks(self):
        chunks = chunk_document(SAMPLE_DOC)
        sections = {c["section"] for c in chunks}
        assert "_unclassified" not in sections

    def test_all_scheme_sections_present(self):
        chunks = chunk_document(SAMPLE_DOC)
        sections = {c["section"] for c in chunks}
        assert "expense_ratio" in sections
        assert "exit_load" in sections
        assert "fund_management" in sections

    def test_empty_sections_dict(self):
        doc = {**SAMPLE_DOC, "sections": {}}
        chunks = chunk_document(doc)
        assert chunks == []

    def test_chunk_count_reasonable(self):
        """Each non-unclassified section with content → at least 1 chunk."""
        chunks = chunk_document(SAMPLE_DOC)
        expected_sections = set(SAMPLE_DOC["sections"].keys()) - SKIP_SECTIONS
        non_empty = {s for s, lines in SAMPLE_DOC["sections"].items() if lines}
        assert len(chunks) >= len(expected_sections & non_empty)

    def test_chunk_ids_are_unique(self):
        chunks = chunk_document(SAMPLE_DOC)
        ids = [c["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Duplicate chunk IDs found!"


# ── chunk_single integration test ────────────────────────────────────────────

class TestChunkSingle:
    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        import src.ingestion.chunker as chunker_mod
        monkeypatch.setattr(chunker_mod, "CLEANED_DIR", tmp_path)
        result = chunk_single("nonexistent-fund", dry_run=True)
        assert result == []

    def test_valid_file_dry_run(self, tmp_path, monkeypatch, capsys):
        import src.ingestion.chunker as chunker_mod
        monkeypatch.setattr(chunker_mod, "CLEANED_DIR", tmp_path)
        monkeypatch.setattr(chunker_mod, "CHUNKS_DIR", tmp_path / "chunks")

        slug = "test-fund"
        doc = {**SAMPLE_DOC, "slug": slug}
        (tmp_path / f"{slug}.json").write_text(
            json.dumps(doc), encoding="utf-8"
        )

        result = chunk_single(slug, dry_run=True)
        assert len(result) > 0

