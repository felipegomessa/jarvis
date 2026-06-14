"""Testes da montagem de prompt da geração (pura) — Spec 007."""

from __future__ import annotations

from src.learning.generator import _normalize_ref, build_generation_messages
from src.rag.retrieve import RetrievedChunk


def _chunk(cid: int, title: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=cid, document_id=1, document_title=title, text=text, position=0, distance=0.0
    )


def test_normalize_ref_variantes() -> None:
    assert _normalize_ref("T3") == "T3"
    assert _normalize_ref("[T3]") == "T3"
    assert _normalize_ref("t3") == "T3"
    assert _normalize_ref("5") == "T5"
    assert _normalize_ref(" T12 ") == "T12"


def test_build_messages_inclui_contagens_e_trechos() -> None:
    refs = [("T1", _chunk(1, "Aula KNN", "vizinhos mais próximos")),
            ("T2", _chunk(2, "TF-IDF", "frequência de termos"))]
    msgs = build_generation_messages(refs, num_mc=5, num_open=2)
    assert msgs[0]["role"] == "system"
    assert "JSON" in msgs[0]["content"]
    user = msgs[1]["content"]
    assert "5 questões 'mc'" in user
    assert "2 questões 'open'" in user
    assert "[T1]" in user and "[T2]" in user
    assert "vizinhos mais próximos" in user


def test_idioma_pt_forca_portugues() -> None:
    refs = [("T1", _chunk(1, "Doc", "texto"))]
    msgs = build_generation_messages(refs, num_mc=1, num_open=0, idioma="pt")
    assert "PORTUGUÊS" in msgs[0]["content"]


def test_idioma_original_usa_fonte() -> None:
    refs = [("T1", _chunk(1, "Doc", "texto"))]
    msgs = build_generation_messages(refs, num_mc=1, num_open=0, idioma="original")
    assert "MESMO idioma" in msgs[0]["content"]
    assert "PORTUGUÊS" not in msgs[0]["content"]
