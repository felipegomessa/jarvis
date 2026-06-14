"""Integração: repositório de aprendizado (quiz→attempt→answers→breakdown)."""

from __future__ import annotations

import sqlite3

from src.domain.learning import (
    Question,
    add_questions,
    create_attempt,
    create_quiz,
    finalize_attempt,
    get_attempt,
    get_quiz,
    latest_graded_attempt_id,
    save_answer,
    topic_breakdown,
)


def _seed_document(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        "INSERT INTO documents (title, source_path, type, char_count, chunk_count, content_hash) "
        "VALUES ('Doc', '/tmp/d.pdf', 'pdf', 10, 1, 'h1')"
    )
    return int(cur.lastrowid or 0)


def test_quiz_crud_e_breakdown(tmp_db: sqlite3.Connection) -> None:
    doc = _seed_document(tmp_db)
    quiz_id = create_quiz(tmp_db, "Prova teste", [doc])
    add_questions(
        tmp_db,
        quiz_id,
        [
            Question(type="mc", prompt="q1", options=["a", "b", "c", "d"],
                     correct_index=0, topic="KNN", max_points=1.0),
            Question(type="open", prompt="q2", answer_key="resposta",
                     topic="KNN", max_points=1.0),
            Question(type="open", prompt="q3", answer_key="resp",
                     topic="TF-IDF", max_points=1.0),
        ],
    )

    quiz = get_quiz(tmp_db, quiz_id)
    assert quiz is not None
    assert quiz.documents == [doc]
    assert len(quiz.questions) == 3

    attempt_id = create_attempt(tmp_db, quiz_id)
    ids = [q.id for q in quiz.questions]
    save_answer(tmp_db, attempt_id, ids[0], "0", 1.0, True, "Correto")    # KNN acertou
    save_answer(tmp_db, attempt_id, ids[1], "x", 0.0, None, "fraco")      # KNN errou
    save_answer(tmp_db, attempt_id, ids[2], "y", 1.0, None, "ok")         # TF-IDF ok
    finalize_attempt(tmp_db, attempt_id, 6.7)

    attempt = get_attempt(tmp_db, attempt_id)
    assert attempt is not None
    assert attempt.status == "graded"
    assert attempt.score == 6.7
    assert len(attempt.answers) == 3

    assert latest_graded_attempt_id(tmp_db) == attempt_id

    breakdown = {t.topic: t for t in topic_breakdown(tmp_db, attempt_id)}
    assert breakdown["KNN"].earned == 1.0 and breakdown["KNN"].possible == 2.0
    assert breakdown["TF-IDF"].ratio == 1.0
