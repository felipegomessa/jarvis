"""Testes de parsing/validação do JSON de geração de provas — Spec 007."""

from __future__ import annotations

import pytest

from src.learning.errors import LearningError
from src.learning.generator import parse_quiz_questions
from src.rag.retrieve import RetrievedChunk


def _chunk(cid: int, doc: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=cid,
        document_id=doc,
        document_title="Doc",
        text="conteúdo",
        position=0,
        distance=0.0,
    )


REF_MAP = {"T1": _chunk(11, 1), "T2": _chunk(22, 2)}

VALID = """
{"questions": [
  {"type":"mc","topic":"regressão","prompt":"O que é sigmoide?",
   "options":["a","b","c","d"],"correct_index":1,"source":"T1"},
  {"type":"open","topic":"regressão","prompt":"Explique o modelo.",
   "answer_key":"combinação linear + sigmoide","source":"T2"}
]}
"""


def test_parse_valido_mapeia_fonte() -> None:
    qs = parse_quiz_questions(VALID, REF_MAP)
    assert len(qs) == 2
    mc = next(q for q in qs if q.type == "mc")
    assert mc.source_chunk_id == 11
    assert mc.source_document_id == 1


def test_parse_json_malformado_levanta() -> None:
    with pytest.raises(LearningError):
        parse_quiz_questions("isto não é json", REF_MAP)


def test_parse_sem_lista_questions_levanta() -> None:
    with pytest.raises(LearningError):
        parse_quiz_questions('{"foo": 1}', REF_MAP)


def test_parse_descarta_invalida_mantem_valida() -> None:
    # MC com correct_index fora das alternativas → descartada; a open válida fica.
    raw = """
    {"questions": [
      {"type":"mc","topic":"t","prompt":"ok","options":["a","b","c","d"],"correct_index":9,"source":"T1"},
      {"type":"open","topic":"t","prompt":"válida","answer_key":"resposta","source":"T2"}
    ]}
    """
    qs = parse_quiz_questions(raw, REF_MAP)
    assert len(qs) == 1
    assert qs[0].type == "open"


def test_parse_tudo_invalido_levanta() -> None:
    raw = '{"questions": [{"type":"mc","prompt":"x","options":["a"],"correct_index":0}]}'
    with pytest.raises(LearningError):
        parse_quiz_questions(raw, REF_MAP)


def test_parse_source_desconhecido_fica_sem_chunk() -> None:
    raw = """
    {"questions": [
      {"type":"open","topic":"t","prompt":"q","answer_key":"r","source":"T99"}
    ]}
    """
    qs = parse_quiz_questions(raw, REF_MAP)
    assert qs[0].source_chunk_id is None
