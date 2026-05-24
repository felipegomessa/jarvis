"""Testes do repositorio de tarefas."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from src.domain.tasks.models import TaskCreate
from src.domain.tasks.repo import (
    complete_task,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)


def test_create_and_get(tmp_db: sqlite3.Connection) -> None:
    t = create_task(
        tmp_db,
        TaskCreate(title="Estudar IA", priority=1),
    )
    assert t.id > 0
    assert t.status == "pending"
    assert t.priority == 1


def test_complete_task(tmp_db: sqlite3.Connection) -> None:
    t = create_task(tmp_db, TaskCreate(title="X"))
    done = complete_task(tmp_db, t.id)
    assert done is not None
    assert done.status == "done"
    assert done.completed_at is not None


def test_list_pending_excludes_done(tmp_db: sqlite3.Connection) -> None:
    a = create_task(tmp_db, TaskCreate(title="A"))
    create_task(tmp_db, TaskCreate(title="B"))
    complete_task(tmp_db, a.id)
    pending = list_tasks(tmp_db, status="pending")
    assert len(pending) == 1
    assert pending[0].title == "B"


def test_list_ordering_priority_then_due(tmp_db: sqlite3.Connection) -> None:
    base = datetime(2026, 6, 1)
    create_task(tmp_db, TaskCreate(title="Normal sem prazo", priority=0))
    create_task(
        tmp_db,
        TaskCreate(title="Alta com prazo", priority=1, due_at=base + timedelta(days=2)),
    )
    create_task(
        tmp_db,
        TaskCreate(title="Urgente com prazo", priority=2, due_at=base + timedelta(days=1)),
    )
    tasks = list_tasks(tmp_db, status="pending")
    titles = [t.title for t in tasks]
    assert titles == ["Urgente com prazo", "Alta com prazo", "Normal sem prazo"]


def test_update_task(tmp_db: sqlite3.Connection) -> None:
    t = create_task(tmp_db, TaskCreate(title="X"))
    updated = update_task(tmp_db, t.id, title="Y", priority=2)
    assert updated is not None
    assert updated.title == "Y"
    assert updated.priority == 2


def test_delete_task(tmp_db: sqlite3.Connection) -> None:
    t = create_task(tmp_db, TaskCreate(title="DelMe"))
    assert delete_task(tmp_db, t.id) is True
    assert get_task(tmp_db, t.id) is None
