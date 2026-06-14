"""Orquestração de alto nível das provas (gerar/corrigir) — Spec 007.

Usado pela UI (`exam.py`) e pelas tools (`tool_learning.py`). Obtém o `GemmaClient`
por parâmetro (UI injeta `state.gemma`; testes injetam fake) ou via client default.
"""

from __future__ import annotations

from src.core.db import get_connection
from src.domain.learning import (
    Attempt,
    DifficultyReport,
    Quiz,
    create_attempt,
    finalize_attempt,
    get_attempt,
    latest_graded_attempt_id,
    save_answer,
)
from src.learning.coach import build_difficulty_report
from src.learning.generator import generate_quiz
from src.learning.grader import aggregate_score, grade_mc, grade_open
from src.llm.client import get_default_client


def _resolve_gemma(gemma):  # type: ignore[no-untyped-def]
    return gemma if gemma is not None else get_default_client()


async def generate(
    document_ids: list[int],
    num_mc: int,
    num_open: int,
    *,
    title: str | None = None,
    idioma: str = "pt",
    gemma=None,  # type: ignore[no-untyped-def]
) -> Quiz:
    """Wrapper de geração que resolve o client default (caminho via tool)."""
    return await generate_quiz(
        _resolve_gemma(gemma), document_ids, num_mc, num_open, title=title, idioma=idioma
    )


async def difficulty_report(
    attempt_id: int | None = None,
    gemma=None,  # type: ignore[no-untyped-def]
) -> DifficultyReport | None:
    """Relatório de dificuldades da tentativa (ou da última graded). None se não há."""
    client = _resolve_gemma(gemma)
    with get_connection() as conn:
        aid = attempt_id if attempt_id is not None else latest_graded_attempt_id(conn)
        if aid is None:
            return None
        return await build_difficulty_report(client, conn, aid)


def _chunk_texts(conn, chunk_ids: list[int]) -> dict[int, str]:
    ids = [c for c in chunk_ids if c is not None]
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT id, text FROM chunks WHERE id IN ({ph})", ids
    ).fetchall()
    return {int(r["id"]): str(r["text"]) for r in rows}


def start_attempt(quiz_id: int) -> int:
    """Cria uma tentativa para a prova e retorna seu id."""
    with get_connection() as conn:
        return create_attempt(conn, quiz_id)


async def grade_attempt(
    quiz: Quiz,
    attempt_id: int,
    responses: dict[int, str],
    gemma=None,  # type: ignore[no-untyped-def]
) -> Attempt:
    """Corrige todas as respostas, persiste, calcula a nota 0-10 e finaliza.

    `responses` mapeia question_id -> resposta do usuario (MC: indice como string).
    """
    client = _resolve_gemma(gemma)
    awarded: list[float] = []
    maxes: list[float] = []

    with get_connection() as conn:
        src = _chunk_texts(
            conn, [q.source_chunk_id for q in quiz.questions if q.source_chunk_id]
        )

        for q in quiz.questions:
            assert q.id is not None
            resp = responses.get(q.id, "")
            if q.type == "mc":
                points, correct = grade_mc(q, resp)
                if not resp.strip():
                    feedback = "não respondida"
                elif correct:
                    feedback = "Correto"
                else:
                    certa = (
                        q.options[q.correct_index]
                        if q.options and q.correct_index is not None
                        else "?"
                    )
                    feedback = f"Incorreto — resposta certa: {certa}"
                is_correct: bool | None = correct
            else:  # open
                source_text = src.get(q.source_chunk_id) if q.source_chunk_id else None
                points, feedback = await grade_open(client, q, resp, source_text)
                is_correct = None

            save_answer(conn, attempt_id, q.id, resp, points, is_correct, feedback)
            awarded.append(points)
            maxes.append(q.max_points)

        score = aggregate_score(awarded, maxes)
        finalize_attempt(conn, attempt_id, score)
        attempt = get_attempt(conn, attempt_id)

    assert attempt is not None
    return attempt
