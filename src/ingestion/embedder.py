"""
embedder.py — Embedding Model & ChromaDB Vector Store Writer (Phase 2)

Converts document chunks from data/chunks/<slug>.json into dense vector
embeddings and upserts them into a persistent ChromaDB vector store.

Embedding Models Supported:
  • BGE (Default / Free / Local):
      - BAAI/bge-small-en-v1.5 (384 dim, fast, ~133MB)
      - BAAI/bge-large-en-v1.5 (1024 dim)
      - Uses fastembed (ONNX runtime, no PyTorch needed)
  • OpenAI (Optional / Paid):
      - text-embedding-3-small / text-embedding-ada-002

ChromaDB Integration:
  - Local persistent client in corpus/vector_store/
  - Collection: mutual_fund_faq
  - Upserts using chunk_id (<slug>__<section>__<index>) as the primary key
  - Saves full metadata (scheme, amc, category, section, source_url, last_updated)

Usage:
    python -m src.ingestion.embedder           # embed & index all chunk files
    python -m src.ingestion.embedder --slug hdfc-mid-cap-fund-direct-growth
    python -m src.ingestion.embedder --query "What is the exit load?"  # test query
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

# Ensure UTF-8 console output for Windows CLI (avoids ₹ currency symbol errors)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import chromadb
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
CHUNKS_DIR = ROOT / "data" / "chunks"
VECTOR_STORE_PATH = ROOT / os.getenv("VECTOR_STORE_PATH", "corpus/vector_store")
COLLECTION_NAME = os.getenv("VECTOR_STORE_COLLECTION", "mutual_fund_faq")

# ── Model Settings ────────────────────────────────────────────────────────────
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "bge").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Embedding Functions ───────────────────────────────────────────────────────

class BGEFastEmbeddingFunction:
    """Wrapper around fastembed TextEmbedding with BGE instruction prefix handling."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding
        logger.info("Initializing BGE embedding model: %s", model_name)
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed document chunks (no query prefix)."""
        embeddings = list(self._model.embed(texts))
        return [e.tolist() for e in embeddings]

    def embed_query(self, query: str) -> List[float]:
        """Embed user search query with BGE prompt instruction prefix."""
        prefix = "Represent this sentence for searching relevant passages: "
        formatted_query = f"{prefix}{query}" if "bge" in self.model_name.lower() else query
        embedding = list(self._model.embed([formatted_query]))[0]
        return embedding.tolist()


def get_embedding_function():
    """Factory to get the embedding function based on configuration."""
    if EMBEDDING_PROVIDER in ("bge", "bge-local", "fastembed", "local"):
        return BGEFastEmbeddingFunction(model_name=EMBEDDING_MODEL)
    elif EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment or .env file.")
        return OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=api_key)
    else:
        logger.warning(
            "Unknown EMBEDDING_PROVIDER '%s'. Falling back to BGE (%s)",
            EMBEDDING_PROVIDER,
            EMBEDDING_MODEL,
        )
        return BGEFastEmbeddingFunction(model_name="BAAI/bge-small-en-v1.5")


# ── Vector Store Helpers ──────────────────────────────────────────────────────

def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create the ChromaDB persistent client."""
    VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(VECTOR_STORE_PATH))


def get_or_create_collection(client: Optional[chromadb.PersistentClient] = None) -> Any:
    """Get or create the target Chroma collection, auto-populating if empty on cloud host."""
    if client is None:
        client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Self-healing cold start: If collection has 0 chunks, populate automatically from data/chunks/
    if collection.count() == 0 and CHUNKS_DIR.exists():
        chunk_files = sorted(CHUNKS_DIR.glob("*.json"))
        if chunk_files:
            logger.info("Chroma collection '%s' is empty. Auto-indexing %d chunk files...", COLLECTION_NAME, len(chunk_files))
            all_chunks = []
            for f in chunk_files:
                try:
                    with open(f, encoding="utf-8") as fp:
                        chunks = json.load(fp)
                        if isinstance(chunks, list):
                            all_chunks.extend(chunks)
                except Exception as exc:
                    logger.warning("Could not read chunk file %s: %s", f.name, exc)

            if all_chunks:
                try:
                    embedding_fn = get_embedding_function()
                    embed_and_upsert_chunks(all_chunks, collection=collection, embedding_fn=embedding_fn)
                    logger.info("Self-healing: Auto-indexed %d chunks into ChromaDB.", len(all_chunks))
                except Exception as exc:
                    logger.error("Auto-indexing chunks failed: %s", exc)

    return collection


# ── Ingestion Logic ───────────────────────────────────────────────────────────

def embed_and_upsert_chunks(
    chunks: List[dict],
    collection: Optional[Any] = None,
    embedding_fn: Optional[Any] = None,
    batch_size: int = 64,
) -> int:
    """
    Generate embeddings for chunks and upsert them into ChromaDB.

    Args:
        chunks: List of chunk dictionaries created by chunker.py.
        collection: Target ChromaDB collection.
        embedding_fn: Embedding instance (BGE or OpenAI).
        batch_size: Batch size for embeddings and upserts.

    Returns:
        Number of successfully upserted chunks.
    """
    if not chunks:
        logger.warning("No chunks provided to embed_and_upsert_chunks.")
        return 0

    if collection is None:
        collection = get_or_create_collection()

    if embedding_fn is None:
        embedding_fn = get_embedding_function()

    total_chunks = len(chunks)
    logger.info("Embedding and indexing %d chunks in batches of %d...", total_chunks, batch_size)

    upserted_count = 0

    for i in range(0, total_chunks, batch_size):
        batch = chunks[i : i + batch_size]

        ids = [c["chunk_id"] for c in batch]
        documents = [c["text"] for c in batch]

        # Flatten metadata: all values must be primitive types for Chroma
        metadatas = [
            {
                "scheme": str(c.get("scheme", "")),
                "amc": str(c.get("amc", "")),
                "category": str(c.get("category", "")),
                "section": str(c.get("section", "")),
                "source_url": str(c.get("source_url", "")),
                "last_updated": str(c.get("last_updated", "")),
                "slug": str(c.get("slug", "")),
                "content_hash": str(c.get("content_hash", "")),
            }
            for c in batch
        ]

        # Generate embeddings
        embeddings = embedding_fn.embed_documents(documents)

        # Upsert into Chroma (idempotent: updates existing, inserts new)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        upserted_count += len(batch)
        logger.info("Upserted batch %d–%d of %d chunks.", i + 1, min(i + batch_size, total_chunks), total_chunks)

    logger.info("Finished embedding & indexing. Total in collection '%s': %d", COLLECTION_NAME, collection.count())
    return upserted_count


def embed_all(client: Optional[chromadb.PersistentClient] = None) -> int:
    """Load all chunk files from data/chunks/ and index them into ChromaDB."""
    chunk_files = sorted(CHUNKS_DIR.glob("*.json"))

    if not chunk_files:
        logger.warning("No chunk files found in %s. Run chunker.py first.", CHUNKS_DIR)
        return 0

    all_chunks = []
    for f in chunk_files:
        try:
            with open(f, encoding="utf-8") as fp:
                chunks = json.load(fp)
                if isinstance(chunks, list):
                    all_chunks.extend(chunks)
        except Exception as exc:
            logger.error("Error reading %s: %s", f.name, exc)

    collection = get_or_create_collection(client)
    embedding_fn = get_embedding_function()

    return embed_and_upsert_chunks(all_chunks, collection=collection, embedding_fn=embedding_fn)


def embed_single_slug(slug: str) -> int:
    """Embed chunks for a single fund scheme slug."""
    path = CHUNKS_DIR / f"{slug}.json"
    if not path.exists():
        logger.error("Chunk file not found: %s", path)
        return 0

    with open(path, encoding="utf-8") as f:
        chunks = json.load(f)

    collection = get_or_create_collection()
    embedding_fn = get_embedding_function()

    return embed_and_upsert_chunks(chunks, collection=collection, embedding_fn=embedding_fn)


def test_similarity_query(query: str, top_k: int = 3, section: Optional[str] = None) -> None:
    """Helper to test vector retrieval directly from ChromaDB."""
    collection = get_or_create_collection()
    embedding_fn = get_embedding_function()

    query_embedding = embedding_fn.embed_query(query)
    where_filter = {"section": section} if section else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    print(f"\n{'='*70}")
    print(f"Query: '{query}' (top_k={top_k}, filter={where_filter})")
    print(f"{'='*70}")

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    if not docs:
        print("No matching documents found.")
        return

    for idx, (doc, meta, dist) in enumerate(zip(docs, metas, dists)):
        # Cosine distance = 1 - cosine similarity
        sim_score = 1.0 - dist if dist is not None else 0.0
        print(f"\n[Rank {idx+1}] Score: {sim_score:.4f} | Section: {meta.get('section')} | Scheme: {meta.get('scheme')}")
        print(f"Source: {meta.get('source_url')} | Date: {meta.get('last_updated')}")
        print(f"Text:\n{doc.strip()}")


# ── CLI Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed chunks and index them into ChromaDB vector store."
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        help="Embed only a single scheme by slug (e.g. hdfc-mid-cap-fund-direct-growth)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Run a test query against the indexed ChromaDB store",
    )
    parser.add_argument(
        "--filter-section",
        type=str,
        default=None,
        help="Optional section filter for test query (e.g. expense_ratio)",
    )
    args = parser.parse_args()

    if args.query:
        test_similarity_query(args.query, section=args.filter_section)
    elif args.slug:
        embed_single_slug(args.slug)
    else:
        embed_all()
