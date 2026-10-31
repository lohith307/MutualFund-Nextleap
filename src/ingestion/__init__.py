"""
Ingestion sub-package — pipeline to build the RAG corpus.

Modules:
    fetch   — HTTP GET each corpus URL; save raw HTML to data/raw/
    parse   — Strip boilerplate; extract and tag scheme sections
    chunker — Split cleaned text into overlapping chunks for embedding
    embedder— Embed chunks and upsert into ChromaDB vector store

Typical run order:
    python -m src.ingestion.fetch
    python -m src.ingestion.parse
    python -m src.ingestion.chunker
    python -m src.ingestion.embedder
"""

from src.ingestion.fetch import fetch_all
from src.ingestion.parse import parse_all
from src.ingestion.chunker import chunk_all
from src.ingestion.embedder import embed_all

__all__ = ["fetch_all", "parse_all", "chunk_all", "embed_all"]

