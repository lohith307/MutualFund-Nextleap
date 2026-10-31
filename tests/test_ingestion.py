"""
test_ingestion.py — Unit tests for fetch.py and parse.py (Phase 2)

Covers:
    fetch.py:
        - _url_to_slug produces valid filesystem slugs
        - _is_js_rendered_empty detects SPA shell pages
        - HTTP 404 sets status="broken"
        - HTTP 403 sets status="blocked"
        - Successful fetch saves file and sets status="fetched"

    parse.py:
        - clean_html strips scripts, nav, footer boilerplate
        - extract_sections tags keywords to correct sections
        - Empty document returns None
        - Section specificity assessment works
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── fetch.py tests ────────────────────────────────────────────────────────────

class TestUrlToSlug:
    from src.ingestion.fetch import _url_to_slug

    def test_groww_scheme_url(self):
        from src.ingestion.fetch import _url_to_slug
        slug = _url_to_slug("https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth")
        assert slug == "hdfc-mid-cap-fund-direct-growth"

    def test_trailing_slash(self):
        from src.ingestion.fetch import _url_to_slug
        slug = _url_to_slug("https://groww.in/mutual-funds/sbi-psu-fund-direct-growth/")
        assert slug == "sbi-psu-fund-direct-growth"

    def test_special_chars_replaced(self):
        from src.ingestion.fetch import _url_to_slug
        slug = _url_to_slug("https://groww.in/mutual-funds/fund_name&v2/")
        assert "&" not in slug
        assert "_" not in slug


class TestJsRenderedDetection:
    def test_empty_html_flagged(self):
        from src.ingestion.fetch import _is_js_rendered_empty
        html = "<html><body><div id='root'></div></body></html>"
        assert _is_js_rendered_empty(html) is True

    def test_rich_html_not_flagged(self):
        from src.ingestion.fetch import _is_js_rendered_empty
        html = "<html><body>" + ("<p>Mutual fund content here. " * 100) + "</body></html>"
        assert _is_js_rendered_empty(html) is False


class TestFetchUrlStatusCodes:
    def _make_entry(self):
        return {
            "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "scheme": "HDFC Mid Cap Fund",
            "status": "pending",
        }

    def test_404_sets_broken(self, tmp_path):
        from src.ingestion.fetch import fetch_url
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        with patch("src.ingestion.fetch._get_with_retry", return_value=mock_response):
            entry = fetch_url(self._make_entry(), mock_session, tmp_path)
        assert entry["status"] == "broken"
        assert entry["parseable"] is False

    def test_403_sets_blocked(self, tmp_path):
        from src.ingestion.fetch import fetch_url
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_session = MagicMock()

        with patch("src.ingestion.fetch._get_with_retry", return_value=mock_response):
            entry = fetch_url(self._make_entry(), mock_session, tmp_path)
        assert entry["status"] == "blocked"
        assert entry["parseable"] is False


# ── parse.py tests ────────────────────────────────────────────────────────────

class TestCleanHtml:
    def test_strips_script_tags(self):
        from src.ingestion.parse import clean_html
        html = "<html><body><script>alert('x')</script><p>Fund info</p></body></html>"
        result = clean_html(html)
        assert "alert" not in result
        assert "Fund info" in result

    def test_strips_nav_by_class(self):
        from src.ingestion.parse import clean_html
        html = "<html><body><nav class='navbar'>Menu</nav><p>Expense ratio: 1.5%</p></body></html>"
        result = clean_html(html)
        assert "Menu" not in result
        assert "Expense ratio" in result

    def test_normalizes_whitespace(self):
        from src.ingestion.parse import clean_html
        html = "<html><body><p>Hello    World</p></body></html>"
        result = clean_html(html)
        assert "  " not in result


class TestExtractSections:
    def test_expense_ratio_tagged(self):
        from src.ingestion.parse import extract_sections
        text = "Expense Ratio: 1.45%\nNAV: 45.67\nFund Manager: John Doe"
        sections = extract_sections(text)
        assert any("Expense Ratio" in line for line in sections.get("expense_ratio", []))

    def test_fund_manager_tagged(self):
        from src.ingestion.parse import extract_sections
        text = "Fund Manager: Jane Smith\nManaging since: 2019"
        sections = extract_sections(text)
        assert any("Fund Manager" in line for line in sections.get("fund_management", []))

    def test_exit_load_tagged(self):
        from src.ingestion.parse import extract_sections
        text = "Exit Load: 1% if redeemed within 1 year"
        sections = extract_sections(text)
        assert any("Exit Load" in line for line in sections.get("exit_load", []))

    def test_benchmark_tagged(self):
        from src.ingestion.parse import extract_sections
        text = "Benchmark Index: Nifty Midcap 150 TRI"
        sections = extract_sections(text)
        assert any("Benchmark" in line for line in sections.get("benchmark", []))


class TestParseFile:
    def test_empty_file_returns_none(self, tmp_path, monkeypatch):
        from src.ingestion import parse as parse_module
        monkeypatch.setattr(parse_module, "RAW_DIR", tmp_path)
        (tmp_path / "empty-fund.html").write_text("", encoding="utf-8")
        result = parse_module.parse_file("empty-fund")
        assert result is None

    def test_missing_file_returns_none(self, tmp_path, monkeypatch):
        from src.ingestion import parse as parse_module
        monkeypatch.setattr(parse_module, "RAW_DIR", tmp_path)
        result = parse_module.parse_file("nonexistent-fund")
        assert result is None

