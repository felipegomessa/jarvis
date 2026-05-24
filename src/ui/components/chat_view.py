"""Área central de chat: título, scroll, pill input — Fase 5."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

from loguru import logger
from nicegui import ui

from src.core.db import get_connection
from src.domain.chat.repo import (
    add_message,
    list_messages_of_session,
    next_position,
)
from src.domain.chat.service import start_session_with_first_message
from src.ui.components.greeting import get_greeting
from src.ui.components.prompt_input import PromptInput
from src.ui.components.tool_call_card import render_tool_call_chip
from src.ui.state import get_state, notify_sessions_changed


class ChatView:
    """Encapsula o estado de render do chat (título, mensagens, input)."""

    def __init__(self) -> None:
        self._title_label = None
        self._messages_area = None
        self._suggestions_row = None
        self._prompt: PromptInput | None = None

    def render(
        self,
        dialog_openers: dict[str, tuple[str, Any]],
    ) -> None:
        """Renderiza o chat completo dentro de uma coluna centralizada.

        dialog_openers: dict{label: (icon_name, callable_to_open_dialog)}
        """
        with ui.column().classes(
            "items-center w-full"
        ).style("max-width:800px; margin:0 auto; padding-top:80px"):

            self._title_label = ui.label(get_greeting(get_state().user_name)).style(
                "font-size:28px; font-weight:500; color:#F5F5F5; "
                "text-align:center; margin-bottom:48px"
            )

            # Área de mensagens
            self._messages_area = ui.column().classes(
                "w-full gap-3"
            ).style("min-height:50px; margin-bottom:24px")

            # Input pill com menu "+"
            self._prompt = PromptInput(on_submit=self._handle_send)
            for label, (icon, opener) in dialog_openers.items():
                self._prompt.register_dialog(label, icon, opener)
            self._prompt.render()

            # Botões de sugestão
            self._suggestions_row = ui.row().classes(
                "gap-2 mt-3 justify-center w-full flex-wrap"
            )
            with self._suggestions_row:
                for label_text, icon, sample in [
                    ("Resumir um material", "description", "Resuma o material mais recente"),
                    ("Tarefas pendentes", "task_alt", "Quais minhas tarefas pendentes?"),
                    ("Próximas aulas", "school", "O que tenho esta semana?"),
                ]:
                    ui.button(
                        label_text,
                        icon=icon,
                        on_click=lambda s=sample: self._prompt.set_value(s) if self._prompt else None,
                    ).props("outline rounded dense").style(
                        "color:#fff; border-color:#2F2F2F; "
                        "height:40px; padding:0 18px; text-transform:none"
                    )

    async def _handle_send(self, text: str) -> None:
        state = get_state()
        if not state.online or not state.agent:
            ui.notify(
                "LLM offline — chat indisponível. Verifique o token em .env.",
                type="warning",
            )
            return

        # Esconde o título central + sugestões assim que a 1ª pergunta chega
        if self._title_label is not None:
            self._title_label.visible = False
        if self._suggestions_row is not None:
            self._suggestions_row.visible = False

        # Garante a sessão (cria com 1ª user msg)
        if state.current_session_id is None:
            with get_connection() as conn:
                state.current_session_id = start_session_with_first_message(conn, text)
            notify_sessions_changed()  # refresh sidebar
        else:
            with get_connection() as conn:
                add_message(
                    conn,
                    state.current_session_id,
                    role="user",
                    content=text,
                    position=next_position(conn, state.current_session_id),
                )

        if self._messages_area is None:
            return

        # Mensagem do usuário
        with self._messages_area:
            with ui.row().classes("w-full justify-end"):
                ui.chat_message(text=text, sent=True, name="Você").classes(
                    "max-w-3xl"
                )

        # Container da resposta
        with self._messages_area:
            response_container = ui.card().classes(
                "w-full max-w-3xl self-start bg-transparent"
            ).style("border:none; box-shadow:none; padding:8px 0")

        await self._stream_response(text, response_container)
        notify_sessions_changed()  # updated_at mudou; reorder na sidebar

        # Scroll para o fim
        with contextlib.suppress(Exception):
            ui.run_javascript(
                "window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})"
            )

    async def _stream_response(self, user_text: str, response_container) -> None:
        state = get_state()
        assert state.agent is not None

        pending_tool: dict | None = None
        tool_events: list[tuple[dict, dict]] = []
        response_md: ui.markdown | None = None
        accumulated_reply = ""

        with response_container:
            ui.label("JARVIS").style(
                "color:#19C37D; font-size:12px; font-weight:600; "
                "letter-spacing:0.5px; margin-bottom:4px"
            )

        try:
            async for event in state.agent.respond(
                user_text, session_id=state.current_session_id
            ):
                t = event.get("type")
                with response_container:
                    if t == "tool_call":
                        pending_tool = event
                    elif t == "tool_result":
                        tool_events.append((pending_tool or {}, event))
                        pending_tool = None
                    elif t == "final":
                        accumulated_reply = event.get("reply", "")
                        if response_md is None:
                            response_md = ui.markdown(accumulated_reply).classes(
                                "jarvis-md-chat"
                            ).style("color:#f5f5f5; font-size:15px; line-height:1.6")
                        else:
                            response_md.content = accumulated_reply
                    elif t == "error":
                        ui.label(f"⚠ {event.get('message', '')}").style(
                            "color:#ff6b6b; font-size:13px"
                        )
                await asyncio.sleep(0)
        except Exception as e:
            logger.exception("erro no agent loop")
            with response_container:
                ui.label(f"[ERRO] {type(e).__name__}: {e}").style("color:#ff6b6b")

        # Após a resposta final, renderiza chips de tool calls abaixo (não somem
        # ao fechar — cada chip abre seu próprio dialog modal com Entrada/Saída).
        if tool_events:
            with response_container, ui.row().classes(
                "gap-2 flex-wrap mt-2"
            ):
                for call_evt, result_evt in tool_events:
                    render_tool_call_chip(call_evt, result_evt)

    def reset(self) -> None:
        """Limpa o chat (chamado por 'Novo chat')."""
        if self._messages_area is not None:
            self._messages_area.clear()
        if self._title_label is not None:
            self._title_label.set_text(get_greeting(get_state().user_name))
            self._title_label.visible = True
        if self._suggestions_row is not None:
            self._suggestions_row.visible = True

    def load_session(self, session_id: int) -> None:
        """Restaura uma sessão antiga na área de mensagens."""
        state = get_state()
        state.current_session_id = session_id

        if self._messages_area is None:
            return

        self._messages_area.clear()
        if self._title_label is not None:
            self._title_label.visible = False
        if self._suggestions_row is not None:
            self._suggestions_row.visible = False

        with get_connection() as conn:
            msgs = list_messages_of_session(conn, session_id)

        def _tool_msg_to_pair(m) -> tuple[dict, dict]:
            meta = m.metadata or {}
            try:
                output = json.loads(m.content) if m.content else None
            except json.JSONDecodeError:
                output = m.content
            call_evt = {"tool": meta.get("tool", "?"), "args": meta.get("args", {})}
            result_evt = {
                "status": meta.get("status", "ok"),
                "duration_ms": meta.get("duration_ms", 0),
                "output": output,
            }
            return call_evt, result_evt

        # Buffer de tool messages até encontrar próximo assistant/user — assim
        # podemos renderizar os chips logo abaixo da resposta correspondente.
        pending_tools: list[tuple[dict, dict]] = []

        def _flush_pending_chips() -> None:
            if not pending_tools or self._messages_area is None:
                return
            with self._messages_area, ui.row().classes(
                "w-full max-w-3xl gap-2 flex-wrap self-start"
            ):
                for call_evt, result_evt in pending_tools:
                    render_tool_call_chip(call_evt, result_evt)
            pending_tools.clear()

        for m in msgs:
            if m.role == "tool":
                pending_tools.append(_tool_msg_to_pair(m))
                continue
            _flush_pending_chips()
            with self._messages_area:
                if m.role == "user":
                    with ui.row().classes("w-full justify-end"):
                        ui.chat_message(text=m.content, sent=True, name="Você").classes(
                            "max-w-3xl"
                        )
                elif m.role == "assistant":
                    with ui.card().classes(
                        "w-full max-w-3xl self-start bg-transparent"
                    ).style("border:none; box-shadow:none; padding:8px 0"):
                        ui.label("JARVIS").style(
                            "color:#19C37D; font-size:12px; font-weight:600; "
                            "letter-spacing:0.5px; margin-bottom:4px"
                        )
                        ui.markdown(m.content).classes("jarvis-md-chat").style(
                            "color:#f5f5f5; font-size:15px; line-height:1.6"
                        )
        _flush_pending_chips()

        ui.notify(f"Conversa restaurada ({len(msgs)} mensagens)", type="info")
