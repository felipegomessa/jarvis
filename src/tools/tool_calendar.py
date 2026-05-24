"""Tool unificada de calendário (eventos + tarefas) — Fase 8."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from loguru import logger

from src.core.db import get_connection
from src.domain.calendar_view import list_calendar_items
from src.tools.registry import ToolDefinition, get_registry


async def _consultar_calendario(args: dict[str, Any]) -> dict[str, Any]:
    try:
        start = datetime.fromisoformat(args["data_inicio"])
        end = datetime.fromisoformat(args["data_fim"])
    except (KeyError, ValueError) as e:
        raise ValueError(
            f"data_inicio e data_fim devem ser ISO8601 "
            f"(ex: '2026-06-01T00:00:00'): {e}"
        ) from e

    incluir_eventos = bool(args.get("incluir_eventos", True))
    incluir_tarefas = bool(args.get("incluir_tarefas", True))
    somente_pendentes = bool(args.get("somente_tarefas_pendentes", False))

    def _run() -> dict[str, Any]:
        with get_connection() as conn:
            items = list_calendar_items(
                conn,
                start=start,
                end=end,
                include_events=incluir_eventos,
                include_tasks=incluir_tarefas,
                only_pending_tasks=somente_pendentes,
            )
        logger.info(
            f"consultar_calendario [{start.date()} → {end.date()}] -> {len(items)} items"
        )
        return {
            "data_inicio": start.isoformat(),
            "data_fim": end.isoformat(),
            "incluir_eventos": incluir_eventos,
            "incluir_tarefas": incluir_tarefas,
            "count": len(items),
            "items": [
                {
                    "item_uid": it.item_uid,
                    "item_type": it.item_type,
                    "source_id": it.source_id,
                    "title": it.title,
                    "starts_at": it.starts_at.isoformat(),
                    "ends_at": it.ends_at.isoformat() if it.ends_at else None,
                    "category": it.category,
                    "status": it.status,
                    "priority": it.priority,
                    "location": it.location,
                }
                for it in items
            ],
        }

    return await asyncio.to_thread(_run)


def _register() -> None:
    reg = get_registry()
    reg.register(
        ToolDefinition(
            name="consultar_calendario",
            description=(
                "Consulta o calendário do usuário num intervalo de datas. Retorna "
                "eventos E tarefas (com prazo) juntos, ordenados por data. Use quando "
                "a pergunta envolver ambos (ex: 'o que tenho na semana?', 'estou "
                "ocupado dia 10?', 'mostra agenda completa de junho')."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "data_inicio": {
                        "type": "string",
                        "description": "ISO8601 inclusivo, ex: '2026-06-01T00:00:00'",
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "ISO8601 exclusivo, ex: '2026-07-01T00:00:00'",
                    },
                    "incluir_eventos": {"type": "boolean", "default": True},
                    "incluir_tarefas": {"type": "boolean", "default": True},
                    "somente_tarefas_pendentes": {"type": "boolean", "default": False},
                },
                "required": ["data_inicio", "data_fim"],
            },
            handler=_consultar_calendario,
            examples=[
                {
                    "tool": "consultar_calendario",
                    "args": {
                        "data_inicio": "2026-06-01T00:00:00",
                        "data_fim": "2026-07-01T00:00:00",
                    },
                }
            ],
        )
    )


_register()
