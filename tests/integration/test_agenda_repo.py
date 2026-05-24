"""Testes do repositório de eventos."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from src.domain.agenda.models import EventCreate
from src.domain.agenda.repo import (
    create_event,
    delete_event,
    get_event,
    list_events,
    update_event,
)


def test_create_and_get(tmp_db: sqlite3.Connection) -> None:
    start = datetime(2026, 6, 1, 10, 0)
    ev = create_event(
        tmp_db,
        EventCreate(
            title="Aula de Algoritmos",
            starts_at=start,
            ends_at=start + timedelta(hours=2),
            kind="aula",
            location="Sala 5",
        ),
    )
    assert ev.id > 0
    got = get_event(tmp_db, ev.id)
    assert got is not None
    assert got.title == "Aula de Algoritmos"
    assert got.kind == "aula"


def test_ends_at_before_starts_at_raises() -> None:
    start = datetime(2026, 6, 1, 10, 0)
    with pytest.raises(Exception):
        EventCreate(
            title="Invalido",
            starts_at=start,
            ends_at=start - timedelta(hours=1),
        )


def test_list_events_in_range(tmp_db: sqlite3.Connection) -> None:
    base = datetime(2026, 6, 1, 9, 0)
    for i in range(5):
        create_event(
            tmp_db,
            EventCreate(
                title=f"E{i}",
                starts_at=base + timedelta(days=i),
                kind="outro",
            ),
        )
    found = list_events(
        tmp_db, base, base + timedelta(days=3)
    )
    assert len(found) == 3
    # Ordenado ascendente
    titles = [e.title for e in found]
    assert titles == sorted(titles)


def test_update_event(tmp_db: sqlite3.Connection) -> None:
    start = datetime(2026, 6, 1, 10, 0)
    ev = create_event(
        tmp_db, EventCreate(title="X", starts_at=start, kind="outro")
    )
    updated = update_event(tmp_db, ev.id, title="Y", kind="prova")
    assert updated is not None
    assert updated.title == "Y"
    assert updated.kind == "prova"


def test_delete_event(tmp_db: sqlite3.Connection) -> None:
    ev = create_event(
        tmp_db,
        EventCreate(title="DelMe", starts_at=datetime(2026, 6, 1, 10, 0)),
    )
    assert delete_event(tmp_db, ev.id) is True
    assert get_event(tmp_db, ev.id) is None
    assert delete_event(tmp_db, ev.id) is False
