"""Retrieval semantico via sqlite-vec — RF-002.6 / D-020 / D-022."""

from __future__ import annotations

import asyncio

from loguru import logger

from src.core.config import get_settings
from src.core.db import get_connection
from src.rag.embed import embed_query
from src.rag.types import RetrievalResult, RetrievedChunk


def search(
    query: str,
    top_k: int | None = None,
    distance_threshold: float | None = None,
) -> RetrievalResult:
    """Retorna os top-K chunks mais relevantes para a query.

    Marca `no_relevant_context=True` se 0 chunks ou se min(distance) > threshold.
    """
    settings = get_settings()
    k = top_k or settings.rag_top_k
    thr = (
        distance_threshold
        if distance_threshold is not None
        else settings.rag_distance_threshold
    )

    q_emb = embed_query(query)
    q_blob = q_emb.tobytes()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT v.chunk_id, v.distance,
                   c.text, c.position, c.document_id,
                   d.title AS document_title
              FROM chunk_vecs v
              JOIN chunks c    ON c.id = v.chunk_id
              JOIN documents d ON d.id = c.document_id
             WHERE v.embedding MATCH ?
               AND k = ?
             ORDER BY v.distance
            """,
            (q_blob, k),
        ).fetchall()

    chunks = [
        RetrievedChunk(
            chunk_id=int(r["chunk_id"]),
            document_id=int(r["document_id"]),
            document_title=str(r["document_title"]),
            text=str(r["text"]),
            position=int(r["position"]),
            distance=float(r["distance"]),
        )
        for r in rows
    ]
    no_relevant = (not chunks) or (chunks[0].distance > thr)

    logger.debug(
        f"retrieval query={query!r} top_k={k} thr={thr} "
        f"-> {len(chunks)} chunks, no_relevant={no_relevant}"
    )

    return RetrievalResult(
        chunks=chunks,
        no_relevant_context=no_relevant,
        threshold_used=thr,
    )


async def search_async(
    query: str,
    top_k: int | None = None,
    distance_threshold: float | None = None,
) -> RetrievalResult:
    return await asyncio.to_thread(search, query, top_k, distance_threshold)


def get_document_chunks(
    document_id: int, limit: int | None = None
) -> list[RetrievedChunk]:
    """Chunks de UM documento em ordem de posição (sem embeddings).

    Diferente de `search` (busca semântica global), lê o documento inteiro/escopado
    — usado para gerar provas e para a tool `ler_documento` (corrige a Falha 4 da
    análise de erros: recuperação sem escopo por documento). `distance` não se
    aplica aqui e é preenchido com 0.0 (campo é obrigatório em `RetrievedChunk`).
    """
    sql = (
        "SELECT c.id AS chunk_id, c.text, c.position, c.document_id, "
        "       d.title AS document_title "
        "  FROM chunks c JOIN documents d ON d.id = c.document_id "
        " WHERE c.document_id = ? ORDER BY c.position"
    )
    params: tuple[int, ...] = (document_id,)
    if limit is not None:
        sql += " LIMIT ?"
        params = (document_id, limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        RetrievedChunk(
            chunk_id=int(r["chunk_id"]),
            document_id=int(r["document_id"]),
            document_title=str(r["document_title"]),
            text=str(r["text"]),
            position=int(r["position"]),
            distance=0.0,
        )
        for r in rows
    ]


async def get_document_chunks_async(
    document_id: int, limit: int | None = None
) -> list[RetrievedChunk]:
    return await asyncio.to_thread(get_document_chunks, document_id, limit)
