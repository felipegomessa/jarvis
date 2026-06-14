"""Testes do coach (seleção de fracos + parsing do plano) — Spec 007."""

from __future__ import annotations

from src.domain.learning import TopicScore
from src.learning.coach import parse_coach_json, select_weak


def test_select_weak_filtra_e_ordena() -> None:
    scores = [
        TopicScore(topic="forte", earned=9.0, possible=10.0),   # 0.9
        TopicScore(topic="fraco", earned=2.0, possible=10.0),   # 0.2
        TopicScore(topic="medio", earned=5.0, possible=10.0),   # 0.5
    ]
    weak = select_weak(scores, threshold=0.6)
    assert [s.topic for s in weak] == ["fraco", "medio"]  # mais fraco primeiro


def test_select_weak_ignora_possible_zero() -> None:
    scores = [TopicScore(topic="x", earned=0.0, possible=0.0)]
    assert select_weak(scores, threshold=0.6) == []


def test_parse_coach_json_valido() -> None:
    raw = """
    {"recommendations": ["Revise sigmoide"],
     "plan": [{"topic":"regressão","action":"reler seção 3","material":"Doc 1",
               "minutes":40,"day":"2026-06-15","time":"19:00"}]}
    """
    recs, plan = parse_coach_json(raw, [])
    assert recs == ["Revise sigmoide"]
    assert plan.items[0].minutes == 40
    assert plan.items[0].material == "Doc 1"
    assert plan.items[0].day == "2026-06-15"
    assert plan.items[0].time == "19:00"


def test_parse_coach_json_fallback_generico() -> None:
    weak = [TopicScore(topic="KNN", earned=1.0, possible=5.0)]
    recs, plan = parse_coach_json("lixo não-json", weak)
    assert recs == []
    assert len(plan.items) == 1
    assert plan.items[0].topic == "KNN"
