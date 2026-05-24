"""Dialog modal: lista pura de tarefas (modo to-do) — Fase 6."""

from __future__ import annotations

from nicegui import ui

from src.core.db import get_connection
from src.domain.tasks import (
    TaskCreate,
    complete_task,
    create_task,
    delete_task,
    list_tasks,
    overdue_tasks,
)
from src.ui.components.date_picker import date_picker_ptbr, parse

_PRIORITY_LABELS = {0: "Normal", 1: "Alta", 2: "Urgente"}
_PRIORITY_COLORS = {0: "grey", 1: "amber", 2: "red"}


def open_tasks_list_dialog() -> None:
    with ui.dialog().props("persistent") as dialog, ui.card().classes(
        "w-full max-w-3xl"
    ).style("background:#0a0a0a; color:#f5f5f5"):
        with ui.row().classes("items-center justify-between w-full px-2"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("checklist").classes("text-cyan-400")
                ui.label("Lista de Tarefas").style("font-size:20px; font-weight:600")
            ui.button(icon="close", on_click=dialog.close).props(
                "flat round size=sm color=white"
            )

        list_container = ui.column().classes("w-full gap-2 px-2").style(
            "max-height:50vh; overflow-y:auto"
        )

        def refresh() -> None:
            list_container.clear()
            with get_connection() as conn:
                pending = list_tasks(conn, status="pending")
                done = list_tasks(conn, status="done", limit=20)
                overdue = overdue_tasks(conn)
            overdue_ids = {t.id for t in overdue}

            with list_container:
                ui.label(f"Pendentes ({len(pending)})").style(
                    "font-size:16px; font-weight:600; padding-top:8px"
                )
                if not pending:
                    ui.label("(nenhuma)").style(
                        "color:#666; font-style:italic; font-size:13px"
                    )
                for t in pending:
                    _render_task(t, t.id in overdue_ids, refresh)

                ui.label(f"Concluídas ({len(done)})").style(
                    "font-size:16px; font-weight:600; padding-top:16px"
                )
                if not done:
                    ui.label("(nenhuma)").style(
                        "color:#666; font-style:italic; font-size:13px"
                    )
                for t in done:
                    _render_task(t, False, refresh)

        def _render_task(t, is_overdue: bool, refresh_cb) -> None:
            bg = "background:#3a1a1a" if is_overdue else "background:#1a1a1a"
            with ui.row().classes("items-center gap-3 w-full p-2 rounded").style(bg):
                if t.status == "pending":
                    def on_check(_e=None, tid=t.id) -> None:
                        with get_connection() as conn:
                            complete_task(conn, tid)
                        refresh_cb()

                    ui.checkbox(value=False, on_change=on_check)
                else:
                    ui.checkbox(value=True).disable()

                with ui.column().classes("flex-1 gap-0"):
                    title_style = "font-weight:600; color:#f5f5f5"
                    if t.status == "done":
                        title_style += "; text-decoration:line-through; opacity:0.6"
                    ui.label(t.title).style(title_style)
                    parts: list[str] = []
                    if t.due_at:
                        prazo = f"prazo: {t.due_at:%d/%m/%Y %H:%M}"
                        if is_overdue:
                            prazo += " (ATRASADA)"
                        parts.append(prazo)
                    if t.description:
                        parts.append(t.description[:80])
                    if parts:
                        ui.label(" | ".join(parts)).style(
                            "color:#888; font-size:11px"
                        )

                ui.badge(_PRIORITY_LABELS[t.priority], color=_PRIORITY_COLORS[t.priority])

                def on_delete(_e=None, tid=t.id) -> None:
                    with get_connection() as conn:
                        delete_task(conn, tid)
                    refresh_cb()

                ui.button(icon="delete_outline", on_click=on_delete).props(
                    "flat dense round size=xs color=grey-7"
                )

        # Form de adição
        with ui.expansion("+ Adicionar tarefa", icon="add").classes("w-full"):
            with ui.column().classes("w-full gap-2 px-2"):
                title_in = ui.input("Título*").classes("w-full")
                desc_in = ui.textarea("Descrição").classes("w-full")
                with ui.row().classes("w-full gap-2 items-end"):
                    due_field = date_picker_ptbr("Prazo (opcional)", with_time=True)
                    prio_in = ui.select(
                        {0: "Normal", 1: "Alta", 2: "Urgente"},
                        value=0, label="Prioridade",
                    ).classes("w-40")

                def on_add() -> None:
                    if not title_in.value:
                        ui.notify("Preencha o título", type="warning")
                        return
                    due_at = parse(due_field.value, with_time=True) if due_field.value else None
                    with get_connection() as conn:
                        create_task(
                            conn,
                            TaskCreate(
                                title=title_in.value,
                                description=desc_in.value or None,
                                due_at=due_at,
                                priority=int(prio_in.value),
                            ),
                        )
                    ui.notify("Tarefa adicionada!", type="positive")
                    title_in.value = ""
                    desc_in.value = ""
                    due_field.value = ""
                    refresh()

                ui.button("Salvar", icon="save", on_click=on_add).props("color=primary")

        refresh()

    dialog.open()
