"""
test_e2e.py — End-to-End Query Verification Suite (Phase 5.2)

Validates the 10 official representative queries defined in Section 5.2 of
Docs/implementationplan.md across the full RAG pipeline.

Queries:
  1. What is the expense ratio of [Scheme]? -> Factual answer + source URL
  2. What is the exit load for [Scheme]? -> Factual answer + source URL
  3. What is the minimum SIP amount for [Scheme]? -> Factual answer + source URL
  4. What is the ELSS lock-in period for [Scheme]? -> Factual answer + source URL
  5. What is the riskometer rating for [Scheme]? -> Factual answer + source URL
  6. What is the benchmark index for [Scheme]? -> Factual answer + source URL
  7. How do I download my statement? -> Factual answer / fallback + source URL
  8. Should I invest in this fund? -> Polite refusal + AMFI educational link
  9. Which fund is better? -> Polite refusal + AMFI educational link
  10. What returns did this fund give? -> Refusal / factsheet link only
"""

from __future__ import annotations

import pytest
from src.pipeline import query_pipeline


class TestEndToEndQueries:
    """Verifies all 10 canonical queries from Section 5.2."""

    def test_query_1_expense_ratio(self):
        """Query 1: Factual expense ratio query."""
        res = query_pipeline("What is the expense ratio of Nippon India Growth Mid Cap Fund?")
        assert res["intent"] == "factual"
        assert "groww.in/mutual-funds" in res["source_url"]
        assert "Source: https://" in res["answer"]
        assert "Last updated from sources:" in res["answer"]

    def test_query_2_exit_load(self):
        """Query 2: Factual exit load query."""
        res = query_pipeline("What is the exit load for Parag Parikh Long Term Value Fund?")
        assert res["intent"] == "factual"
        assert "groww.in/mutual-funds" in res["source_url"]
        assert "Source: https://" in res["answer"]
        assert "Last updated from sources:" in res["answer"]

    def test_query_3_minimum_sip(self):
        """Query 3: Factual minimum SIP query."""
        res = query_pipeline("What is the minimum SIP amount for Bandhan Small Cap Fund?")
        assert res["intent"] == "factual"
        assert "groww.in/mutual-funds" in res["source_url"]
        assert "Source: https://" in res["answer"]
        assert "Last updated from sources:" in res["answer"]

    def test_query_4_lock_in_period(self):
        """Query 4: Factual lock-in period query."""
        res = query_pipeline("What is the lock-in period for Bank of India Flexi Cap Fund?")
        assert res["intent"] == "factual"
        assert "groww.in/mutual-funds" in res["source_url"]
        assert "Source: https://" in res["answer"]
        assert "Last updated from sources:" in res["answer"]

    def test_query_5_riskometer(self):
        """Query 5: Factual riskometer rating query."""
        res = query_pipeline("What is the riskometer rating for SBI PSU Fund?")
        assert res["intent"] == "factual"
        assert "groww.in/mutual-funds" in res["source_url"]
        assert "Source: https://" in res["answer"]
        assert "Last updated from sources:" in res["answer"]

    def test_query_6_benchmark_index(self):
        """Query 6: Factual benchmark index query."""
        res = query_pipeline("What is the benchmark index for Axis Liquid Direct Fund?")
        assert res["intent"] == "factual"
        assert "groww.in/mutual-funds" in res["source_url"]
        assert "Source: https://" in res["answer"]
        assert "Last updated from sources:" in res["answer"]

    def test_query_7_download_statement(self):
        """Query 7: Account/statement question without specific scheme."""
        res = query_pipeline("How do I download my statement?")
        assert res["intent"] == "factual"
        assert "groww.in/mutual-funds" in res["source_url"]
        assert res["status"] in ("fallback", "success")
        assert "Source: https://" in res["answer"]

    def test_query_8_should_i_invest(self):
        """Query 8: Investment advice inquiry."""
        res = query_pipeline("Should I invest in this fund?")
        assert res["status"] == "refusal"
        assert res["intent"] == "advisory"
        assert "amfiindia.com/investor-corner" in res["source_url"]
        assert "Facts-only. No investment advice." in res["answer"]

    def test_query_9_which_fund_is_better(self):
        """Query 9: Comparative evaluation inquiry."""
        res = query_pipeline("Which fund is better?")
        assert res["status"] == "refusal"
        assert res["intent"] == "comparative"
        assert "amfiindia.com/investor-corner" in res["source_url"]
        assert "Facts-only. No investment advice." in res["answer"]

    def test_query_10_returns_calculation(self):
        """Query 10: Historical returns inquiry."""
        res = query_pipeline("What returns did this fund give?")
        assert res["status"] == "refusal"
        assert res["intent"] == "performance_returns"
        assert "amfiindia.com/investor-corner" in res["source_url"]
        assert "Facts-only. No investment advice." in res["answer"]

