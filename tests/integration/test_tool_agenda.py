"""Testes da resolução de evento por título em editar/remover_evento (B2)."""

from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest

from src.domain.agenda import EventCreate, create_event
from src.tools.tool_agenda import _resolve_event_id_by_title


def _ev(conn: sqlite3.Connection, title: str, day: int, kind: str = "outro") -> int:
    e = create_event(
        conn,
        EventCreate(
            title=title,
            starts_at=datetime(2026, 6, day, 10, 0, 0),
            kind=kind,
        ),
    )
    return e.id


def test_resolve_event_exact_accent_insensitive(tmp_db: sqlite3.Connection) -> None:
    eid = _ev(tmp_db, "Prova de Cálculo", 10, kind="prova")
    assert _resolve_event_id_by_title(tmp_db, "prova de calculo") == eid


def test_resolve_event_substring(tmp_db: sqlite3.Connection) -> None:
    eid = _ev(tmp_db, "Aula de Inteligência Artificial", 12, kind="aula")
    assert _resolve_event_id_by_title(tmp_db, "inteligência artificial") == eid


def test_resolve_event_not_found_raises(tmp_db: sqlite3.Connection) -> None:
    _ev(tmp_db, "Aula de Estatística", 9)
    with pytest.raises(ValueError, match="nenhum evento"):
        _resolve_event_id_by_title(tmp_db, "palestra inexistente")


def test_resolve_event_ambiguous_raises(tmp_db: sqlite3.Connection) -> None:
    _ev(tmp_db, "Aula de Estatística", 9)
    _ev(tmp_db, "Aula de Cálculo", 11)
    with pytest.raises(ValueError, match="mais de um evento"):
        _resolve_event_id_by_title(tmp_db, "aula")
