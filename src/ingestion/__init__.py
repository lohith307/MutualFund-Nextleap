"""
Ingestion sub-package — pipeline to build the RAG corpus.

Modules:
    fetch   — HTTP GET each corpus URL; save raw HTML to data/raw/
    parse   — Strip boilerplate; extract and tag scheme sections
    chunker — Split cleaned text into overlapping chunks for embedding
    embedder— Embed chunks and upsert into ChromaDB vector store
"""

__all__ = ["fetch_all", "parse_all", "chunk_all", "embed_all"]


def __getattr__(name: str):
    """Lazy-load ingestion pipeline functions on demand (PEP 562)."""
    if name == "fetch_all":
        from src.ingestion.fetch import fetch_all
        return fetch_all
    if name == "parse_all":
        from src.ingestion.parse import parse_all
        return parse_all
    if name == "chunk_all":
        from src.ingestion.chunker import chunk_all
        return chunk_all
    if name == "embed_all":
        from src.ingestion.embedder import embed_all
        return embed_all
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
