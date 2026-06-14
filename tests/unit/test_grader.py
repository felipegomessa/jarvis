"""Testes do corretor (MC determinístico + parsing do LLM-juiz) — Spec 007."""

from __future__ import annotations

from src.domain.learning import Question
from src.learning.grader import aggregate_score, grade_mc, parse_open_grade

MC = Question(type="mc", prompt="q", options=["a", "b", "c", "d"], correct_index=2, max_points=1.0)


def test_grade_mc_correto() -> None:
    assert grade_mc(MC, "2") == (1.0, True)


def test_grade_mc_incorreto() -> None:
    assert grade_mc(MC, "0") == (0.0, False)


def test_grade_mc_branco() -> None:
    assert grade_mc(MC, "") == (0.0, False)
    assert grade_mc(MC, "   ") == (0.0, False)


def test_grade_mc_nao_numerico() -> None:
    assert grade_mc(MC, "abc") == (0.0, False)


def test_aggregate_score() -> None:
    assert aggregate_score([1.0, 0.0, 0.5], [1.0, 1.0, 1.0]) == 5.0
    assert aggregate_score([2.0], [2.0]) == 10.0


def test_aggregate_score_total_zero() -> None:
    assert aggregate_score([], []) == 0.0


def test_parse_open_grade_clampa_e_escala() -> None:
    points, fb = parse_open_grade('{"score": 0.5, "feedback": "ok"}', max_points=2.0)
    assert points == 1.0
    assert "ok" in fb


def test_parse_open_grade_score_acima_de_1() -> None:
    points, _ = parse_open_grade('{"score": 5, "feedback": "x"}', max_points=1.0)
    assert points == 1.0


def test_parse_open_grade_inclui_faltantes() -> None:
    _, fb = parse_open_grade(
        '{"score": 0.3, "feedback": "parcial", "pontos_faltantes": ["sigmoide"]}',
        max_points=1.0,
    )
    assert "sigmoide" in fb
