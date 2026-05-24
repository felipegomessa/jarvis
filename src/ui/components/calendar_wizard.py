"""Wizard 'Evento vs Tarefa' para o calendário — Fase 10.

Passo 1: usuário escolhe entre EVENTO ou TAREFA com texto didático.
Passo 2: form específico do tipo escolhido. Salva no DB e fecha.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from loguru import logger
from nicegui import ui

from src.core.db import get_connection
from src.domain.agenda import EventCreate, create_event
from src.domain.tasks.models import TaskCreate
from src.domain.tasks.repo import create_task
from src.ui.components.date_picker import date_picker_ptbr, parse


def open_create_wizard(
    pre_filled_date: date | None = None,
    on_saved: Callable[[], None] | None = None,
) -> None:
    """Abre o wizard de criação. Se on_saved for fornecido, é chamado pós-save."""
    with ui.dialog().props("persistent") as dialog, ui.card().classes(
        "w-full max-w-2xl"
    ).style("background:#0a0a0a; color:#f5f5f5; padding:20px"):
        step1_box = ui.column().classes("w-full gap-4")
        step2_box = ui.column().classes("w-full gap-3")
        step2_box.visible = False

        def _close():
            dialog.close()

        with step1_box:
            with ui.row().classes("items-center justify-between w-full"):
                ui.label("Adicionar ao calendário").style(
                    "font-size:20px; font-weight:600"
                )
                ui.button(icon="close", on_click=_close).props(
                    "flat round size=sm color=white"
                )
            ui.label("Que tipo de item você quer adicionar?").style(
                "color:#bbb; margin-bottom:12px"
            )

            with ui.row().classes("w-full gap-4 no-wrap"):
                with ui.element("div").classes("flex-1 jarvis-wizard-card").on(
                    "click", lambda _e=None: _go_step2("event")
                ):
                    ui.icon("event").style("font-size:36px; color:#1E88E5")
                    ui.label("EVENTO").style(
                        "font-weight:700; color:#1E88E5; "
                        "margin-top:8px; font-size:16px"
                    )
                    ui.label(
                        "Algo que VAI ACONTECER em horário fixo: "
                        "aula, prova, reunião, palestra."
                    ).style("color:#ccc; font-size:13px; margin-top:6px")

                with ui.element("div").classes("flex-1 jarvis-wizard-card").on(
                    "click", lambda _e=None: _go_step2("task")
                ):
                    ui.icon("check_circle").style("font-size:36px; color:#E91E63")
                    ui.label("TAREFA").style(
                        "font-weight:700; color:#E91E63; "
                        "margin-top:8px; font-size:16px"
                    )
                    ui.label(
                        "Algo que VOCÊ PRECISA FAZER até um prazo: "
                        "estudar, escrever, entregar trabalho."
                    ).style("color:#ccc; font-size:13px; margin-top:6px")

            with ui.row().classes("justify-end w-full mt-3"):
                ui.button("Cancelar", on_click=_close).props("flat color=grey-5")

        def _go_step2(item_type: str) -> None:
            step1_box.visible = False
            step2_box.visible = True
            step2_box.clear()
            with step2_box:
                if item_type == "event":
                    _render_event_form(pre_filled_date, dialog, on_saved, _back_to_step1)
                else:
                    _render_task_form(pre_filled_date, dialog, on_saved, _back_to_step1)

        def _back_to_step1() -> None:
            step2_box.visible = False
            step1_box.visible = True

    dialog.open()


def _render_event_form(
    pre_date: date | None, dialog, on_saved, on_back
) -> None:
    ui.label("Novo evento").style("font-size:18px; font-weight:600")
    ui.label(
        "Um evento ocupa um momento da sua agenda. Tipos: aula, prova, "
        "trabalho, outro."
    ).style("color:#999; font-size:12px; margin-bottom:8px")

    title_in = ui.input("Título*").classes("w-full")
    desc_in = ui.textarea("Descrição").classes("w-full")
    with ui.row().classes("w-full gap-2"):
        starts_field = date_picker_ptbr("Início*", with_time=True)
        ends_field = date_picker_ptbr("Fim (opcional)", with_time=True)
    if pre_date:
        starts_field.value = pre_date.strftime("%d/%m/%Y 10:00")

    with ui.row().classes("w-full gap-2"):
        kind_in = ui.select(
            ["aula", "prova", "trabalho", "outro"], value="outro", label="Tipo"
        ).classes("flex-1")
        location_in = ui.input("Local").classes("flex-1")

    def save() -> None:
        dt_start = parse(starts_field.value, with_time=True)
        if not title_in.value or not dt_start:
            ui.notify("Preencha título e início", type="warning")
            return
        dt_end = parse(ends_field.value, with_time=True) if ends_field.value else None
        if dt_end and dt_end < dt_start:
            ui.notify("Fim não pode ser antes do início", type="warning")
            return
        try:
            with get_connection() as conn:
                ev = create_event(
                    conn,
                    EventCreate(
                        title=title_in.value,
                        description=desc_in.value or None,
                        starts_at=dt_start,
                        ends_at=dt_end,
                        kind=kind_in.value,
                        location=location_in.value or None,
                    ),
                )
                logger.info(f"evento criado via wizard: {ev.id}")
        except Exception as e:
            ui.notify(f"Erro ao salvar: {e}", type="negative")
            return
        ui.notify("Evento criado!", type="positive")
        dialog.close()
        if on_saved:
            on_saved()

    with ui.row().classes("justify-between w-full mt-3"):
        ui.button("← Voltar", on_click=on_back).props("flat color=grey-5")
        with ui.row().classes("gap-2"):
            ui.button("Cancelar", on_click=dialog.close).props("flat color=grey-5")
            ui.button("Salvar evento", icon="save", on_click=save).props(
                "color=primary"
            )


def _render_task_form(
    pre_date: date | None, dialog, on_saved, on_back
) -> None:
    ui.label("Nova tarefa").style("font-size:18px; font-weight:600")
    ui.label(
        "Uma tarefa é algo que você precisa fazer (tem prazo opcional + "
        "prioridade). Pode ser marcada como concluída."
    ).style("color:#999; font-size:12px; margin-bottom:8px")

    title_in = ui.input("Título*").classes("w-full")
    desc_in = ui.textarea("Descrição").classes("w-full")

    with ui.row().classes("w-full gap-2"):
        due_field = date_picker_ptbr("Prazo (opcional)", with_time=True)
        prio_in = ui.select(
            {0: "Normal", 1: "Alta", 2: "Urgente"}, value=0, label="Prioridade"
        ).classes("w-40")
    if pre_date:
        due_field.value = pre_date.strftime("%d/%m/%Y 23:59")

    def save() -> None:
        if not title_in.value:
            ui.notify("Preencha o título", type="warning")
            return
        dt_due = parse(due_field.value, with_time=True) if due_field.value else None
        try:
            with get_connection() as conn:
                t = create_task(
                    conn,
                    TaskCreate(
                        title=title_in.value,
                        description=desc_in.value or None,
                        due_at=dt_due,
                        priority=int(prio_in.value),
                    ),
                )
                logger.info(f"tarefa criada via wizard: {t.id}")
        except Exception as e:
            ui.notify(f"Erro ao salvar: {e}", type="negative")
            return
        ui.notify("Tarefa criada!", type="positive")
        dialog.close()
        if on_saved:
            on_saved()

    with ui.row().classes("justify-between w-full mt-3"):
        ui.button("← Voltar", on_click=on_back).props("flat color=grey-5")
        with ui.row().classes("gap-2"):
            ui.button("Cancelar", on_click=dialog.close).props("flat color=grey-5")
            ui.button("Salvar tarefa", icon="save", on_click=save).props(
                "color=primary"
            )
