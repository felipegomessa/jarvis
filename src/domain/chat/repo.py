"""Repositório CRUD de sessões e mensagens de chat — Fase 3."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from src.domain.chat.models import ChatMessage, ChatSession, MessageRole


def _row_to_session(row: sqlite3.Row) -> ChatSession:
    return ChatSession(
        id=int(row["id"]),
        title=str(row["title"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_message(row: sqlite3.Row) -> ChatMessage:
    md_raw = row["metadata_json"]
    md = json.loads(md_raw) if md_raw else None
    return ChatMessage(
        id=int(row["id"]),
        session_id=int(row["session_id"]),
        role=row["role"],
        content=str(row["content"]),
        metadata=md,
        position=int(row["position"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def create_session(conn: sqlite3.Connection, title: str) -> int:
    """Cria uma nova sessão e retorna seu id."""
    cur = conn.execute(
        "INSERT INTO chat_sessions (title) VALUES (?)",
        (title.strip(),),
    )
    return int(cur.lastrowid or 0)


def get_session(conn: sqlite3.Connection, session_id: int) -> ChatSession | None:
    row = conn.execute(
        "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    return _row_to_session(row) if row else None


def list_recent_sessions(
    conn: sqlite3.Connection, limit: int = 15
) -> list[ChatSession]:
    """Lista as N sessões mais recentemente atualizadas."""
    rows = conn.execute(
        "SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [_row_to_session(r) for r in rows]


def update_session_title(
    conn: sqlite3.Connection, session_id: int, title: str
) -> bool:
    cur = conn.execute(
        "UPDATE chat_sessions SET title = ?, updated_at = datetime('now') "
        "WHERE id = ?",
        (title.strip(), session_id),
    )
    return (cur.rowcount or 0) > 0


def update_session_timestamp(conn: sqlite3.Connection, session_id: int) -> None:
    """Marca a sessão como recém-modificada (para reorder na sidebar)."""
    conn.execute(
        "UPDATE chat_sessions SET updated_at = datetime('now') WHERE id = ?",
        (session_id,),
    )


def delete_session(conn: sqlite3.Connection, session_id: int) -> bool:
    """Remove uma sessão (cascade limpa mensagens)."""
    cur = conn.execute(
        "DELETE FROM chat_sessions WHERE id = ?", (session_id,)
    )
    return (cur.rowcount or 0) > 0


def add_message(
    conn: sqlite3.Connection,
    session_id: int,
    role: MessageRole,
    content: str,
    position: int,
    metadata: dict[str, Any] | None = None,
) -> int:
    """Insere uma mensagem na sessão. Retorna o id."""
    md_json = (
        json.dumps(metadata, ensure_ascii=False, default=str) if metadata else None
    )
    cur = conn.execute(
        """
        INSERT INTO chat_messages
            (session_id, role, content, metadata_json, position)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, role, content, md_json, position),
    )
    return int(cur.lastrowid or 0)


def list_messages_of_session(
    conn: sqlite3.Connection, session_id: int
) -> list[ChatMessage]:
    rows = conn.execute(
        "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY position ASC",
        (session_id,),
    ).fetchall()
    return [_row_to_message(r) for r in rows]


def next_position(conn: sqlite3.Connection, session_id: int) -> int:
    """Próxima posição livre para nova mensagem (max+1, ou 0 se vazia)."""
    row = conn.execute(
        "SELECT COALESCE(MAX(position) + 1, 0) AS next FROM chat_messages "
        "WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return int(row["next"])
