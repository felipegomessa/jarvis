"""Pipeline RAG completo (retrieve + prompt + stream) — RF-002.8."""

from __future__ import annotations

from collections.abc import AsyncIterator

from src.llm import GemmaClient
from src.rag.prompt import build_rag_messages
from src.rag.retrieve import search_async
from src.rag.types import Citation, RagResponse


async def ask(
    question: str,
    gemma: GemmaClient,
    top_k: int | None = None,
    distance_threshold: float | None = None,
) -> AsyncIterator[RagResponse]:
    """Pipeline RAG: retrieve -> prompt -> stream.

    Yield de `RagResponse` a cada token. O último yield tem `finished=True`.
    """
    retrieval = await search_async(question, top_k, distance_threshold)

    citations = [
        Citation(
            doc_id=ch.document_id,
            doc_title=ch.document_title,
            chunk_id=ch.chunk_id,
            position=ch.position,
            distance=ch.distance,
        )
        for ch in retrieval.chunks
    ]

    messages = build_rag_messages(question, retrieval)

    acc = ""
    async for token in gemma.stream_chat(messages):
        acc += token
        yield RagResponse(
            text_chunk_streaming=acc,
            citations=citations,
            no_relevant_context=retrieval.no_relevant_context,
            finished=False,
        )

    yield RagResponse(
        text_chunk_streaming=acc,
        citations=citations,
        no_relevant_context=retrieval.no_relevant_context,
        finished=True,
    )


async def ask_complete(
    question: str,
    gemma: GemmaClient,
    top_k: int | None = None,
    distance_threshold: float | None = None,
) -> RagResponse:
    """Versao nao-streaming: usa complete_chat. Util para o agent loop / tool."""
    retrieval = await search_async(question, top_k, distance_threshold)

    citations = [
        Citation(
            doc_id=ch.document_id,
            doc_title=ch.document_title,
            chunk_id=ch.chunk_id,
            position=ch.position,
            distance=ch.distance,
        )
        for ch in retrieval.chunks
    ]

    messages = build_rag_messages(question, retrieval)
    text = await gemma.complete_chat(messages)

    return RagResponse(
        text_chunk_streaming=text,
        citations=citations,
        no_relevant_context=retrieval.no_relevant_context,
        finished=True,
    )
