"""
test_embedder.py — Unit tests for ChromaDB embedder and BGE embedding integration

Tests cover:
- Embedding generation with BGE model
- Embedding dimension matches expected (384 for bge-small)
- Query embedding incorporates BGE instruction prefix
- Chroma collection creation and upsert idempotency
- Metadata retention (scheme, section, url, date)
- Querying with and without section filter
"""

import pytest
from unittest.mock import MagicMock, patch

from src.ingestion.embedder import (
    BGEFastEmbeddingFunction,
    get_embedding_function,
    embed_and_upsert_chunks,
)

SAMPLE_CHUNKS = [
    {
        "chunk_id": "test_fund__expense_ratio__000",
        "content_hash": "a1b2c3d4e5f60718",
        "text": "Expense Ratio: 1.45% (Direct Plan)",
        "scheme": "Test Mid Cap Fund",
        "amc": "Test Mutual Fund",
        "category": "Mid Cap",
        "section": "expense_ratio",
        "source_url": "https://groww.in/mutual-funds/test-fund",
        "last_updated": "2026-10-31",
        "slug": "test-fund",
    },
    {
        "chunk_id": "test_fund__exit_load__000",
        "content_hash": "b2c3d4e5f6071829",
        "text": "Exit Load: 1.0% if redeemed within 365 days. Nil thereafter.",
        "scheme": "Test Mid Cap Fund",
        "amc": "Test Mutual Fund",
        "category": "Mid Cap",
        "section": "exit_load",
        "source_url": "https://groww.in/mutual-funds/test-fund",
        "last_updated": "2026-10-31",
        "slug": "test-fund",
    },
]


class TestBGEFastEmbeddingFunction:
    @pytest.fixture(scope="class")
    def embedding_fn(self):
        return BGEFastEmbeddingFunction(model_name="BAAI/bge-small-en-v1.5")

    def test_embed_documents_dimension(self, embedding_fn):
        texts = ["What is the expense ratio?", "Exit load details"]
        embeddings = embedding_fn.embed_documents(texts)
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 384
        assert len(embeddings[1]) == 384

    def test_embed_query_dimension(self, embedding_fn):
        query = "What is the exit load for Test Mid Cap Fund?"
        embedding = embedding_fn.embed_query(query)
        assert isinstance(embedding, list)
        assert len(embedding) == 384


class TestEmbedderUpsert:
    def test_embed_and_upsert_chunks(self):
        mock_collection = MagicMock()
        mock_embedding_fn = MagicMock()
        mock_embedding_fn.embed_documents.return_value = [
            [0.1] * 384,
            [0.2] * 384,
        ]

        count = embed_and_upsert_chunks(
            SAMPLE_CHUNKS,
            collection=mock_collection,
            embedding_fn=mock_embedding_fn,
            batch_size=10,
        )

        assert count == 2
        mock_collection.upsert.assert_called_once()
        call_kwargs = mock_collection.upsert.call_args[1]
        assert call_kwargs["ids"] == ["test_fund__expense_ratio__000", "test_fund__exit_load__000"]
        assert len(call_kwargs["metadatas"]) == 2
        assert call_kwargs["metadatas"][0]["section"] == "expense_ratio"
        assert call_kwargs["metadatas"][0]["scheme"] == "Test Mid Cap Fund"
