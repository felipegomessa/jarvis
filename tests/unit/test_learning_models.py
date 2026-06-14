"""Testes dos modelos de aprendizado (validators MC vs open) — Spec 007."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.learning import Question, Quiz, TopicScore


def test_mc_valido() -> None:
    q = Question(type="mc", prompt="2+2?", options=["1", "2", "3", "4"], correct_index=3)
    assert q.correct_index == 3


def test_mc_aceita_entre_2_e_6_alternativas() -> None:
    # 3 e 5 alternativas são aceitas (robustez com LLM real)
    assert Question(type="mc", prompt="x", options=["a", "b", "c"], correct_index=2)
    assert Question(
        type="mc", prompt="x", options=["a", "b", "c", "d", "e"], correct_index=4
    )


def test_mc_menos_de_2_alternativas_falha() -> None:
    with pytest.raises(ValidationError):
        Question(type="mc", prompt="x", options=["a"], correct_index=0)


def test_mc_correct_index_fora_das_alternativas_falha() -> None:
    with pytest.raises(ValidationError):
        Question(type="mc", prompt="x", options=["a", "b", "c", "d"], correct_index=9)


def test_open_sem_answer_key_falha() -> None:
    with pytest.raises(ValidationError):
        Question(type="open", prompt="explique X", answer_key="")


def test_open_valido() -> None:
    q = Question(type="open", prompt="explique X", answer_key="X é Y")
    assert q.answer_key == "X é Y"


def test_quiz_sem_documentos_falha() -> None:
    with pytest.raises(ValidationError):
        Quiz(title="t", documents=[])


def test_topic_score_ratio() -> None:
    assert TopicScore(topic="t", earned=3.0, possible=4.0).ratio == 0.75
    assert TopicScore(topic="t", earned=0.0, possible=0.0).ratio == 0.0
