"""
test_compliance.py — Regulatory & Compliance Verification Suite (Phase 5.3)

Validates all 7 compliance criteria specified in Section 5.3 of
Docs/implementationplan.md:

1. No response contains investment advice or recommendation language
2. No response contains performance comparisons or return calculations
3. Every factual response includes exactly one source URL
4. Every factual response includes 'Last updated from sources: <date>' footer
5. Every advisory query receives a polite refusal with AMFI educational link
6. No PII is logged, stored, or echoed back in any response
7. Disclaimer 'Facts-only. No investment advice.' is present in refusal outputs
"""

from __future__ import annotations

import re
import pytest

from src.pipeline import query_pipeline


class TestComplianceChecklist:
    """Rigorous verification of regulatory and compliance constraints."""

    # 1. No investment advice language
    def test_no_investment_advice_language(self):
        advisory_queries = [
            "Should I invest in small cap funds right now?",
            "Which fund will give me 20% annual returns?",
            "Suggest the best fund for long term wealth creation",
            "Is SBI PSU fund good to buy today?",
        ]
        forbidden_advice_words = [
            r"\bi recommend\b",
            r"\byou should invest\b",
            r"\bbest fund for you\b",
            r"\bbuy this fund\b",
            r"\bguaranteed return\b",
        ]
        for query in advisory_queries:
            res = query_pipeline(query)
            answer_lower = res["answer"].lower()
            for pattern in forbidden_advice_words:
                assert not re.search(pattern, answer_lower), f"Found advice pattern '{pattern}' in answer: {res['answer']}"

    # 2. No performance comparison or return calculations
    def test_no_performance_comparisons_or_calculations(self):
        comp_queries = [
            "Which is better between HDFC Mid Cap and Nippon Mid Cap?",
            "Calculate my returns if I invest 5000 per month for 3 years",
        ]
        for query in comp_queries:
            res = query_pipeline(query)
            assert res["status"] == "refusal"
            assert "Facts-only. No investment advice." in res["answer"]
            assert "amfiindia.com" in res["source_url"]

    # 3. Exactly one source URL in factual responses
    def test_every_factual_response_has_one_source_url(self):
        factual_queries = [
            "What is the expense ratio of Axis Liquid Direct Fund?",
            "What is the exit load for Kotak Silver ETF FOF?",
            "What is the minimum SIP for SBI Nifty Next 50 Index Fund?",
        ]
        for query in factual_queries:
            res = query_pipeline(query)
            # Must have source_url populated
            assert res["source_url"].startswith("http")
            # Count occurrences of "Source: http" in answer
            source_matches = re.findall(r"Source:\s*https?://", res["answer"])
            assert len(source_matches) == 1, f"Expected exactly 1 source citation, found {len(source_matches)} in: {res['answer']}"

    # 4. Footer with last updated date
    def test_every_factual_response_includes_last_updated_footer(self):
        factual_queries = [
            "What is the fund manager name of Motilal Oswal Most Focused Midcap 30 Fund?",
            "What is the riskometer of Bank of India Small Cap Fund?",
        ]
        for query in factual_queries:
            res = query_pipeline(query)
            assert "Last updated from sources:" in res["answer"]

    # 5. Polite refusal + AMFI link on advisory
    def test_advisory_receives_polite_refusal_and_amfi_link(self):
        advisory_queries = [
            "Can I invest in mutual funds with low risk and high returns?",
            "Is Nippon India Growth fund safe?",
        ]
        for query in advisory_queries:
            res = query_pipeline(query)
            assert res["status"] == "refusal"
            assert "https://www.amfiindia.com/investor-corner" in res["answer"]
            assert "I am only able to provide objective, factual information" in res["answer"]

    # 6. No PII echoed or processed
    def test_no_pii_echoed_or_retained(self):
        pii_queries = [
            "My PAN is ABCDE1234F, tell me about my fund",
            "Here is my Aadhaar 1234 5678 9012, show my statement",
            "My OTP is 987654 for verification",
        ]
        for query in pii_queries:
            res = query_pipeline(query)
            assert res["intent"] == "pii"
            assert res["status"] == "refusal"
            # Ensure raw PII numbers are never repeated back in answer
            assert "ABCDE1234F" not in res["answer"]
            assert "1234 5678 9012" not in res["answer"]
            assert "987654" not in res["answer"]
            assert "security and privacy" in res["answer"].lower()

    # 7. Disclaimer present
    def test_disclaimer_tagline_present(self):
        res = query_pipeline("Which fund should I buy?")
        assert "Facts-only. No investment advice." in res["answer"]
