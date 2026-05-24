"""Tools de agenda (consultar_agenda, adicionar_evento)."""

from __future__ import annotations

import asyncio
import unicodedata
from datetime import datetime
from typing import Any

from loguru import logger

from src.core.db import get_connection
from src.domain.agenda import (
    EventCreate,
    create_event,
    events_this_week,
    events_today,
    events_tomorrow,
    next_event,
)
from src.tools.registry import ToolDefinition, get_registry


def _event_to_dict(e: Any) -> dict[str, Any]:
    return {
        "id": e.id,
        "title": e.title,
        "description": e.description,
        "starts_at": e.starts_at.isoformat(),
        "ends_at": e.ends_at.isoformat() if e.ends_at else None,
        "kind": e.kind,
        "location": e.location,
    }


def _strip_accents(s: str) -> str:
    """Remove acentos para comparação tolerante de enum vindo da LLM."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


async def _consultar_agenda(args: dict[str, Any]) -> dict[str, Any]:
    periodo_raw = (args.get("periodo") or "hoje").lower().strip()
    # Aceita tanto "amanha" quanto "amanhã" (LLM pode mandar qualquer um)
    periodo = _strip_accents(periodo_raw)
    kind = args.get("kind")

    def _run() -> dict[str, Any]:
        with get_connection() as conn:
            if periodo == "hoje":
                evs = events_today(conn, kind=kind)
            elif periodo == "amanha":
                evs = events_tomorrow(conn, kind=kind)
            elif periodo == "semana":
                evs = events_this_week(conn, kind=kind)
            elif periodo == "agora":
                nxt = next_event(conn)
                evs = [nxt] if nxt else []
            else:
                raise ValueError(
                    f"período inválido: {periodo_raw!r}. "
                    "Use 'hoje', 'amanhã', 'semana' ou 'agora'."
                )
        return {
            "periodo": periodo_raw,
            "kind_filter": kind,
            "count": len(evs),
            "events": [_event_to_dict(e) for e in evs],
        }

    return await asyncio.to_thread(_run)


async def _adicionar_evento(args: dict[str, Any]) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        try:
            starts_at = datetime.fromisoformat(args["starts_at"])
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"starts_at deve ser ISO8601 (ex: '2026-06-01T10:00:00'): {e}"
            ) from e
        ends_at = None
        if args.get("ends_at"):
            try:
                ends_at = datetime.fromisoformat(args["ends_at"])
            except ValueError as e:
                raise ValueError(f"ends_at inválido: {e}") from e

        ec = EventCreate(
            title=args["title"],
            description=args.get("description"),
            starts_at=starts_at,
            ends_at=ends_at,
            kind=args.get("kind", "outro"),
            location=args.get("location"),
        )
        with get_connection() as conn:
            ev = create_event(conn, ec)
            logger.info(f"evento criado via tool: id={ev.id}, title={ev.title}")
        return _event_to_dict(ev)

    return await asyncio.to_thread(_run)


def _register() -> None:
    reg = get_registry()
    reg.register(
        ToolDefinition(
            name="consultar_agenda",
            description=(
                "Consulta eventos da agenda acadêmica (aulas, provas, trabalhos). "
                "Use sempre que o usuário perguntar sobre o que ele tem hoje/amanhã/"
                "esta semana, ou sobre o próximo evento."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "periodo": {
                        "type": "string",
                        "enum": ["hoje", "amanhã", "semana", "agora"],
                        "description": "Janela temporal.",
                    },
                    "kind": {
                        "type": "string",
                        "enum": ["aula", "prova", "trabalho", "outro"],
                        "description": "Opcional. Filtra por tipo de evento.",
                    },
                },
                "required": ["periodo"],
            },
            handler=_consultar_agenda,
            examples=[
                {"tool": "consultar_agenda", "args": {"periodo": "hoje"}},
                {"tool": "consultar_agenda", "args": {"periodo": "amanhã", "kind": "prova"}},
            ],
        )
    )
    reg.register(
        ToolDefinition(
            name="adicionar_evento",
            description=(
                "Adiciona um novo evento na agenda. Use para criar aulas, provas, "
                "trabalhos ou outros compromissos com horário fixo. Datas em ISO8601."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "starts_at": {
                        "type": "string",
                        "description": "ISO8601, ex: '2026-06-01T10:00:00'",
                    },
                    "ends_at": {"type": "string", "description": "ISO8601 opcional"},
                    "kind": {
                        "type": "string",
                        "enum": ["aula", "prova", "trabalho", "outro"],
                    },
                    "location": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["title", "starts_at"],
            },
            handler=_adicionar_evento,
            examples=[
                {
                    "tool": "adicionar_evento",
                    "args": {
                        "title": "Prova de Cálculo",
                        "starts_at": "2026-06-10T14:00:00",
                        "kind": "prova",
                        "location": "Sala 12",
                    },
                }
            ],
        )
    )


_register()
