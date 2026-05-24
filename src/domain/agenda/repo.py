"""Repositorio CRUD de eventos — RF-003.2."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from src.domain.agenda.models import Event, EventCreate


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") if dt else None


def _row_to_event(row: sqlite3.Row) -> Event:
    return Event(
        id=int(row["id"]),
        title=str(row["title"]),
        description=row["description"],
        starts_at=datetime.fromisoformat(row["starts_at"]),
        ends_at=datetime.fromisoformat(row["ends_at"]) if row["ends_at"] else None,
        kind=row["kind"],
        location=row["location"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def create_event(conn: sqlite3.Connection, data: EventCreate) -> Event:
    cur = conn.execute(
        """
        INSERT INTO events (title, description, starts_at, ends_at, kind, location)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data.title,
            data.description,
            _iso(data.starts_at),
            _iso(data.ends_at),
            data.kind,
            data.location,
        ),
    )
    new_id = int(cur.lastrowid or 0)
    ev = get_event(conn, new_id)
    assert ev is not None, "evento recém-criado não encontrado"
    return ev


def get_event(conn: sqlite3.Connection, event_id: int) -> Event | None:
    row = conn.execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    return _row_to_event(row) if row else None


def list_events(
    conn: sqlite3.Connection,
    start: datetime,
    end: datetime,
    kind: str | None = None,
) -> list[Event]:
    """Lista eventos com `starts_at` dentro de [start, end). Filtra por kind se dado."""
    sql = "SELECT * FROM events WHERE starts_at >= ? AND starts_at < ?"
    params: list[Any] = [_iso(start), _iso(end)]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " ORDER BY starts_at ASC"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_event(r) for r in rows]


def list_all_events(conn: sqlite3.Connection) -> list[Event]:
    rows = conn.execute("SELECT * FROM events ORDER BY starts_at ASC").fetchall()
    return [_row_to_event(r) for r in rows]


def update_event(
    conn: sqlite3.Connection, event_id: int, **patch: Any
) -> Event | None:
    if not patch:
        return get_event(conn, event_id)

    allowed = {"title", "description", "starts_at", "ends_at", "kind", "location"}
    sets: list[str] = []
    vals: list[Any] = []
    for k, v in patch.items():
        if k not in allowed:
            raise ValueError(f"campo não permitido em update_event: {k}")
        if isinstance(v, datetime):
            v = _iso(v)
        sets.append(f"{k} = ?")
        vals.append(v)
    sets.append("updated_at = (datetime('now'))")

    sql = f"UPDATE events SET {', '.join(sets)} WHERE id = ?"
    vals.append(event_id)
    conn.execute(sql, vals)
    return get_event(conn, event_id)


def delete_event(conn: sqlite3.Connection, event_id: int) -> bool:
    cur = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    return (cur.rowcount or 0) > 0
