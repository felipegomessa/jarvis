"""Tools de tarefas (listar_tarefas, adicionar_tarefa, concluir_tarefa)."""

from __future__ import annotations

import asyncio
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


async def _concluir_tarefa(args: dict[str, Any]) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        task_id = int(args["task_id"])
        with get_connection() as conn:
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
            description="Marca uma tarefa como concluída.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID da tarefa."},
                },
                "required": ["task_id"],
            },
            handler=_concluir_tarefa,
            examples=[
                {"tool": "concluir_tarefa", "args": {"task_id": 3}},
            ],
        )
    )


_register()
