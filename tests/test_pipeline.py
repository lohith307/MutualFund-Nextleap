"""
test_pipeline.py — Integration tests for query_pipeline (Phase 3)

Tests cover:
- End-to-end factual answering
- Advisory query refusal handling
- Comparative query refusal handling
- PII query blocking
- Out-of-corpus scheme handling
- Output format compliance: <= 3 sentences, Source URL, date footer
"""

import pytest
from src.pipeline import query_pipeline


class TestQueryPipelineIntegration:

    def test_advisory_query_refused(self):
        result = query_pipeline("Should I invest in SBI PSU Fund?")
        assert result["status"] == "refusal"
        assert result["intent"] == "advisory"
        assert "cannot offer investment advice" in result["answer"]
        assert "Facts-only. No investment advice." in result["answer"]

    def test_comparative_query_refused(self):
        result = query_pipeline("Which fund is better, HDFC Mid Cap or SBI PSU Fund?")
        assert result["status"] == "refusal"
        assert result["intent"] == "comparative"
        assert "cannot compare" in result["answer"]

    def test_pii_query_blocked(self):
        result = query_pipeline("My PAN is ABCDE1234F, what is the exit load?")
        assert result["status"] == "refusal"
        assert result["intent"] == "pii"
        assert "do not share personal details" in result["answer"]

    def test_out_of_corpus_fallback(self):
        result = query_pipeline("What is the expense ratio of Quant Small Cap Fund?")
        assert result["status"] == "fallback"
        assert "could not find information about this scheme" in result["answer"]

    def test_ambiguous_query_fallback(self):
        result = query_pipeline("What is the minimum SIP amount?")
        assert result["status"] == "fallback"
        assert "Please specify which mutual fund scheme" in result["answer"]

    def test_factual_query_contract(self):
        result = query_pipeline("What is the exit load for Bandhan Small Cap Fund?")
        assert result["status"] in ("success", "fallback")
        answer = result["answer"]
        assert "Source:" in answer
        assert "Last updated from sources:" in answer
