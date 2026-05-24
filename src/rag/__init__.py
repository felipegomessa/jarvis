"""Pipeline de RAG: ingestao, chunking, embeddings, retrieval, geracao."""

from src.rag.chunk import chunk_text
from src.rag.embed import (
    embed_passages,
    embed_passages_async,
    embed_query,
    embed_query_async,
    get_embedder,
)
from src.rag.ingest import ingest_directory, ingest_document
from src.rag.pipeline import ask, ask_complete
from src.rag.prompt import SYSTEM_PROMPT, build_rag_messages
from src.rag.retrieve import search, search_async
from src.rag.types import (
    Chunk,
    Citation,
    IngestResult,
    RagResponse,
    RetrievalResult,
    RetrievedChunk,
)

__all__ = [
    "SYSTEM_PROMPT",
    "Chunk",
    "Citation",
    "IngestResult",
    "RagResponse",
    "RetrievalResult",
    "RetrievedChunk",
    "ask",
    "ask_complete",
    "build_rag_messages",
    "chunk_text",
    "embed_passages",
    "embed_passages_async",
    "embed_query",
    "embed_query_async",
    "get_embedder",
    "ingest_directory",
    "ingest_document",
    "search",
    "search_async",
]
