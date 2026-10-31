"""
test_retriever.py — Unit tests for the Retriever (Phase 3)

Tests cover:
- Top-K retrieval returns relevant chunks with metadata
- No results above threshold returns empty list
- Out-of-corpus scheme handling (Quant Small Cap)
- Ambiguous query handling (no scheme specified)
- Source URL and last-updated metadata presence
- Edge cases R-01 through R-10 from edge-cases.md
"""

import pytest
from src.pipeline.retriever import retrieve, RetrievalResult


class TestRetrieverBasic:

    def test_relevant_chunks_returned(self):
        """R-01 baseline: Valid query returns non-empty chunk list."""
        res = retrieve("What is the exit load for Bandhan Small Cap Fund?")
        assert isinstance(res, RetrievalResult)
        assert res.status == "success"
        assert len(res.chunks) > 0
        assert "Bandhan Small Cap" in res.chunks[0]["scheme"]

    def test_chunks_include_source_url(self):
        """Each returned chunk must include a source_url in metadata."""
        res = retrieve("What is the exit load for Bandhan Small Cap Fund?")
        assert res.source_url is not None
        assert "groww.in" in res.source_url

    def test_chunks_include_last_updated(self):
        """Each returned chunk must include a last_updated date."""
        res = retrieve("What is the exit load for Bandhan Small Cap Fund?")
        assert res.last_updated is not None
        assert len(res.last_updated) == 10  # YYYY-MM-DD

    def test_top_k_limit_respected(self):
        """Retriever never returns more than top_k chunks."""
        res = retrieve("What is the exit load for Bandhan Small Cap Fund?", top_k=2)
        assert len(res.chunks) <= 2


class TestRetrieverEdgeCases:

    def test_out_of_corpus_scheme(self):
        """C-04 / R-01: Asking about an unknown fund → out_of_corpus status."""
        res = retrieve("What is the expense ratio of Quant Small Cap Fund?")
        assert res.status == "out_of_corpus"
        assert len(res.chunks) == 0

    def test_ambiguous_scheme_name(self):
        """R-05: Generic question with no scheme specified → ambiguous status."""
        res = retrieve("What is the exit load?")
        assert res.status == "ambiguous"

    def test_empty_query(self):
        """Empty query returns below_threshold safely."""
        res = retrieve("")
        assert res.status == "below_threshold"

    def test_fund_manager_query(self):
        """Fund manager query retrieves overview or fund_management section."""
        res = retrieve("Who manages Parag Parikh Long Term Value Fund?")
        assert res.status == "success"
        assert len(res.chunks) > 0
        assert "Parag Parikh" in res.chunks[0]["scheme"]
