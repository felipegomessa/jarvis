"""Repositório CRUD de provas/tentativas/respostas — Spec 007 / D-013."""

from __future__ import annotations

import json
import sqlite3

from src.domain.learning.models import (
    Answer,
    Attempt,
    Question,
    Quiz,
    TopicScore,
)


def _row_to_question(row: sqlite3.Row) -> Question:
    opts_raw = row["options_json"]
    return Question(
        id=int(row["id"]),
        type=row["type"],
        prompt=str(row["prompt"]),
        topic=str(row["topic"] or ""),
        options=json.loads(opts_raw) if opts_raw else None,
        correct_index=row["correct_index"],
        answer_key=row["answer_key"],
        source_document_id=row["source_document_id"],
        source_chunk_id=row["source_chunk_id"],
        max_points=float(row["max_points"]),
    )


def create_quiz(conn: sqlite3.Connection, title: str, document_ids: list[int]) -> int:
    """Cria a prova + associações de documentos-fonte. Retorna o quiz_id."""
    if not document_ids:
        raise ValueError("a prova precisa de ao menos 1 documento-fonte")
    cur = conn.execute("INSERT INTO quizzes (title) VALUES (?)", (title.strip(),))
    quiz_id = int(cur.lastrowid or 0)
    conn.executemany(
        "INSERT INTO quiz_documents (quiz_id, document_id) VALUES (?, ?)",
        [(quiz_id, d) for d in document_ids],
    )
    return quiz_id


def add_questions(
    conn: sqlite3.Connection, quiz_id: int, questions: list[Question]
) -> None:
    """Persiste as questões de uma prova (posição = ordem na lista)."""
    for pos, q in enumerate(questions):
        opts = json.dumps(q.options, ensure_ascii=False) if q.options else None
        conn.execute(
            """
            INSERT INTO quiz_questions
                (quiz_id, position, type, prompt, options_json, correct_index,
                 answer_key, topic, source_document_id, source_chunk_id, max_points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quiz_id, pos, q.type, q.prompt, opts, q.correct_index,
                q.answer_key, q.topic, q.source_document_id, q.source_chunk_id,
                q.max_points,
            ),
        )


def get_quiz(conn: sqlite3.Connection, quiz_id: int) -> Quiz | None:
    qrow = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not qrow:
        return None
    docs = [
        int(r["document_id"])
        for r in conn.execute(
            "SELECT document_id FROM quiz_documents WHERE quiz_id = ?", (quiz_id,)
        ).fetchall()
    ]
    qs = [
        _row_to_question(r)
        for r in conn.execute(
            "SELECT * FROM quiz_questions WHERE quiz_id = ? ORDER BY position",
            (quiz_id,),
        ).fetchall()
    ]
    return Quiz(
        id=quiz_id,
        title=str(qrow["title"]),
        documents=docs,
        questions=qs,
        status=str(qrow["status"]),
    )


def list_quizzes(conn: sqlite3.Connection, limit: int = 30) -> list[Quiz]:
    rows = conn.execute(
        "SELECT id FROM quizzes ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    out = [get_quiz(conn, int(r["id"])) for r in rows]
    return [q for q in out if q is not None]


def create_attempt(conn: sqlite3.Connection, quiz_id: int) -> int:
    cur = conn.execute("INSERT INTO quiz_attempts (quiz_id) VALUES (?)", (quiz_id,))
    return int(cur.lastrowid or 0)


def save_answer(
    conn: sqlite3.Connection,
    attempt_id: int,
    question_id: int,
    response: str,
    awarded_points: float | None,
    is_correct: bool | None,
    feedback: str | None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO quiz_answers
            (attempt_id, question_id, response, awarded_points, is_correct, feedback)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            attempt_id,
            question_id,
            response,
            awarded_points,
            None if is_correct is None else int(is_correct),
            feedback,
        ),
    )
    return int(cur.lastrowid or 0)


def finalize_attempt(conn: sqlite3.Connection, attempt_id: int, score: float) -> None:
    conn.execute(
        "UPDATE quiz_attempts SET score = ?, status = 'graded', "
        "finished_at = datetime('now') WHERE id = ?",
        (score, attempt_id),
    )


def get_attempt(conn: sqlite3.Connection, attempt_id: int) -> Attempt | None:
    arow = conn.execute(
        "SELECT * FROM quiz_attempts WHERE id = ?", (attempt_id,)
    ).fetchone()
    if not arow:
        return None
    answers = [
        Answer(
            question_id=int(r["question_id"]),
            response=str(r["response"]),
            awarded_points=r["awarded_points"],
            is_correct=None if r["is_correct"] is None else bool(r["is_correct"]),
            feedback=r["feedback"],
        )
        for r in conn.execute(
            "SELECT * FROM quiz_answers WHERE attempt_id = ? ORDER BY id", (attempt_id,)
        ).fetchall()
    ]
    return Attempt(
        id=attempt_id,
        quiz_id=int(arow["quiz_id"]),
        score=arow["score"],
        status=str(arow["status"]),
        answers=answers,
    )


def latest_graded_attempt_id(
    conn: sqlite3.Connection, quiz_id: int | None = None
) -> int | None:
    """Id da tentativa graded mais recente (de um quiz ou global). None se não houver."""
    if quiz_id is None:
        row = conn.execute(
            "SELECT id FROM quiz_attempts WHERE status = 'graded' "
            "ORDER BY finished_at DESC LIMIT 1"
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id FROM quiz_attempts WHERE status = 'graded' AND quiz_id = ? "
            "ORDER BY finished_at DESC LIMIT 1",
            (quiz_id,),
        ).fetchone()
    return int(row["id"]) if row else None


def topic_breakdown(conn: sqlite3.Connection, attempt_id: int) -> list[TopicScore]:
    """Agrega pontos obtidos/possíveis por tópico para uma tentativa."""
    rows = conn.execute(
        """
        SELECT q.topic AS topic,
               SUM(q.max_points) AS possible,
               SUM(COALESCE(a.awarded_points, 0)) AS earned
          FROM quiz_answers a
          JOIN quiz_questions q ON q.id = a.question_id
         WHERE a.attempt_id = ?
         GROUP BY q.topic
         ORDER BY (earned / possible) ASC
        """,
        (attempt_id,),
    ).fetchall()
    return [
        TopicScore(
            topic=str(r["topic"] or "(geral)"),
            earned=float(r["earned"] or 0.0),
            possible=float(r["possible"] or 0.0),
        )
        for r in rows
    ]
