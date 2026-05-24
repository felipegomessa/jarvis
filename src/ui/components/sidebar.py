"""Sidebar lateral estilo ChatGPT — modos expandida (260px) e mini (60px)."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from src.core.db import get_connection
from src.domain.chat.repo import delete_session, list_recent_sessions
from src.ui.state import (
    get_state,
    register_sessions_changed,
    register_sidebar_toggled,
    reset_session,
    toggle_sidebar,
)


def render_sidebar(
    drawer,
    on_new_chat: Callable[[], None] | None = None,
    on_load_session: Callable[[int], None] | None = None,
) -> None:
    """Renderiza a sidebar dentro de um ui.left_drawer (chame entre seus 'with')."""
    state = get_state()

    def _apply_mode(collapsed: bool) -> None:
        if collapsed:
            drawer.props(add="mini")
        else:
            drawer.props(remove="mini")

    def _do_toggle() -> None:
        new_state = toggle_sidebar()
        _apply_mode(new_state)

    register_sidebar_toggled(_apply_mode)

    with ui.column().classes("h-full w-full px-2 py-3 gap-2"):
        # ---------------- Topo: logo + toggle ----------------
        # Modo expandido: logo grande + botão toggle à direita (alto contraste)
        with ui.row().classes(
            "items-center justify-between w-full jarvis-full-only"
        ):
            ui.image("/img/jarvis-logo-completo.png").style(
                "max-width:140px; height:auto"
            )
            with ui.button(icon="chevron_left", on_click=_do_toggle).props(
                "round size=sm"
            ).style(
                "background-color:#2B2B2B; color:#fff"
            ):
                ui.tooltip("Recolher menu").style(
                    "background:#1a1a1a; color:#ddd; font-size:11px"
                )
        # Modo mini: logo pequeno + toggle abaixo (centralizados)
        with ui.column().classes(
            "items-center w-full gap-2 jarvis-mini-only"
        ):
            ui.image("/img/jarvis-logo-menor.png").style(
                "max-width:32px; height:auto"
            )
            with ui.button(icon="chevron_right", on_click=_do_toggle).props(
                "round size=sm"
            ).style(
                "background-color:#2B2B2B; color:#fff"
            ):
                ui.tooltip("Expandir menu").style(
                    "background:#1a1a1a; color:#ddd; font-size:11px"
                )

        # ---------------- Botão "Novo chat" ----------------
        def _new_chat() -> None:
            reset_session()
            if on_new_chat:
                on_new_chat()

        # Variante full: botão com texto
        with ui.button(on_click=_new_chat).classes(
            "w-full jarvis-full-only"
        ).style(
            "background-color:#2B2B2B; color:#fff; border-radius:10px; "
            "height:40px; margin-top:8px; justify-content:flex-start; "
            "padding: 0 12px; text-transform: none;"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("edit_note").style("font-size:18px")
                ui.label("Novo chat").style("font-weight:500; font-size:14px")
        # Variante mini: botão só com ícone centralizado
        with ui.row().classes("w-full justify-center jarvis-mini-only").style(
            "margin-top:8px"
        ):
            with ui.button(icon="edit_note", on_click=_new_chat).props(
                "round"
            ).style("background-color:#2B2B2B; color:#fff"):
                ui.tooltip("Novo chat").style(
                    "background:#1a1a1a; color:#ddd; font-size:11px"
                )

        # ---------------- "Recentes" (apenas em modo expandido) ----------------
        # Toda a seção é jarvis-full-only — em mini, simplesmente some.
        with ui.column().classes("w-full gap-0 jarvis-full-only"):
            ui.separator().style(
                "background-color:#1f1f1f; margin:12px 0 6px 0"
            )
            ui.label("RECENTES").style(
                "font-size:11px; font-weight:600; color:#888; "
                "padding:4px 4px; letter-spacing:0.5px"
            )
            recents_container = ui.column().classes(
                "w-full jarvis-recent gap-0"
            ).style("max-height: 50vh; overflow-y: auto")

        def _click_session(session_id: int) -> None:
            if on_load_session:
                on_load_session(session_id)

        def _delete_and_refresh(session_id: int) -> None:
            with get_connection() as conn:
                delete_session(conn, session_id)
            if state.current_session_id == session_id:
                reset_session()
                if on_new_chat:
                    on_new_chat()
            refresh_recents()
            ui.notify("Conversa removida", type="info")

        def refresh_recents() -> None:
            recents_container.clear()
            with get_connection() as conn:
                sessions = list_recent_sessions(conn, limit=30)
            with recents_container:
                if not sessions:
                    ui.label("(nenhuma conversa ainda)").style(
                        "color:#666; font-style:italic; font-size:12px; padding:6px"
                    )
                    return
                for s in sessions:
                    is_current = state.current_session_id == s.id
                    bg_style = "background-color:#1a1a1a" if is_current else ""
                    with ui.row().classes(
                        "items-center justify-between w-full"
                    ).style(bg_style + "; border-radius:6px"):
                        with ui.item(
                            on_click=lambda sid=s.id: _click_session(sid)
                        ).props("clickable dense").classes("flex-1 min-w-0"):
                            ui.label(s.title)
                        ui.button(
                            icon="delete_outline",
                            on_click=lambda sid=s.id: _delete_and_refresh(sid),
                        ).props("flat dense size=xs round color=grey-7")

        register_sessions_changed(refresh_recents)
        refresh_recents()

        ui.space()

        ui.separator().style(
            "background-color:#1f1f1f; margin-bottom:8px"
        )

        # ---------------- Rodapé: UFMS | FACOM (sempre visível) ----------------
        # Em modo expandido: ícone school + "UFMS | FACOM" lado a lado.
        # Em modo mini: apenas o ícone (com tooltip).
        with ui.row().classes("items-center justify-center w-full gap-2 p-2"):
            ui.icon("school").style("font-size:20px; color:#888")
            ui.label("UFMS | FACOM").classes("jarvis-full-only").style(
                "color:#888; font-size:12px; font-weight:500; letter-spacing:0.5px"
            )
            with ui.element("div").classes("jarvis-mini-only").style(
                "position:absolute; pointer-events:none"
            ):
                ui.tooltip("UFMS | FACOM").style(
                    "background:#1a1a1a; color:#ddd; font-size:11px"
                )

    # Aplica o modo atual após renderizar (mantém estado consistente após reload)
    _apply_mode(state.sidebar_collapsed)
