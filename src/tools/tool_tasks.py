"""Tools de tarefas (listar_tarefas, adicionar_tarefa, concluir_tarefa)."""

from __future__ import annotations

import asyncio
import unicodedata
from datetime import datetime
from typing import Any

from loguru import logger

from src.core.db import get_connection
from src.domain.tasks import (
    TaskCreate,
    complete_task,
    create_task,
    list_tasks,
    overdue_tasks,
)
from src.tools.registry import ToolDefinition, get_registry


def _norm(s: str) -> str:
    """Normaliza para comparação tolerante: minúsculas, sem acento, sem espaços nas bordas."""
    no_accents = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    return no_accents.casefold().strip()


def _task_to_dict(t: Any) -> dict[str, Any]:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "due_at": t.due_at.isoformat() if t.due_at else None,
        "status": t.status,
        "priority": t.priority,
        "created_at": t.created_at.isoformat(),
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


async def _listar_tarefas(args: dict[str, Any]) -> dict[str, Any]:
    status = args.get("status")  # 'pending', 'done' ou None
    somente_atrasadas = bool(args.get("somente_atrasadas", False))

    def _run() -> dict[str, Any]:
        with get_connection() as conn:
            items = (
                overdue_tasks(conn) if somente_atrasadas else list_tasks(conn, status=status)
            )
        return {
            "status_filter": status,
            "somente_atrasadas": somente_atrasadas,
            "count": len(items),
            "tasks": [_task_to_dict(t) for t in items],
        }

    return await asyncio.to_thread(_run)


async def _adicionar_tarefa(args: dict[str, Any]) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        due_at = None
        if args.get("due_at"):
            try:
                due_at = datetime.fromisoformat(args["due_at"])
            except ValueError as e:
                raise ValueError(
                    f"due_at deve ser ISO8601 (ex: '2026-06-10T23:59:00'): {e}"
                ) from e
        tc = TaskCreate(
            title=args["title"],
            description=args.get("description"),
            due_at=due_at,
            priority=args.get("priority", 0),
        )
        with get_connection() as conn:
            t = create_task(conn, tc)
            logger.info(f"tarefa criada via tool: id={t.id}, title={t.title}")
        return _task_to_dict(t)

    return await asyncio.to_thread(_run)


def _resolve_task_id_by_title(conn: Any, titulo: str) -> int:
    """Resolve um título para o id de uma tarefa PENDENTE única.

    Prioriza correspondência exata (sem acento/caixa); cai para 'contém' se não
    houver exata. Levanta ValueError se nada casar ou se houver ambiguidade.
    """
    alvo = _norm(titulo)
    pendentes = list_tasks(conn, status="pending")
    exatas = [t for t in pendentes if _norm(t.title) == alvo]
    candidatos = exatas or [t for t in pendentes if alvo in _norm(t.title)]

    if not candidatos:
        raise ValueError(
            f"nenhuma tarefa pendente corresponde a {titulo!r}. "
            "Use `listar_tarefas` para ver os títulos exatos."
        )
    if len(candidatos) > 1:
        opcoes = ", ".join(f"id={t.id} ({t.title})" for t in candidatos)
        raise ValueError(
            f"mais de uma tarefa pendente corresponde a {titulo!r}: {opcoes}. "
            "Repita informando o `task_id` específico."
        )
    return candidatos[0].id


async def _concluir_tarefa(args: dict[str, Any]) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        with get_connection() as conn:
            # Aceita `task_id` direto ou `titulo` (resolvido para um id único).
            if args.get("task_id") is not None:
                task_id = int(args["task_id"])
            elif args.get("titulo"):
                task_id = _resolve_task_id_by_title(conn, str(args["titulo"]))
            else:
                raise ValueError("informe `task_id` ou `titulo` da tarefa a concluir")

            t = complete_task(conn, task_id)
            if t is None:
                raise ValueError(f"tarefa não encontrada: id={task_id}")
            logger.info(f"tarefa concluída via tool: id={t.id}")
        return _task_to_dict(t)

    return await asyncio.to_thread(_run)


def _register() -> None:
    reg = get_registry()
    reg.register(
        ToolDefinition(
            name="listar_tarefas",
            description=(
                "Lista as tarefas da lista de afazeres. Use para mostrar pendentes, "
                "concluídas, ou apenas as atrasadas (com prazo vencido)."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "done"],
                        "description": "Opcional. Filtra por status.",
                    },
                    "somente_atrasadas": {
                        "type": "boolean",
                        "description": "Se true, retorna apenas tarefas pending com due_at vencido.",
                    },
                },
            },
            handler=_listar_tarefas,
            examples=[
                {"tool": "listar_tarefas", "args": {"status": "pending"}},
                {"tool": "listar_tarefas", "args": {"somente_atrasadas": True}},
            ],
        )
    )
    reg.register(
        ToolDefinition(
            name="adicionar_tarefa",
            description=(
                "Cria uma nova tarefa na lista de afazeres. Use quando o usuário "
                "pedir para anotar/criar/lembrar de algo que ELE PRECISA FAZER até "
                "um prazo (estudar, escrever, entregar trabalho, ler capítulo)."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "due_at": {
                        "type": "string",
                        "description": "ISO8601 opcional, ex: '2026-06-10T23:59:00'",
                    },
                    "priority": {
                        "type": "integer",
                        "enum": [0, 1, 2],
                        "description": "0=normal, 1=alta, 2=urgente. Default 0.",
                    },
                },
                "required": ["title"],
            },
            handler=_adicionar_tarefa,
            examples=[
                {
                    "tool": "adicionar_tarefa",
                    "args": {
                        "title": "Estudar Naive Bayes",
                        "priority": 1,
                        "due_at": "2026-06-08T22:00:00",
                    },
                }
            ],
        )
    )
    reg.register(
        ToolDefinition(
            name="concluir_tarefa",
            description=(
                "Marca uma tarefa como concluída. Informe o `task_id` (preferível, "
                "obtido via `listar_tarefas`) OU o `titulo` da tarefa pendente — "
                "neste caso a tarefa é resolvida por correspondência de título "
                "(erro se nenhuma ou mais de uma casar)."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID da tarefa."},
                    "titulo": {
                        "type": "string",
                        "description": (
                            "Título (ou parte dele) de uma tarefa pendente. "
                            "Alternativa ao task_id."
                        ),
                    },
                },
            },
            handler=_concluir_tarefa,
            examples=[
                {"tool": "concluir_tarefa", "args": {"task_id": 3}},
                {
                    "tool": "concluir_tarefa",
                    "args": {"titulo": "estudar regressão logística"},
                },
            ],
        )
    )


_register()
