"""Testes unit do serviço de chat — Fase 3."""

from __future__ import annotations

from src.domain.chat.service import title_from_prompt


def test_title_short_unchanged() -> None:
    assert title_from_prompt("Olá!") == "Olá!"


def test_title_truncates_with_ellipsis() -> None:
    long = "Quero entender em detalhes o algoritmo de regressão logística aplicado a classificação binária quando..."
    out = title_from_prompt(long, max_chars=40)
    assert len(out) == 40
    assert out.endswith("…")


def test_title_collapses_whitespace() -> None:
    assert title_from_prompt("  oi  \n\n  como  vai\t") == "oi como vai"


def test_title_empty_falls_back() -> None:
    assert title_from_prompt("   ") == "Nova conversa"
