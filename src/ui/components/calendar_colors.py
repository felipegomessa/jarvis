"""Paleta de cores e renderização de chips do calendário.

Estratégia visual (a partir da UI v2.1):
- Cor **primária** por TIPO (evento = cyan; tarefa = pink) — alinhada com os
  filtros laterais. Define o background do chip.
- Cor **secundária** por kind/priority (border-left do chip) — preserva a
  granularidade visual sem dominar a percepção evento-vs-tarefa.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from src.domain.calendar_view import CalendarItem

# Cores primárias por TIPO — espelham os filtros laterais.
EVENT_PRIMARY = "#00B8D4"   # cyan-7
TASK_PRIMARY = "#EC407A"    # pink-6

# Cores secundárias (border-left) — preservam informação fina de kind/priority.
EVENT_KIND_COLORS: dict[str, str] = {
    "aula": "#1E88E5",
    "prova": "#E53935",
    "trabalho": "#F57C00",
    "outro": "#757575",
}
TASK_PRIORITY_COLORS: dict[int, str] = {
    0: "#9E9E9E",
    1: "#FB8C00",
    2: "#E91E63",
}


def primary_for(item: CalendarItem) -> str:
    """Cor primária (background do chip) — distingue Evento vs Tarefa."""
    return EVENT_PRIMARY if item.item_type == "event" else TASK_PRIMARY


def secondary_for(item: CalendarItem) -> str:
    """Cor secundária (border-left do chip) — informa kind/priority."""
    if item.item_type == "event":
        return EVENT_KIND_COLORS.get(item.category or "outro", "#757575")
    return TASK_PRIORITY_COLORS.get(item.priority or 0, "#9E9E9E")


def render_item_chip(
    item: CalendarItem,
    on_click: Callable[[CalendarItem], None] | None = None,
) -> None:
    """Renderiza um chip horizontal compacto para um dia do grid mensal."""
    primary = primary_for(item)
    secondary = secondary_for(item)
    is_task = item.item_type == "task"
    is_done = is_task and item.status == "done"

    extra_class = "task-done" if is_done else ""
    # Background: cor primária com baixa opacidade. Border-left: secundária sólida.
    # Texto: tom claro mais legível em fundo escuro (mantém leitura).
    style = (
        f"background-color:{primary}20; border-left:3px solid {secondary}; "
        f"color:#eee;"
    )

    def _handle(_e=None, it=item) -> None:
        if on_click:
            on_click(it)

    with ui.row().classes(
        f"jarvis-cal-chip {extra_class} items-center no-wrap gap-1 w-full"
    ).style(style).on("click", _handle):
        if is_task:
            ui.icon(
                "radio_button_unchecked" if not is_done else "check_circle",
                size="xs",
            ).style(f"color:{primary}; min-width:14px")
            ui.label(item.title).style(
                "flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap"
            )
        else:
            time_str = item.starts_at.strftime("%H:%M")
            ui.label(time_str).style(
                f"color:{primary}; min-width:36px; font-variant-numeric:tabular-nums; "
                "font-weight:600"
            )
            ui.label(item.title).style(
                "flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap"
            )
