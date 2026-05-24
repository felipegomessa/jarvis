"""Testes da VIEW unificada calendar_items_view + service — Fase 8."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from src.domain.agenda.models import EventCreate
from src.domain.agenda.repo import create_event
from src.domain.calendar_view import list_calendar_items
from src.domain.tasks.models import TaskCreate
from src.domain.tasks.repo import complete_task, create_task


def _seed(conn: sqlite3.Connection) -> None:
    base = datetime(2026, 6, 1, 9, 0)
    # 2 eventos
    create_event(conn, EventCreate(
        title="Aula de IA", starts_at=base, kind="aula", location="Sala 5",
    ))
    create_event(conn, EventCreate(
        title="Prova de Cálculo",
        starts_at=base + timedelta(days=2, hours=5),
        kind="prova", location="Sala 12",
    ))
    # 3 tarefas (2 com due, 1 sem)
    create_task(conn, TaskCreate(
        title="Estudar Naive Bayes",
        due_at=base + timedelta(days=1, hours=14),
        priority=1,
    ))
    t_done = create_task(conn, TaskCreate(
        title="Ler capítulo 3",
        due_at=base + timedelta(hours=23),
        priority=0,
    ))
    complete_task(conn, t_done.id)
    create_task(conn, TaskCreate(title="Sem prazo (não aparece no calendário)"))


def test_calendar_view_returns_unified_items(tmp_db: sqlite3.Connection) -> None:
    _seed(tmp_db)
    start = datetime(2026, 6, 1)
    end = datetime(2026, 6, 10)
    items = list_calendar_items(tmp_db, start, end)
    # 2 eventos + 2 tarefas com due_at = 4 (tarefa sem prazo NÃO aparece)
    assert len(items) == 4
    types = [it.item_type for it in items]
    assert types.count("event") == 2
    assert types.count("task") == 2
    # Ordenado ascendentemente
    assert items == sorted(items, key=lambda i: i.starts_at)


def test_filters_events_only(tmp_db: sqlite3.Connection) -> None:
    _seed(tmp_db)
    items = list_calendar_items(
        tmp_db, datetime(2026, 6, 1), datetime(2026, 6, 10),
        include_events=True, include_tasks=False,
    )
    assert all(it.item_type == "event" for it in items)
    assert len(items) == 2


def test_filters_tasks_only(tmp_db: sqlite3.Connection) -> None:
    _seed(tmp_db)
    items = list_calendar_items(
        tmp_db, datetime(2026, 6, 1), datetime(2026, 6, 10),
        include_events=False, include_tasks=True,
    )
    assert all(it.item_type == "task" for it in items)
    assert len(items) == 2


def test_only_pending_tasks(tmp_db: sqlite3.Connection) -> None:
    _seed(tmp_db)
    items = list_calendar_items(
        tmp_db, datetime(2026, 6, 1), datetime(2026, 6, 10),
        only_pending_tasks=True,
    )
    # 2 eventos + 1 tarefa pendente (a outra foi marcada como done)
    types = [it.item_type for it in items]
    assert types.count("event") == 2
    assert types.count("task") == 1
    assert items[-1].item_type == "task" or any(
        it.item_type == "task" and it.status == "pending" for it in items
    )


def test_kinds_filter_applies_only_to_events(tmp_db: sqlite3.Connection) -> None:
    _seed(tmp_db)
    items = list_calendar_items(
        tmp_db, datetime(2026, 6, 1), datetime(2026, 6, 10),
        kinds={"prova"},  # só eventos de prova; tasks NÃO filtradas
    )
    # 1 evento de prova + 2 tarefas (filtro de kind não afeta tasks)
    event_items = [it for it in items if it.item_type == "event"]
    task_items = [it for it in items if it.item_type == "task"]
    assert len(event_items) == 1
    assert event_items[0].category == "prova"
    assert len(task_items) == 2
