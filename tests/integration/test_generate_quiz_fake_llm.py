"""Integração: geração de prova com LLM fake (sem rede) — Spec 007."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from src.core.config import get_settings
from src.core.db import apply_migrations, get_connection
from src.learning import LearningError, generate_quiz
from tests.conftest import FakeLLM

QUIZ_JSON = """
{"questions": [
  {"type":"mc","topic":"KNN","prompt":"O que é KNN?",
   "options":["a","b","c","d"],"correct_index":2,"source":"T1"},
  {"type":"open","topic":"TF-IDF","prompt":"Explique TF-IDF.",
   "answer_key":"frequência de termo x inverso de documento","source":"T2"}
]}
"""

# JSON malformado (falta vírgula entre membros) — força falha de parsing.
BROKEN_JSON = '{"questions": [ {"type": "mc" "prompt": "x"} ] }'


@pytest.fixture
def seeded_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[list[int]]:
    db = tmp_path / "gen.db"
    monkeypatch.setenv("JARVIS_DB_PATH", str(db))
    monkeypatch.setenv("JARVIS_LLM_API_KEY", "fake")
    get_settings.cache_clear()
    ids: list[int] = []
    with get_connection() as conn:
        apply_migrations(conn)
        for title, txt in [("Aula KNN", "vizinhos mais próximos"), ("TF-IDF", "frequência")]:
            cur = conn.execute(
                "INSERT INTO documents (title, source_path, type, char_count, chunk_count, content_hash) "
                "VALUES (?, ?, 'pdf', 10, 1, ?)",
                (title, f"/tmp/{title}.pdf", f"h-{title}"),
            )
            doc = int(cur.lastrowid or 0)
            ids.append(doc)
            conn.execute(
                "INSERT INTO chunks (document_id, position, text, char_start, char_end) "
                "VALUES (?, 0, ?, 0, 1)",
                (doc, txt),
            )
    yield ids
    get_settings.cache_clear()


async def test_gera_e_persiste_prova(seeded_docs: list[int]) -> None:
    fake = FakeLLM(scripted_completions=[QUIZ_JSON])
    quiz = await generate_quiz(fake, seeded_docs, num_mc=1, num_open=1)

    assert quiz.id is not None
    assert len(quiz.questions) == 2
    mc = next(q for q in quiz.questions if q.type == "mc")
    op = next(q for q in quiz.questions if q.type == "open")
    assert mc.correct_index == 2
    assert mc.source_chunk_id is not None         # mapeou T1 → chunk real
    assert op.answer_key

    # Persistido no DB?
    with get_connection() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM quiz_questions WHERE quiz_id = ?", (quiz.id,)
        ).fetchone()[0]
        assert n == 2


async def test_reparo_apos_json_malformado(seeded_docs: list[int]) -> None:
    """1a resposta malformada → reparo (2a resposta válida) → prova gerada."""
    fake = FakeLLM(scripted_completions=[BROKEN_JSON, QUIZ_JSON])
    quiz = await generate_quiz(fake, seeded_docs, num_mc=1, num_open=1)
    assert len(quiz.questions) == 2
    assert fake.scripted_completions == []  # consumiu as duas (geração + reparo)


async def test_falha_apos_reparo_tambem_malformado(seeded_docs: list[int]) -> None:
    fake = FakeLLM(scripted_completions=[BROKEN_JSON, BROKEN_JSON])
    with pytest.raises(LearningError):
        await generate_quiz(fake, seeded_docs, num_mc=1, num_open=1)
