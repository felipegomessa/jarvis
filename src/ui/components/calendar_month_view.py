"""Grid mensal do calendário (7 colunas por 6 linhas) — Fase 9.

Renderiza eventos e tarefas juntos, distinguidos por cor + ícone (eventos =
barra com horário; tarefas = bolinha + título riscável). Click em dia vazio
ou item dispara callbacks fornecidos pelo dialog.
"""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Callable
from datetime import date, datetime, timedelta

from nicegui import ui

from src.core.db import get_connection
from src.domain.calendar_view import CalendarItem, list_calendar_items
from src.ui.components.calendar_colors import render_item_chip

PT_WEEKDAYS = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"]
PT_MONTHS = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


class CalendarMonthView:
    """Componente do grid mensal. Use:

        view = CalendarMonthView(on_day_click=..., on_item_click=...)
        view.render()
        view.set_filter(events=False)
        view.refresh()
    """

    def __init__(
        self,
        on_day_click: Callable[[date], None] | None = None,
        on_item_click: Callable[[CalendarItem], None] | None = None,
    ) -> None:
        self._on_day_click = on_day_click
        self._on_item_click = on_item_click
        self._current_month = date.today().replace(day=1)
        self._filters = {
            "events": True,
            "tasks": True,
            "only_pending_tasks": False,
            "kinds": {"aula", "prova", "trabalho", "outro"},
        }
        self._title_label: ui.label | None = None
        self._grid: ui.column | None = None

    def render(self) -> None:
        with ui.column().classes("w-full gap-2"):
            with ui.row().classes("items-center gap-2 w-full"):
                ui.button(icon="chevron_left", on_click=self._prev_month).props(
                    "flat round size=sm color=grey-5"
                )
                ui.button("Hoje", on_click=self._go_today).props(
                    "outline rounded dense size=sm color=white"
                )
                ui.button(icon="chevron_right", on_click=self._next_month).props(
                    "flat round size=sm color=grey-5"
                )
                self._title_label = ui.label("").style(
                    "font-size:20px; font-weight:600; color:#fff; margin-left:12px"
                )

            self._grid = ui.column().classes("w-full gap-0")
            self._draw()

    def _draw(self) -> None:
        if self._grid is None or self._title_label is None:
            return
        self._grid.clear()

        y, m = self._current_month.year, self._current_month.month
        self._title_label.text = f"{PT_MONTHS[m - 1]} de {y}"

        first = date(y, m, 1)
        first_wd = (first.weekday() + 1) % 7  # 0 = Domingo
        grid_start = first - timedelta(days=first_wd)

        _, last_day = monthrange(y, m)
        last = date(y, m, last_day)
        last_wd = (last.weekday() + 1) % 7
        grid_end = last + timedelta(days=(6 - last_wd))

        items_by_day: dict[date, list[CalendarItem]] = {}
        with get_connection() as conn:
            items = list_calendar_items(
                conn,
                start=datetime.combine(grid_start, datetime.min.time()),
                end=datetime.combine(grid_end + timedelta(days=1), datetime.min.time()),
                include_events=self._filters["events"],
                include_tasks=self._filters["tasks"],
                only_pending_tasks=self._filters["only_pending_tasks"],
                kinds=self._filters["kinds"],
            )
        for it in items:
            d = it.starts_at.date()
            items_by_day.setdefault(d, []).append(it)

        with self._grid:
            # Cabeçalho com nomes dos dias da semana
            with ui.row().classes("w-full no-wrap gap-0"):
                for wd in PT_WEEKDAYS:
                    ui.label(wd).classes("jarvis-weekday-header flex-1")

            # 6 linhas por 7 colunas
            day = grid_start
            while day <= grid_end:
                with ui.row().classes("w-full no-wrap gap-0"):
                    for _ in range(7):
                        is_other_month = day.month != m
                        is_today = day == date.today()
                        cell_classes = ["jarvis-cal-cell", "flex-1"]
                        if is_other_month:
                            cell_classes.append("other-month")
                        if is_today:
                            cell_classes.append("today-cell")
                        with ui.column().classes(
                            " ".join(cell_classes) + " gap-0"
                        ).on("click", lambda _e=None, d=day: self._click_day(d)):
                            num_classes = ["jarvis-day-number"]
                            if is_today:
                                num_classes.append("today")
                            elif is_other_month:
                                num_classes.append("other-month")
                            ui.label(str(day.day)).classes(" ".join(num_classes))

                            day_items = items_by_day.get(day, [])
                            visible = day_items[:4]
                            for it in visible:
                                render_item_chip(it, on_click=self._click_item)
                            if len(day_items) > 4:
                                ui.label(f"+ {len(day_items) - 4} mais").style(
                                    "font-size:10px; color:#888; padding:2px 6px"
                                )
                        day += timedelta(days=1)

    def _click_day(self, d: date) -> None:
        if self._on_day_click:
            self._on_day_click(d)

    def _click_item(self, item: CalendarItem) -> None:
        if self._on_item_click:
            self._on_item_click(item)

    def _prev_month(self) -> None:
        y, m = self._current_month.year, self._current_month.month
        self._current_month = date(y - 1, 12, 1) if m == 1 else date(y, m - 1, 1)
        self._draw()

    def _next_month(self) -> None:
        y, m = self._current_month.year, self._current_month.month
        self._current_month = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        self._draw()

    def _go_today(self) -> None:
        self._current_month = date.today().replace(day=1)
        self._draw()

    def go_to(self, d: date) -> None:
        """Navega para o mês que contém `d`."""
        self._current_month = date(d.year, d.month, 1)
        self._draw()

    def set_filter(self, **kwargs) -> None:
        self._filters.update(kwargs)
        self._draw()

    def refresh(self) -> None:
        self._draw()

    @property
    def current_month(self) -> date:
        return self._current_month
