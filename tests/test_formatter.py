"""
test_formatter.py — Unit tests for the Response Formatter (Phase 3)

Tests cover:
- Responses exceeding 3 sentences are truncated
- Missing citation URL is injected from metadata
- Advisory language in response is detected and rejected
- PII echoed in response is redacted
- Footer is always appended
- Edge cases F-01 through F-08 from edge-cases.md
"""

import pytest
from src.pipeline.formatter import redact_pii, validate_and_format


class TestFormatterOutputContract:

    def test_response_truncated_to_3_sentences(self):
        """F-03 variant: 5-sentence response → truncated to 3."""
        long_response = (
            "Sentence one is here. Sentence two is here. Sentence three is here. "
            "Sentence four should be stripped. Sentence five should also be stripped."
        )
        formatted = validate_and_format(
            long_response,
            source_url="https://groww.in/test",
            last_updated="2026-10-31",
        )
        assert "Sentence four" not in formatted
        assert "Sentence five" not in formatted
        assert "Sentence one is here." in formatted
        assert "Sentence three is here." in formatted

    def test_footer_always_appended(self):
        """Footer 'Last updated from sources: ...' always present."""
        resp = "The exit load is 1% if redeemed within 1 year."
        formatted = validate_and_format(
            resp,
            source_url="https://groww.in/test",
            last_updated="2026-10-31",
        )
        assert "Last updated from sources: 2026-10-31" in formatted

    def test_missing_citation_injected(self):
        """F-01: No URL in response → source URL from metadata appended."""
        resp = "The minimum SIP investment is Rs 100."
        formatted = validate_and_format(
            resp,
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap",
            last_updated="2026-10-31",
        )
        assert "Source: https://groww.in/mutual-funds/hdfc-mid-cap" in formatted

    def test_multiple_citations_reduced_to_one(self):
        """F-02: Two URLs in response → only canonical metadata URL used."""
        resp = (
            "Visit https://example.com/one and https://example.com/two for details. "
            "The exit load is 1%."
        )
        formatted = validate_and_format(
            resp,
            source_url="https://groww.in/mutual-funds/canonical",
            last_updated="2026-10-31",
        )
        assert "Source: https://groww.in/mutual-funds/canonical" in formatted
        # Only one 'Source:' line
        assert formatted.count("Source:") == 1

    def test_missing_last_updated_handled(self):
        """F-04: null last_updated → 'date unavailable' footer."""
        resp = "The expense ratio is 0.74%."
        formatted = validate_and_format(
            resp,
            source_url="https://groww.in/test",
            last_updated=None,
        )
        assert "Last updated from sources: date unavailable" in formatted


class TestFormatterSecurityChecks:

    def test_pii_in_response_redacted(self):
        """F-06: PAN number echoed in response → redacted."""
        resp = "Your PAN ABCDE1234F is registered. The expense ratio is 1%."
        formatted = validate_and_format(
            resp,
            source_url="https://groww.in/test",
            last_updated="2026-10-31",
        )
        assert "ABCDE1234F" not in formatted
        assert "[REDACTED_PAN]" in formatted

    def test_aadhaar_in_response_redacted(self):
        resp = "Account for Aadhaar 1234 5678 9012 has no exit load."
        formatted = validate_and_format(
            resp,
            source_url="https://groww.in/test",
            last_updated="2026-10-31",
        )
        assert "1234 5678 9012" not in formatted
        assert "[REDACTED_AADHAAR]" in formatted

    def test_advisory_language_detected(self):
        """F-08: 'recommend' in response → overridden with refusal."""
        resp = "I strongly recommend this fund because it gives great returns."
        formatted = validate_and_format(
            resp,
            source_url="https://groww.in/test",
            last_updated="2026-10-31",
        )
        assert "cannot provide opinions or investment recommendations" in formatted
        assert "https://www.amfiindia.com/investor-corner" in formatted
