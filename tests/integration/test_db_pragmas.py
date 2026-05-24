"""Testes de integração para PRAGMAs e extensão sqlite-vec — T-001.14."""

from __future__ import annotations

from pathlib import Path

from src.core.db import get_connection, smoke_check_vec


def test_pragma_journal_mode_wal(tmp_path: Path) -> None:
    with get_connection(tmp_path / "p.db") as conn:
        row = conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0].lower() == "wal"


def test_pragma_foreign_keys_on(tmp_path: Path) -> None:
    with get_connection(tmp_path / "p.db") as conn:
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1


def test_pragma_busy_timeout(tmp_path: Path) -> None:
    with get_connection(tmp_path / "p.db") as conn:
        row = conn.execute("PRAGMA busy_timeout").fetchone()
        assert row[0] == 3000


def test_pragma_synchronous_normal(tmp_path: Path) -> None:
    with get_connection(tmp_path / "p.db") as conn:
        row = conn.execute("PRAGMA synchronous").fetchone()
        # NORMAL == 1
        assert row[0] == 1


def test_sqlite_vec_extension_loaded(tmp_path: Path) -> None:
    with get_connection(tmp_path / "p.db") as conn:
        version = smoke_check_vec(conn)
        assert version  # string não-vazia
        assert isinstance(version, str)
