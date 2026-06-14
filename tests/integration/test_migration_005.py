"""Integração: migration 005 (tabelas de provas) — Spec 007."""

from __future__ import annotations

from pathlib import Path

from src.core.db import apply_migrations, get_connection


def test_migration_005_aplica_e_cria_tabelas(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    with get_connection(db) as conn:
        v = apply_migrations(conn)
        assert v >= 5
        assert int(conn.execute("PRAGMA user_version").fetchone()[0]) >= 5

        nomes = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for t in (
            "quizzes",
            "quiz_documents",
            "quiz_questions",
            "quiz_attempts",
            "quiz_answers",
        ):
            assert t in nomes


def test_migration_005_cascade_apaga_questoes(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    with get_connection(db) as conn:
        apply_migrations(conn)
        conn.execute("INSERT INTO quizzes (title) VALUES ('p')")
        qid = conn.execute("SELECT id FROM quizzes").fetchone()["id"]
        conn.execute(
            "INSERT INTO quiz_questions (quiz_id, position, type, prompt, answer_key) "
            "VALUES (?, 0, 'open', 'q', 'k')",
            (qid,),
        )
        conn.execute("DELETE FROM quizzes WHERE id = ?", (qid,))
        n = conn.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0]
        assert n == 0  # CASCADE
