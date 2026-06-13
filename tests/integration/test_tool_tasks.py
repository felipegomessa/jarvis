"""Testes da resolução de tarefa por título em concluir_tarefa (M2)."""

from __future__ import annotations

import sqlite3

import pytest

from src.domain.tasks import TaskCreate, create_task
from src.tools.tool_tasks import _resolve_task_id_by_title


def _seed(conn: sqlite3.Connection) -> dict[str, int]:
    ids = {}
    for title in [
        "Estudar regressão logística",
        "Ler capítulo sobre redes neurais",
        "Resolver lista de embeddings",
    ]:
        t = create_task(conn, TaskCreate(title=title))
        ids[title] = t.id
    return ids


def test_resolve_exact_match_accent_insensitive(tmp_db: sqlite3.Connection) -> None:
    ids = _seed(tmp_db)
    # Sem acento e em caixa diferente deve resolver para a tarefa exata.
    rid = _resolve_task_id_by_title(tmp_db, "estudar regressao logistica")
    assert rid == ids["Estudar regressão logística"]


def test_resolve_substring_match(tmp_db: sqlite3.Connection) -> None:
    ids = _seed(tmp_db)
    rid = _resolve_task_id_by_title(tmp_db, "redes neurais")
    assert rid == ids["Ler capítulo sobre redes neurais"]


def test_resolve_not_found_raises(tmp_db: sqlite3.Connection) -> None:
    _seed(tmp_db)
    with pytest.raises(ValueError, match="nenhuma tarefa pendente"):
        _resolve_task_id_by_title(tmp_db, "assunto inexistente")


def test_resolve_ambiguous_raises(tmp_db: sqlite3.Connection) -> None:
    # Dois títulos contendo "lista" → ambiguidade.
    create_task(tmp_db, TaskCreate(title="Resolver lista de embeddings"))
    create_task(tmp_db, TaskCreate(title="Revisar lista de exercícios"))
    with pytest.raises(ValueError, match="mais de uma tarefa"):
        _resolve_task_id_by_title(tmp_db, "lista")


def test_resolve_ignores_done_tasks(tmp_db: sqlite3.Connection) -> None:
    from src.domain.tasks import complete_task

    t = create_task(tmp_db, TaskCreate(title="Tarefa já feita"))
    complete_task(tmp_db, t.id)
    # Concluída não é candidata → não encontra.
    with pytest.raises(ValueError, match="nenhuma tarefa pendente"):
        _resolve_task_id_by_title(tmp_db, "já feita")
