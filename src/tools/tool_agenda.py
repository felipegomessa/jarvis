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
    delete_event,
    events_this_week,
    events_today,
    events_tomorrow,
    get_event,
    list_all_events,
    next_event,
    update_event,
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


def _resolve_event_id_by_title(conn: Any, titulo: str) -> int:
    """Resolve um título para o id de um evento único.

    Prioriza correspondência exata (sem acento/caixa); cai para 'contém'. Levanta
    ValueError se nada casar ou se houver ambiguidade.
    """
    alvo = _strip_accents(titulo).casefold().strip()
    eventos = list_all_events(conn)

    def _norm(s: str) -> str:
        return _strip_accents(s).casefold().strip()

    exatos = [e for e in eventos if _norm(e.title) == alvo]
    candidatos = exatos or [e for e in eventos if alvo in _norm(e.title)]

    if not candidatos:
        raise ValueError(
            f"nenhum evento corresponde a {titulo!r}. "
            "Use `consultar_agenda` ou `consultar_calendario` para ver os títulos."
        )
    if len(candidatos) > 1:
        opcoes = ", ".join(
            f"id={e.id} ({e.title} em {e.starts_at.isoformat()})" for e in candidatos
        )
        raise ValueError(
            f"mais de um evento corresponde a {titulo!r}: {opcoes}. "
            "Repita informando o `event_id` específico."
        )
    return candidatos[0].id


def _locate_event_id(conn: Any, args: dict[str, Any]) -> int:
    if args.get("event_id") is not None:
        return int(args["event_id"])
    if args.get("titulo"):
        return _resolve_event_id_by_title(conn, str(args["titulo"]))
    raise ValueError("informe `event_id` ou `titulo` do evento")


async def _editar_evento(args: dict[str, Any]) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        # Campos editáveis vindos do chat → patch para update_event.
        patch: dict[str, Any] = {}
        if args.get("novo_titulo"):
            patch["title"] = str(args["novo_titulo"])
        if "description" in args:
            patch["description"] = args["description"]
        if "location" in args:
            patch["location"] = args["location"]
        if args.get("kind"):
            patch["kind"] = args["kind"]
        for campo in ("starts_at", "ends_at"):
            if args.get(campo):
                try:
                    patch[campo] = datetime.fromisoformat(args[campo])
                except ValueError as e:
                    raise ValueError(f"{campo} deve ser ISO8601: {e}") from e

        if not patch:
            raise ValueError(
                "nada para editar: informe ao menos um campo "
                "(novo_titulo, starts_at, ends_at, kind, location, description)"
            )

        with get_connection() as conn:
            event_id = _locate_event_id(conn, args)
            if get_event(conn, event_id) is None:
                raise ValueError(f"evento não encontrado: id={event_id}")
            ev = update_event(conn, event_id, **patch)
            assert ev is not None
            logger.info(f"evento editado via tool: id={ev.id}, campos={list(patch)}")
        return _event_to_dict(ev)

    return await asyncio.to_thread(_run)


async def _remover_evento(args: dict[str, Any]) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        with get_connection() as conn:
            event_id = _locate_event_id(conn, args)
            ev = get_event(conn, event_id)
            if ev is None:
                raise ValueError(f"evento não encontrado: id={event_id}")
            removido = _event_to_dict(ev)
            delete_event(conn, event_id)
            logger.info(f"evento removido via tool: id={event_id}")
        return {"removed": True, "event": removido}

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
    reg.register(
        ToolDefinition(
            name="editar_evento",
            description=(
                "Edita um evento existente da agenda. Localize o evento por "
                "`event_id` OU `titulo` e informe os campos a alterar (novo_titulo, "
                "starts_at, ends_at, kind, location, description). Use quando o "
                "usuário pedir para remarcar, mudar horário/local ou renomear um "
                "compromisso. Datas em ISO8601."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "ID do evento."},
                    "titulo": {
                        "type": "string",
                        "description": "Título (ou parte) do evento. Alternativa ao event_id.",
                    },
                    "novo_titulo": {"type": "string", "description": "Novo título."},
                    "starts_at": {"type": "string", "description": "Novo início ISO8601."},
                    "ends_at": {"type": "string", "description": "Novo fim ISO8601."},
                    "kind": {
                        "type": "string",
                        "enum": ["aula", "prova", "trabalho", "outro"],
                    },
                    "location": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
            handler=_editar_evento,
            examples=[
                {
                    "tool": "editar_evento",
                    "args": {
                        "titulo": "Prova de Cálculo",
                        "starts_at": "2026-06-11T14:00:00",
                        "location": "Sala 20",
                    },
                },
                {
                    "tool": "editar_evento",
                    "args": {"event_id": 5, "novo_titulo": "Prova de Cálculo II"},
                },
            ],
        )
    )
    reg.register(
        ToolDefinition(
            name="remover_evento",
            description=(
                "Remove (cancela) um evento da agenda. Localize por `event_id` OU "
                "`titulo`. Use quando o usuário pedir para cancelar/apagar um "
                "compromisso. Se o título casar com mais de um evento, o erro lista "
                "os candidatos para o usuário escolher o id."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "ID do evento."},
                    "titulo": {
                        "type": "string",
                        "description": "Título (ou parte) do evento. Alternativa ao event_id.",
                    },
                },
            },
            handler=_remover_evento,
            examples=[
                {"tool": "remover_evento", "args": {"event_id": 5}},
                {"tool": "remover_evento", "args": {"titulo": "Aula de Estatística"}},
            ],
        )
    )


_register()
