"""Testes do repositório de sessões de chat — Fase 3."""

from __future__ import annotations

import sqlite3

import pytest

from src.domain.chat.repo import (
    add_message,
    create_session,
    delete_session,
    get_session,
    list_messages_of_session,
    list_recent_sessions,
    next_position,
    update_session_timestamp,
    update_session_title,
)


def test_create_and_get_session(tmp_db: sqlite3.Connection) -> None:
    sid = create_session(tmp_db, "Primeira conversa")
    assert sid > 0
    s = get_session(tmp_db, sid)
    assert s is not None
    assert s.title == "Primeira conversa"


def test_add_messages_and_list_ordered(tmp_db: sqlite3.Connection) -> None:
    sid = create_session(tmp_db, "Chat ordenado")
    add_message(tmp_db, sid, role="user", content="Olá", position=0)
    add_message(tmp_db, sid, role="assistant", content="Oi, como posso ajudar?", position=1)
    add_message(
        tmp_db, sid, role="tool",
        content='{"result": "ok"}',
        metadata={"tool": "x", "duration_ms": 5},
        position=2,
    )

    msgs = list_messages_of_session(tmp_db, sid)
    assert len(msgs) == 3
    assert [m.role for m in msgs] == ["user", "assistant", "tool"]
    assert msgs[2].metadata == {"tool": "x", "duration_ms": 5}


def test_next_position_increments(tmp_db: sqlite3.Connection) -> None:
    sid = create_session(tmp_db, "Pos")
    assert next_position(tmp_db, sid) == 0
    add_message(tmp_db, sid, role="user", content="a", position=0)
    assert next_position(tmp_db, sid) == 1
    add_message(tmp_db, sid, role="assistant", content="b", position=1)
    assert next_position(tmp_db, sid) == 2


def test_position_uniqueness(tmp_db: sqlite3.Connection) -> None:
    """UNIQUE(session_id, position) impede colisão."""
    sid = create_session(tmp_db, "Unique")
    add_message(tmp_db, sid, role="user", content="a", position=0)
    with pytest.raises(sqlite3.IntegrityError):
        add_message(tmp_db, sid, role="user", content="b", position=0)


def test_list_recent_sessions_orders_by_updated(tmp_db: sqlite3.Connection) -> None:
    import time
    s1 = create_session(tmp_db, "Antiga")
    time.sleep(1.05)  # garante datetime('now') diferente em segundos
    s2 = create_session(tmp_db, "Recente")
    recents = list_recent_sessions(tmp_db, limit=10)
    assert recents[0].id == s2
    assert recents[1].id == s1


def test_update_session_title(tmp_db: sqlite3.Connection) -> None:
    sid = create_session(tmp_db, "Original")
    assert update_session_title(tmp_db, sid, "Novo título") is True
    s = get_session(tmp_db, sid)
    assert s is not None and s.title == "Novo título"


def test_update_session_timestamp(tmp_db: sqlite3.Connection) -> None:
    import time
    sid = create_session(tmp_db, "T")
    s1 = get_session(tmp_db, sid)
    assert s1 is not None
    time.sleep(1.05)
    update_session_timestamp(tmp_db, sid)
    s2 = get_session(tmp_db, sid)
    assert s2 is not None
    assert s2.updated_at >= s1.updated_at


def test_delete_session_cascades_messages(tmp_db: sqlite3.Connection) -> None:
    sid = create_session(tmp_db, "ToDelete")
    add_message(tmp_db, sid, role="user", content="a", position=0)
    add_message(tmp_db, sid, role="assistant", content="b", position=1)
    assert delete_session(tmp_db, sid) is True
    assert get_session(tmp_db, sid) is None
    assert list_messages_of_session(tmp_db, sid) == []
