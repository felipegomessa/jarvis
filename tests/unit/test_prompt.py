"""Testes de src/rag/prompt.py."""

from __future__ import annotations

from src.rag.prompt import SYSTEM_PROMPT, build_rag_messages
from src.rag.types import RetrievalResult, RetrievedChunk


def test_build_messages_with_empty_retrieval() -> None:
    retrieval = RetrievalResult(chunks=[], no_relevant_context=True)
    msgs = build_rag_messages("o que e regressao?", retrieval)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert SYSTEM_PROMPT in msgs[0]["content"]
    assert "nenhum trecho relevante" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "o que e regressao?"


def test_build_messages_with_chunks() -> None:
    retrieval = RetrievalResult(
        chunks=[
            RetrievedChunk(
                chunk_id=1, document_id=10, document_title="Estatistica",
                text="Regressao logistica e usada para classificacao.",
                position=0, distance=0.2,
            ),
            RetrievedChunk(
                chunk_id=2, document_id=20, document_title="ML Basico",
                text="A funcao sigmoide mapeia para [0,1].",
                position=3, distance=0.4,
            ),
        ],
        no_relevant_context=False,
        threshold_used=0.6,
    )
    msgs = build_rag_messages("explique regressao logistica", retrieval)
    system = msgs[0]["content"]
    assert "[Doc 1: Estatistica]" in system
    assert "[Doc 2: ML Basico]" in system
    # Ordem mantida (menor distancia primeiro)
    idx1 = system.find("[Doc 1:")
    idx2 = system.find("[Doc 2:")
    assert 0 < idx1 < idx2
