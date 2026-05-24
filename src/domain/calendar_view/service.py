"""Leitura unificada de eventos + tarefas para o calendário — Fase 8."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CalendarItem(BaseModel):
    item_uid: str  # 'event:5' ou 'task:12'
    item_type: str  # 'event' | 'task'
    source_id: int
    title: str
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    category: str | None = None  # kind dos eventos
    status: str | None = None  # pending/done dos tasks
    priority: int | None = None  # 0/1/2 dos tasks
    location: str | None = None


def _row_to_item(row: sqlite3.Row) -> CalendarItem:
    def _dt(s: Any) -> datetime | None:
        if s is None or s == "":
            return None
        return datetime.fromisoformat(str(s))

    return CalendarItem(
        item_uid=str(row["item_uid"]),
        item_type=str(row["item_type"]),
        source_id=int(row["source_id"]),
        title=str(row["title"]),
        description=row["description"],
        starts_at=_dt(row["starts_at"]) or datetime.now(),
        ends_at=_dt(row["ends_at"]),
        category=row["category"],
        status=row["status"],
        priority=int(row["priority"]) if row["priority"] is not None else None,
        location=row["location"],
    )


def list_calendar_items(
    conn: sqlite3.Connection,
    start: datetime,
    end: datetime,
    include_events: bool = True,
    include_tasks: bool = True,
    only_pending_tasks: bool = False,
    kinds: set[str] | None = None,
) -> list[CalendarItem]:
    """Lista items do calendário (eventos + tarefas) na janela [start, end).

    Args:
        kinds: se fornecido, filtra eventos por kind (aula/prova/trabalho/outro).
               Não afeta tarefas.
    """
    type_filter: list[str] = []
    if include_events:
        type_filter.append("'event'")
    if include_tasks:
        type_filter.append("'task'")
    if not type_filter:
        return []

    sql = (
        "SELECT * FROM calendar_items_view "
        "WHERE starts_at >= ? AND starts_at < ? "
        f"AND item_type IN ({','.join(type_filter)})"
    )
    params: list[Any] = [start.isoformat(), end.isoformat()]

    if only_pending_tasks:
        sql += " AND (item_type = 'event' OR status = 'pending')"

    if kinds:
        sanitized = [k for k in kinds if k in {"aula", "prova", "trabalho", "outro"}]
        if sanitized:
            placeholders = ",".join("?" * len(sanitized))
            sql += f" AND (item_type = 'task' OR category IN ({placeholders}))"
            params.extend(sanitized)

    sql += " ORDER BY starts_at ASC"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_item(r) for r in rows]
