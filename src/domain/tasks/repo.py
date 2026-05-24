"""Repositorio CRUD de tarefas — RF-004.2."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from src.domain.tasks.models import Task, TaskCreate


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") if dt else None


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=int(row["id"]),
        title=str(row["title"]),
        description=row["description"],
        due_at=datetime.fromisoformat(row["due_at"]) if row["due_at"] else None,
        status=row["status"],
        priority=int(row["priority"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        completed_at=(
            datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None
        ),
    )


def create_task(conn: sqlite3.Connection, data: TaskCreate) -> Task:
    cur = conn.execute(
        """
        INSERT INTO tasks (title, description, due_at, priority)
        VALUES (?, ?, ?, ?)
        """,
        (data.title, data.description, _iso(data.due_at), data.priority),
    )
    new_id = int(cur.lastrowid or 0)
    t = get_task(conn, new_id)
    assert t is not None
    return t


def get_task(conn: sqlite3.Connection, task_id: int) -> Task | None:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_task(row) if row else None


def list_tasks(
    conn: sqlite3.Connection,
    status: str | None = None,
    only_due_until: datetime | None = None,
    priority_min: int | None = None,
    limit: int | None = None,
) -> list[Task]:
    sql = "SELECT * FROM tasks WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if only_due_until is not None:
        sql += " AND due_at IS NOT NULL AND due_at <= ?"
        params.append(_iso(only_due_until))
    if priority_min is not None:
        sql += " AND priority >= ?"
        params.append(priority_min)
    # Pendentes primeiro, prioridade desc, depois due_at asc (NULLs por último)
    sql += (
        " ORDER BY CASE WHEN status='pending' THEN 0 ELSE 1 END, "
        "priority DESC, "
        "CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, due_at ASC"
    )
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_task(r) for r in rows]


def update_task(
    conn: sqlite3.Connection, task_id: int, **patch: Any
) -> Task | None:
    if not patch:
        return get_task(conn, task_id)

    allowed = {"title", "description", "due_at", "priority", "status"}
    sets: list[str] = []
    vals: list[Any] = []
    for k, v in patch.items():
        if k not in allowed:
            raise ValueError(f"campo não permitido em update_task: {k}")
        if isinstance(v, datetime):
            v = _iso(v)
        sets.append(f"{k} = ?")
        vals.append(v)

    sql = f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?"
    vals.append(task_id)
    conn.execute(sql, vals)
    return get_task(conn, task_id)


def complete_task(conn: sqlite3.Connection, task_id: int) -> Task | None:
    """Marca como concluída e define completed_at = now (UTC)."""
    now_iso = datetime.now(UTC).isoformat(timespec="seconds")
    conn.execute(
        "UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ?",
        (now_iso, task_id),
    )
    return get_task(conn, task_id)


def delete_task(conn: sqlite3.Connection, task_id: int) -> bool:
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return (cur.rowcount or 0) > 0
