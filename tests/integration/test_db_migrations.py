"""Testes de integração para src/core/db.py migrations — T-001.14."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.core import db as db_module
from src.core.db import apply_migrations, get_connection


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r["name"] for r in rows}


def _index_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r["name"] for r in rows}


def test_apply_migrations_on_empty_db_creates_5_tables_and_6_indexes(tmp_path: Path) -> None:
    db_path = tmp_path / "t.db"
    with get_connection(db_path) as conn:
        v = apply_migrations(conn)
        # Após Fase 8 (calendar view), esperamos v=4 (001..004 aplicadas)
        assert v == 4
        tables = _table_names(conn)
        expected_base = {
            "documents", "chunks", "events", "tasks", "tool_call_logs",
            "chat_sessions", "chat_messages",
        }
        assert expected_base.issubset(tables)
        indexes = _index_names(conn)
        expected_indexes = {
            "idx_chunks_doc",
            "idx_events_starts_at",
            "idx_tasks_status",
            "idx_tasks_due_at",
            "idx_tool_call_logs_ts",
            "idx_tool_call_logs_tool",
        }
        # sqlite cria índices automáticos para UNIQUE; verificamos só os nossos
        assert expected_indexes.issubset(indexes)


def test_apply_migrations_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "t.db"
    with get_connection(db_path) as conn:
        v1 = apply_migrations(conn)
        v2 = apply_migrations(conn)
        v3 = apply_migrations(conn)
        # v final é 4 (001..004 aplicadas)
        assert v1 == v2 == v3 == 4


def test_db_ahead_of_code_raises(tmp_path: Path) -> None:
    db_path = tmp_path / "t.db"
    with get_connection(db_path) as conn:
        # Força versão futura, simulando que o usuário rodou código mais novo antes
        conn.execute("PRAGMA user_version = 99")
        with pytest.raises(RuntimeError) as excinfo:
            apply_migrations(conn)
        assert "99" in str(excinfo.value)


def test_atomicity_rollback_on_broken_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Injeta migration 002 quebrada e verifica que rollback é efetivo."""
    db_path = tmp_path / "t.db"
    # Cria diretório de migrations local com 001 + 002_broken
    local_migrations = tmp_path / "migrations"
    local_migrations.mkdir()

    # Copia 001_initial.sql real
    real_001 = Path(__file__).parents[2] / "src" / "core" / "migrations" / "001_initial.sql"
    (local_migrations / "001_initial.sql").write_text(
        real_001.read_text(encoding="utf-8"), encoding="utf-8"
    )

    # Cria 002 com 2 statements: o 1º válido (cria tabela), o 2º inválido
    broken = """
    CREATE TABLE will_not_persist (id INTEGER PRIMARY KEY);
    CREATE TABLE invalid_syntax (((;
    """
    (local_migrations / "002_broken.sql").write_text(broken, encoding="utf-8")

    # Aponta o runner para essa pasta
    monkeypatch.setattr(db_module, "MIGRATIONS_DIR", local_migrations)

    with get_connection(db_path) as conn:
        # 001 aplica com sucesso (v0 -> v1), 002_broken falha no 2o statement ->
        # rollback do 002 (mas 001 ja foi commitado e fica em v1).
        with pytest.raises(sqlite3.OperationalError):
            apply_migrations(conn)

        # Pós-falha: user_version permanece em 1 (não foi para 2)
        v = conn.execute("PRAGMA user_version").fetchone()[0]
        assert v == 1, f"esperado v=1 após rollback, obtido v={v}"

        # A tabela 'will_not_persist' do 1º statement de 002 NÃO foi persistida
        names = _table_names(conn)
        assert "will_not_persist" not in names, (
            f"rollback falhou: 'will_not_persist' persistiu — tabelas={names}"
        )
