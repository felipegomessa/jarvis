"""Date picker PT-BR (dd/mm/aaaa) reutilizável — Fase 7."""

from __future__ import annotations

from datetime import datetime

from nicegui import ui


def date_picker_ptbr(label: str, value: str = "", with_time: bool = True):
    """Input com calendário Quasar em PT-BR, formato dd/mm/aaaa[ HH:mm].

    O locale Quasar é aplicado globalmente pelo `apply_theme()` (Fase 1).

    Returns: `ui.input` cuja `.value` é uma string PT-BR. Use `parse()` para
             converter para `datetime`.
    """
    mask = "DD/MM/YYYY HH:mm" if with_time else "DD/MM/YYYY"
    placeholder = "dd/mm/aaaa hh:mm" if with_time else "dd/mm/aaaa"
    field_mask = "##/##/#### ##:##" if with_time else "##/##/####"

    field = ui.input(label, placeholder=placeholder).props(f'mask="{field_mask}"')
    field.value = value

    with ui.menu().props("no-parent-event") as menu:
        with ui.column().classes("gap-0").style("background:#1a1a1a"):
            ui.date(mask=mask).bind_value(field)
            if with_time:
                ui.time(mask=mask).bind_value(field)
            with ui.row().classes("justify-end w-full p-2"):
                ui.button("OK", on_click=menu.close).props("flat color=primary")

    with field.add_slot("append"):
        ui.icon("event").on("click", menu.open).classes("cursor-pointer")

    return field


def parse(value: str | None, with_time: bool = True) -> datetime | None:
    """Converte 'dd/mm/aaaa[ HH:mm]' para datetime. Retorna None se vazio/inválido."""
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    fmts = (
        ["%d/%m/%Y %H:%M", "%d/%m/%Y"]
        if with_time
        else ["%d/%m/%Y"]
    )
    for fmt in fmts:
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def format_ptbr(dt: datetime | None, with_time: bool = True) -> str:
    """Formata datetime → 'dd/mm/aaaa[ HH:mm]'. Vazio se None."""
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")
