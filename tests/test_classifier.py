"""
test_classifier.py — Unit tests for the Query Classifier (Phase 3)

Tests cover:
- Factual queries correctly classified as FACTUAL
- Advisory queries correctly classified as ADVISORY
- Comparative queries classified as COMPARATIVE
- PII queries blocked as PII
- Out-of-scope queries classified as OUT_OF_SCOPE
- Performance / historical returns intent
- Edge cases C-01 through C-14 from edge-cases.md
"""

import pytest
from src.pipeline.classifier import QueryIntent, classify, detect_scheme, detect_section


class TestFactualQueries:
    """Queries that should be routed to the RAG pipeline."""

    def test_expense_ratio_query(self):
        assert classify("What is the expense ratio of HDFC Mid Cap Fund?") == QueryIntent.FACTUAL

    def test_exit_load_query(self):
        assert classify("What is the exit load for Bandhan Small Cap Fund?") == QueryIntent.FACTUAL

    def test_minimum_sip_query(self):
        assert classify("What is the minimum SIP amount for Axis Liquid Fund?") == QueryIntent.FACTUAL

    def test_lock_in_period_query(self):
        assert classify("What is the lock-in period for an ELSS mutual fund?") == QueryIntent.FACTUAL

    def test_riskometer_query(self):
        assert classify("What is the riskometer rating of SBI PSU Fund?") == QueryIntent.FACTUAL

    def test_benchmark_index_query(self):
        assert classify("What is the benchmark index of Kotak Silver ETF FOF?") == QueryIntent.FACTUAL

    def test_fund_manager_name_query(self):
        assert classify("Who manages the Parag Parikh Long Term Value Fund?") == QueryIntent.FACTUAL

    def test_fund_manager_since_query(self):
        assert classify("Since when has the manager been managing HDFC Mid Cap Fund?") == QueryIntent.FACTUAL

    def test_polite_filler_stripped(self):
        """C-07: 'Could you please tell me the NAV...' → FACTUAL"""
        assert classify("Could you please tell me the NAV of JioBlackRock Flexi Cap Fund?") == QueryIntent.FACTUAL

    def test_risk_of_fund_is_factual(self):
        """C-02: 'What are the risks of this fund?' → FACTUAL (riskometer)"""
        assert classify("What are the risks of HDFC Mid Cap Fund?") == QueryIntent.FACTUAL

    def test_recommended_sip_amount_is_factual(self):
        """C-13: 'What is the recommended SIP amount?' → FACTUAL (minimum SIP)"""
        assert classify("What is the minimum recommended SIP amount?") == QueryIntent.FACTUAL


class TestAdvisoryQueries:
    """Queries that should be refused."""

    def test_should_i_invest(self):
        """C-01: 'Should I invest in this fund?' → ADVISORY"""
        assert classify("Should I invest in SBI PSU Fund?") == QueryIntent.ADVISORY

    def test_which_fund_is_better(self):
        """C-03: 'Which fund is better?' → COMPARATIVE"""
        assert classify("Which fund is better, HDFC Mid Cap or SBI PSU Fund?") == QueryIntent.COMPARATIVE

    def test_future_performance(self):
        """C-08: 'Will this fund give good returns next year?' → ADVISORY"""
        assert classify("Will this fund give good returns next year?") == QueryIntent.ADVISORY

    def test_hypothetical_investment(self):
        """C-09: 'If I invest ₹10,000 now, how much will I get?' → ADVISORY"""
        assert classify("If I invest ₹10,000 now, how much return will I get?") == QueryIntent.ADVISORY

    def test_fund_manager_opinion(self):
        """C-11: 'Is the fund manager good?' → ADVISORY"""
        assert classify("Is the fund manager of HDFC Mid Cap good?") == QueryIntent.ADVISORY

    def test_safe_to_invest(self):
        """C-01 variant: 'Is it safe to invest in this fund?' → ADVISORY"""
        assert classify("Is it safe to invest in Bandhan Small Cap?") == QueryIntent.ADVISORY


class TestPIIQueries:
    """Queries containing PII that must be blocked."""

    def test_pan_in_query(self):
        """C-12 / S-03: Query with PAN → PII"""
        assert classify("My PAN is ABCDE1234F, what is my exit load?") == QueryIntent.PII

    def test_aadhaar_in_query(self):
        """S-04: 12-digit Aadhaar → PII"""
        assert classify("My Aadhaar is 1234 5678 9012, tell me the NAV") == QueryIntent.PII

    def test_otp_in_query(self):
        """S-05: 6-digit OTP → PII"""
        assert classify("My OTP is 847392 please verify my fund") == QueryIntent.PII


class TestEdgeCaseQueries:
    """Borderline and unusual input edge cases."""

    def test_empty_query(self):
        """Q-01: Empty string → UNRECOGNIZED"""
        assert classify("") == QueryIntent.UNRECOGNIZED
        assert classify("   ") == QueryIntent.UNRECOGNIZED

    def test_mixed_case_query(self):
        """Q-09: ALL CAPS query → classified correctly"""
        assert classify("WHAT IS THE EXIT LOAD OF SBI PSU FUND?") == QueryIntent.FACTUAL

    def test_historical_returns_query(self):
        """C-10: Historical returns → PERFORMANCE_RETURNS"""
        assert classify("What returns did HDFC Mid Cap give in the last 3 years?") == QueryIntent.PERFORMANCE_RETURNS

    def test_out_of_scope_query(self):
        assert classify("What is the interest rate on a fixed deposit?") == QueryIntent.OUT_OF_SCOPE


class TestEntityAndSectionDetection:
    def test_detect_scheme(self):
        assert detect_scheme("What is the exit load for HDFC Mid Cap?") == "HDFC Mid Cap Fund – Direct Growth"
        assert detect_scheme("Tell me about Bandhan small cap") == "Bandhan Small Cap Fund – Direct Growth"
        assert detect_scheme("NAV of Parag Parikh") == "Parag Parikh Long Term Value Fund – Direct Growth"
        assert detect_scheme("Something unknown") is None

    def test_detect_section(self):
        assert detect_section("What is the expense ratio?") == "expense_ratio"
        assert detect_section("What is the exit load?") == "exit_load"
        assert detect_section("Who is the fund manager?") == "fund_management"
        assert detect_section("What is the benchmark?") == "benchmark"
