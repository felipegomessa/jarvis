"""Testes de migration 002 (RAG)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.core.db import apply_migrations, get_connection


def test_migration_002_applies_and_bumps_version(tmp_path: Path) -> None:
    db_path = tmp_path / "t.db"
    with get_connection(db_path) as conn:
        v = apply_migrations(conn)
        # apply_migrations aplica TODAS as migrations; após a Spec 007, v=5
        assert v == 5

    with get_connection(db_path) as conn:
        # content_hash existe em documents
        cols = {
            r["name"]
            for r in conn.execute("PRAGMA table_info(documents)").fetchall()
        }
        assert "content_hash" in cols

        # chunk_vecs existe (virtual table)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_vecs'"
        ).fetchone()
        assert row is not None


def test_chunk_vecs_accepts_384_float_blob(tmp_path: Path) -> None:
    db_path = tmp_path / "t.db"
    with get_connection(db_path) as conn:
        apply_migrations(conn)
        # Cria 1 documento + 1 chunk para satisfazer referencia logica
        conn.execute("BEGIN")
        cur = conn.execute(
            "INSERT INTO documents (title, source_path, type, content_hash) "
            "VALUES ('t', '/tmp/x.txt', 'txt', 'h')"
        )
        doc_id = cur.lastrowid
        cur2 = conn.execute(
            "INSERT INTO chunks (document_id, position, text, char_start, char_end) "
            "VALUES (?, 0, 'hello', 0, 5)",
            (doc_id,),
        )
        chunk_id = cur2.lastrowid

        emb = np.random.rand(384).astype(np.float32)
        conn.execute(
            "INSERT INTO chunk_vecs (chunk_id, embedding) VALUES (?, ?)",
            (chunk_id, emb.tobytes()),
        )
        conn.execute("COMMIT")

        # Conta
        n = conn.execute("SELECT COUNT(*) FROM chunk_vecs").fetchone()[0]
        assert n == 1
