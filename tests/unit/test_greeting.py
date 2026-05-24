"""Testes da geração de saudações dinâmicas (sem nome próprio)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.ui.components import greeting


def _at(hour: int) -> datetime:
    return datetime(2026, 5, 24, hour, 0, 0, tzinfo=ZoneInfo("America/Campo_Grande"))


class _FixedDatetime:
    """Substitui datetime.now em greeting.datetime."""

    def __init__(self, value: datetime) -> None:
        self._value = value

    def now(self, tz=None):
        _ = tz
        return self._value


def test_time_based_bom_dia_at_8h() -> None:
    with patch.object(greeting, "datetime", _FixedDatetime(_at(8))):
        assert greeting._time_based() == "Bom dia!"


def test_time_based_boa_tarde_at_14h() -> None:
    with patch.object(greeting, "datetime", _FixedDatetime(_at(14))):
        assert greeting._time_based() == "Boa tarde!"


def test_time_based_boa_noite_at_21h() -> None:
    with patch.object(greeting, "datetime", _FixedDatetime(_at(21))):
        assert greeting._time_based() == "Boa noite!"


def test_time_based_boa_noite_madrugada_3h() -> None:
    with patch.object(greeting, "datetime", _FixedDatetime(_at(3))):
        assert greeting._time_based() == "Boa noite!"


def test_time_based_boundary_05h_bom_dia() -> None:
    with patch.object(greeting, "datetime", _FixedDatetime(_at(5))):
        assert greeting._time_based() == "Bom dia!"


def test_time_based_boundary_12h_boa_tarde() -> None:
    with patch.object(greeting, "datetime", _FixedDatetime(_at(12))):
        assert greeting._time_based() == "Boa tarde!"


def test_time_based_boundary_18h_boa_noite() -> None:
    with patch.object(greeting, "datetime", _FixedDatetime(_at(18))):
        assert greeting._time_based() == "Boa noite!"


def test_get_greeting_time_based_branch() -> None:
    with (
        patch.object(greeting.random, "random", return_value=0.1),
        patch.object(greeting, "datetime", _FixedDatetime(_at(8))),
    ):
        assert greeting.get_greeting() == "Bom dia!"


def test_get_greeting_name_argument_is_ignored() -> None:
    """O argumento `name` existe para compat, mas não personaliza a saudação."""
    with (
        patch.object(greeting.random, "random", return_value=0.1),
        patch.object(greeting, "datetime", _FixedDatetime(_at(8))),
    ):
        assert greeting.get_greeting("Felipe Sá") == "Bom dia!"
        assert greeting.get_greeting(None) == "Bom dia!"


def test_get_greeting_neutral_branch_returns_known_phrase() -> None:
    with (
        patch.object(greeting.random, "random", return_value=0.9),
        patch.object(
            greeting.random, "choice", return_value="No que você está pensando hoje?"
        ),
    ):
        assert greeting.get_greeting() == "No que você está pensando hoje?"


def test_get_greeting_neutral_phrases_are_all_valid() -> None:
    """Garante que todas as variações neutras seguem o padrão esperado."""
    for phrase in greeting._NEUTRAL:
        assert phrase.endswith(("?", "!", "."))
        assert len(phrase) > 5
        assert "," not in phrase  # nenhum nome próprio (sem vocativos)
