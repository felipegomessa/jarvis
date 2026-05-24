"""Serviços de alto nível para sessões de chat."""

from __future__ import annotations

import sqlite3

from src.domain.chat.repo import (
    add_message,
    create_session,
    next_position,
)


def title_from_prompt(prompt: str, max_chars: int = 60) -> str:
    """Gera um título conciso a partir do primeiro prompt do usuário."""
    clean = " ".join(prompt.strip().split())
    if len(clean) <= max_chars:
        return clean or "Nova conversa"
    return clean[: max_chars - 1] + "…"


def start_session_with_first_message(
    conn: sqlite3.Connection, first_user_message: str
) -> int:
    """Cria sessão usando o primeiro prompt como título e grava a 1ª mensagem."""
    title = title_from_prompt(first_user_message)
    session_id = create_session(conn, title)
    add_message(
        conn,
        session_id,
        role="user",
        content=first_user_message,
        position=next_position(conn, session_id),
    )
    return session_id
