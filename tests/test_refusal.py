"""
test_refusal.py — Unit tests for the Refusal Handler (Phase 3)

Tests cover:
- Refusal responses are polite and include an educational link
- Refusal template is returned consistently (not empty)
- Repeated advisory queries continue to be refused (RF-07)
- Out-of-scope topics trigger the correct refusal message
- Edge cases RF-01 through RF-07 from edge-cases.md
"""

import pytest
from src.pipeline.classifier import QueryIntent, refusal_response


class TestRefusalContent:

    def test_refusal_is_non_empty(self):
        """Refusal handler never returns empty or None."""
        for intent in [QueryIntent.ADVISORY, QueryIntent.COMPARATIVE, QueryIntent.PII, QueryIntent.OUT_OF_SCOPE]:
            resp = refusal_response(intent)
            assert resp is not None
            assert len(resp.strip()) > 20

    def test_refusal_contains_educational_link(self):
        """RF-05: Every refusal includes an AMFI or SEBI link."""
        for intent in [QueryIntent.ADVISORY, QueryIntent.COMPARATIVE, QueryIntent.OUT_OF_SCOPE]:
            resp = refusal_response(intent)
            assert "https://www.amfiindia.com" in resp

    def test_refusal_contains_disclaimer(self):
        """Refusal response ends with 'Facts-only. No investment advice.'"""
        for intent in [QueryIntent.ADVISORY, QueryIntent.COMPARATIVE, QueryIntent.PII]:
            resp = refusal_response(intent)
            assert "Facts-only. No investment advice." in resp

    def test_refusal_for_advisory_intent(self):
        """RF-01: Advisory query → polite refusal."""
        resp = refusal_response(QueryIntent.ADVISORY)
        assert "cannot offer investment advice" in resp
        assert "Facts-only. No investment advice." in resp

    def test_refusal_for_out_of_scope(self):
        """RF-04: 'Tell me about FDs' → out-of-scope refusal."""
        resp = refusal_response(QueryIntent.OUT_OF_SCOPE)
        assert "exclusively to answer factual queries about mutual fund schemes" in resp

    def test_refusal_for_comparative_query(self):
        """RF-02: 'Which fund performs better?' → comparative refusal."""
        resp = refusal_response(QueryIntent.COMPARATIVE)
        assert "cannot compare" in resp

    def test_repeated_advisory_still_refused(self):
        """RF-07: Same advisory query asked 5 times → refused every time."""
        for _ in range(5):
            resp = refusal_response(QueryIntent.ADVISORY)
            assert "Facts-only. No investment advice." in resp
