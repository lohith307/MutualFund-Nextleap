"""
test_api.py — Unit & Integration Tests for FastAPI Endpoints (Phase 4)

Covers:
  - GET /health: verifies service status, vector store, scheme count, LLM config
  - GET /schemes: verifies 15 Groww schemes list and structure
  - POST /query (advisory): verifies instant refusal with AMFI link
  - POST /query (PII): verifies immediate refusal and protection
  - POST /query (out of scope): verifies refusal
  - POST /query (factual): verifies retrieval, source URL citation, timestamp
  - Validation: empty body, whitespace, oversized input, missing question key
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_check_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["vector_store"] in ("ready", "unavailable")
        assert "chunks_indexed" in data
        assert "schemes_available" in data
        assert "llm_provider" in data
        assert "llm_model" in data


class TestSchemesEndpoint:
    """Tests for GET /schemes."""

    def test_list_schemes_returns_15_items(self):
        response = client.get("/schemes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 15

    def test_scheme_item_structure(self):
        response = client.get("/schemes")
        data = response.json()
        for item in data:
            assert "name" in item
            assert "category" in item
            assert "url" in item
            assert "last_updated" in item
            assert item["url"].startswith("https://groww.in/mutual-funds/")


class TestQueryEndpointRefusals:
    """Tests for POST /query with non-factual questions."""

    def test_advisory_query_refused(self):
        response = client.post(
            "/query",
            json={"question": "Should I invest in Parag Parikh Flexi Cap Fund?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "advisory"
        assert data["status"] == "refusal"
        assert "amfiindia.com" in data["source"]
        assert "Facts-only. No investment advice." in data["answer"]

    def test_pii_query_refused(self):
        response = client.post(
            "/query",
            json={"question": "My PAN is ABCDE1234F, show my mutual fund portfolio"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "pii"
        assert data["status"] == "refusal"
        assert "PAN" in data["answer"] or "privacy" in data["answer"].lower()

    def test_out_of_scope_query_refused(self):
        response = client.post(
            "/query",
            json={"question": "What is the best crypto coin to buy?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] in ("out_of_scope", "advisory")
        assert data["status"] == "refusal"


class TestQueryEndpointFactual:
    """Tests for POST /query with valid factual queries."""

    def test_factual_query_returns_citation_and_footer(self):
        response = client.post(
            "/query",
            json={"question": "What is the exit load for Bandhan Small Cap Fund?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "factual"
        assert "source" in data
        assert "last_updated" in data
        assert "groww.in/mutual-funds" in data["source"]

    def test_query_response_keys_present(self):
        response = client.post(
            "/query",
            json={"question": "Who is the fund manager of Quant Small Cap Fund?"},
        )
        assert response.status_code == 200
        data = response.json()
        for expected_key in ("answer", "source", "source_url", "last_updated", "intent", "status", "retrieved_chunks"):
            assert expected_key in data


class TestQueryValidation:
    """Tests for POST /query input validation and edge cases."""

    def test_empty_string_rejected(self):
        response = client.post("/query", json={"question": ""})
        assert response.status_code == 422  # Pydantic min_length=1

    def test_whitespace_only_rejected(self):
        response = client.post("/query", json={"question": "     "})
        assert response.status_code == 400

    def test_missing_question_field_rejected(self):
        response = client.post("/query", json={"text": "expense ratio"})
        assert response.status_code == 422

    def test_oversized_query_rejected(self):
        response = client.post("/query", json={"question": "a" * 1001})
        assert response.status_code == 422
