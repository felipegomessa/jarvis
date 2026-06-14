"""Integração: leitura por documento (get_document_chunks) — Spec 007 / Falha 4."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from src.core.config import get_settings
from src.core.db import apply_migrations, get_connection
from src.rag.retrieve import get_document_chunks


@pytest.fixture
def seeded_doc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    db = tmp_path / "doc.db"
    monkeypatch.setenv("JARVIS_DB_PATH", str(db))
    monkeypatch.setenv("JARVIS_LLM_API_KEY", "fake")
    get_settings.cache_clear()
    with get_connection() as conn:
        apply_migrations(conn)
        cur = conn.execute(
            "INSERT INTO documents (title, source_path, type, char_count, chunk_count, content_hash) "
            "VALUES ('Doc', '/tmp/d.pdf', 'pdf', 30, 3, 'h')"
        )
        doc = int(cur.lastrowid or 0)
        # Inserção fora de ordem para validar ORDER BY position.
        for pos, txt in [(2, "terceiro"), (0, "primeiro"), (1, "segundo")]:
            conn.execute(
                "INSERT INTO chunks (document_id, position, text, char_start, char_end) "
                "VALUES (?, ?, ?, 0, 1)",
                (doc, pos, txt),
            )
    yield doc
    get_settings.cache_clear()


def test_retorna_em_ordem_de_posicao(seeded_doc: int) -> None:
    chunks = get_document_chunks(seeded_doc)
    assert [c.position for c in chunks] == [0, 1, 2]
    assert [c.text for c in chunks] == ["primeiro", "segundo", "terceiro"]
    assert all(c.distance == 0.0 for c in chunks)


def test_limit_restringe(seeded_doc: int) -> None:
    chunks = get_document_chunks(seeded_doc, limit=2)
    assert len(chunks) == 2
    assert chunks[0].position == 0


def test_documento_inexistente_lista_vazia(seeded_doc: int) -> None:
    assert get_document_chunks(99999) == []
