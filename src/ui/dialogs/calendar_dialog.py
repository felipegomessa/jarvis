"""Dialog do Calendário unificado (Fase 10).

Layout (referência: Google Calendar):
- Header: ◀ Hoje ▶ + título do mês + [+ Criar]
- Sidebar esquerda: mini-calendário + filtros (eventos/tarefas/kinds)
- Área central: grid mensal 7 colunas por 6 linhas com chips coloridos
"""

from __future__ import annotations

from datetime import date

from loguru import logger
from nicegui import ui

from src.core.db import get_connection
from src.domain.agenda.repo import delete_event, get_event, update_event
from src.domain.calendar_view import CalendarItem
from src.domain.tasks.repo import complete_task, delete_task, get_task, update_task
from src.ui.components.calendar_mini import CalendarMini
from src.ui.components.calendar_month_view import CalendarMonthView
from src.ui.components.calendar_wizard import open_create_wizard
from src.ui.components.date_picker import date_picker_ptbr, format_ptbr, parse


def open_calendar_dialog() -> None:
    with ui.dialog().props("maximized") as dialog, ui.card().classes(
        "w-full h-full"
    ).style("background:#000000; color:#f5f5f5; padding:0"):

        # Header
        with ui.row().classes("items-center w-full px-4 py-3").style(
            "border-bottom:1px solid #1f1f1f; background:#050505"
        ):
            ui.icon("event").classes("text-cyan-400").style("font-size:22px")
            ui.label("Calendário").style("font-size:20px; font-weight:600")
            ui.space()
            ui.button("Fechar", icon="close", on_click=dialog.close).props(
                "flat color=white"
            )

        # Layout 2 colunas
        with ui.row().classes("w-full no-wrap gap-0 px-3 py-3").style(
            "height: calc(100vh - 60px); align-items: stretch"
        ):
            # ----- Sidebar esquerda -----
            with ui.column().classes("gap-3").style(
                "width:240px; min-width:240px; max-width:240px; "
                "padding-right:12px; border-right:1px solid #1f1f1f; overflow-y:auto"
            ):
                # Botão Criar
                ui.button(
                    "+ Criar", icon="add",
                    on_click=lambda: open_create_wizard(
                        on_saved=_refresh_all,
                    ),
                ).classes("w-full").style(
                    "background-color:#fff; color:#000; border-radius:24px; "
                    "height:48px; font-weight:600; text-transform:none; "
                    "box-shadow:0 2px 8px rgba(255,255,255,0.1)"
                )

                # Mini-calendário
                mini = CalendarMini(
                    on_day_click=lambda d: _focus_day(d),
                )
                mini.render()

                ui.separator().classes("my-2").style("background:#1f1f1f")

                # Filtros
                ui.label("FILTROS").style(
                    "font-size:11px; font-weight:600; color:#888; "
                    "letter-spacing:0.5px; padding:0 4px"
                )

                show_events = ui.switch("Eventos", value=True).props("color=cyan-7")
                show_tasks = ui.switch("Tarefas", value=True).props("color=pink-6")
                only_pending = ui.switch("Só pendentes", value=False).props(
                    "color=orange-7"
                )

                ui.label("TIPOS DE EVENTO").style(
                    "font-size:11px; font-weight:600; color:#888; "
                    "letter-spacing:0.5px; padding:6px 4px 0 4px"
                )
                kind_aula = ui.switch("Aula", value=True).props("color=blue-7")
                kind_prova = ui.switch("Prova", value=True).props("color=red-7")
                kind_trab = ui.switch("Trabalho", value=True).props("color=amber-7")
                kind_outro = ui.switch("Outro", value=True).props("color=grey-6")

                def _apply_filters(_=None) -> None:
                    kinds = set()
                    if kind_aula.value:
                        kinds.add("aula")
                    if kind_prova.value:
                        kinds.add("prova")
                    if kind_trab.value:
                        kinds.add("trabalho")
                    if kind_outro.value:
                        kinds.add("outro")
                    month_view.set_filter(
                        events=show_events.value,
                        tasks=show_tasks.value,
                        only_pending_tasks=only_pending.value,
                        kinds=kinds,
                    )

                for sw in (show_events, show_tasks, only_pending,
                           kind_aula, kind_prova, kind_trab, kind_outro):
                    sw.on_value_change(_apply_filters)

            # ----- Área central: grid -----
            with ui.column().classes("flex-1 px-3").style(
                "overflow-y:auto; min-width:0"
            ):
                month_view = CalendarMonthView(
                    on_day_click=lambda d: open_create_wizard(
                        pre_filled_date=d, on_saved=_refresh_all
                    ),
                    on_item_click=lambda it: _open_item_detail(it, _refresh_all),
                )
                month_view.render()

        def _focus_day(d: date) -> None:
            month_view.go_to(d)

        def _refresh_all() -> None:
            month_view.refresh()

    dialog.open()


# ============================================================
# Dialog secundário: detalhe/edição/exclusão de um item
# ============================================================

def _open_item_detail(item: CalendarItem, on_changed) -> None:
    """Abre dialog menor com detalhes editáveis do item clicado."""
    with ui.dialog().props("persistent") as d, ui.card().classes(
        "w-full max-w-xl"
    ).style("background:#0a0a0a; color:#f5f5f5; padding:18px"):
        with ui.row().classes("items-center justify-between w-full"):
            badge = "Evento" if item.item_type == "event" else "Tarefa"
            color = "#1E88E5" if item.item_type == "event" else "#E91E63"
            ui.label(f"{badge}: {item.title}").style(
                f"font-size:18px; font-weight:600; color:{color}"
            )
            ui.button(icon="close", on_click=d.close).props(
                "flat round size=sm color=white"
            )

        if item.item_type == "event":
            _render_event_detail(item, d, on_changed)
        else:
            _render_task_detail(item, d, on_changed)

    d.open()


def _render_event_detail(item: CalendarItem, dialog, on_changed) -> None:
    with get_connection() as conn:
        ev = get_event(conn, item.source_id)
    if ev is None:
        ui.label("Evento não encontrado (talvez foi excluído).").style(
            "color:#ff6b6b"
        )
        ui.button("Fechar", on_click=dialog.close).props("flat")
        return

    title_in = ui.input("Título", value=ev.title).classes("w-full")
    desc_in = ui.textarea("Descrição", value=ev.description or "").classes("w-full")
    with ui.row().classes("w-full gap-2"):
        starts_field = date_picker_ptbr(
            "Início", value=format_ptbr(ev.starts_at), with_time=True
        )
        ends_field = date_picker_ptbr(
            "Fim", value=format_ptbr(ev.ends_at), with_time=True
        )
    with ui.row().classes("w-full gap-2"):
        kind_in = ui.select(
            ["aula", "prova", "trabalho", "outro"], value=ev.kind, label="Tipo",
        ).classes("flex-1")
        location_in = ui.input("Local", value=ev.location or "").classes("flex-1")

    def save() -> None:
        dt_start = parse(starts_field.value, with_time=True)
        if not title_in.value or not dt_start:
            ui.notify("Preencha título e início", type="warning")
            return
        dt_end = parse(ends_field.value, with_time=True) if ends_field.value else None
        try:
            with get_connection() as conn:
                update_event(
                    conn, ev.id,
                    title=title_in.value,
                    description=desc_in.value or None,
                    starts_at=dt_start,
                    ends_at=dt_end,
                    kind=kind_in.value,
                    location=location_in.value or None,
                )
        except Exception as e:
            ui.notify(f"Erro: {e}", type="negative")
            return
        ui.notify("Evento atualizado!", type="positive")
        dialog.close()
        on_changed()

    def remove() -> None:
        try:
            with get_connection() as conn:
                delete_event(conn, ev.id)
        except Exception as e:
            ui.notify(f"Erro: {e}", type="negative")
            return
        ui.notify("Evento excluído", type="info")
        dialog.close()
        on_changed()

    with ui.row().classes("justify-between w-full mt-3"):
        ui.button("Excluir", icon="delete", on_click=remove).props(
            "flat color=negative"
        )
        with ui.row().classes("gap-2"):
            ui.button("Cancelar", on_click=dialog.close).props("flat")
            ui.button("Salvar", icon="save", on_click=save).props("color=primary")


def _render_task_detail(item: CalendarItem, dialog, on_changed) -> None:
    with get_connection() as conn:
        t = get_task(conn, item.source_id)
    if t is None:
        ui.label("Tarefa não encontrada (talvez foi excluída).").style(
            "color:#ff6b6b"
        )
        ui.button("Fechar", on_click=dialog.close).props("flat")
        return

    title_in = ui.input("Título", value=t.title).classes("w-full")
    desc_in = ui.textarea("Descrição", value=t.description or "").classes("w-full")
    with ui.row().classes("w-full gap-2 items-end"):
        due_field = date_picker_ptbr(
            "Prazo", value=format_ptbr(t.due_at), with_time=True
        )
        prio_in = ui.select(
            {0: "Normal", 1: "Alta", 2: "Urgente"}, value=t.priority,
            label="Prioridade",
        ).classes("w-40")

    is_done_label = "✓ Concluída" if t.status == "done" else "Pendente"
    ui.label(f"Status atual: {is_done_label}").style(
        "color:#888; font-size:13px; margin-top:6px"
    )

    def save() -> None:
        dt_due = parse(due_field.value, with_time=True) if due_field.value else None
        try:
            with get_connection() as conn:
                update_task(
                    conn, t.id,
                    title=title_in.value,
                    description=desc_in.value or None,
                    due_at=dt_due,
                    priority=int(prio_in.value),
                )
        except Exception as e:
            ui.notify(f"Erro: {e}", type="negative")
            return
        ui.notify("Tarefa atualizada!", type="positive")
        dialog.close()
        on_changed()

    def toggle_done() -> None:
        try:
            with get_connection() as conn:
                if t.status == "pending":
                    complete_task(conn, t.id)
                    ui.notify("Marcada como concluída!", type="positive")
                else:
                    update_task(conn, t.id, status="pending", completed_at=None)
                    ui.notify("Reaberta como pendente", type="info")
        except Exception as e:
            logger.warning(f"erro ao alternar status: {e}")
        dialog.close()
        on_changed()

    def remove() -> None:
        with get_connection() as conn:
            delete_task(conn, t.id)
        ui.notify("Tarefa excluída", type="info")
        dialog.close()
        on_changed()

    with ui.row().classes("justify-between w-full mt-3"):
        with ui.row().classes("gap-2"):
            ui.button("Excluir", icon="delete", on_click=remove).props(
                "flat color=negative"
            )
            toggle_label = "Reabrir" if t.status == "done" else "Marcar concluída"
            toggle_icon = "undo" if t.status == "done" else "check_circle"
            ui.button(toggle_label, icon=toggle_icon, on_click=toggle_done).props(
                "flat color=positive"
            )
        with ui.row().classes("gap-2"):
            ui.button("Cancelar", on_click=dialog.close).props("flat")
            ui.button("Salvar", icon="save", on_click=save).props("color=primary")
