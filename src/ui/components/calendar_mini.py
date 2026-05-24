"""Mini-calendário para navegação rápida (sidebar do dialog Calendário) — Fase 9."""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Callable
from datetime import date, timedelta

from nicegui import ui

PT_WEEKDAYS_SHORT = ["D", "S", "T", "Q", "Q", "S", "S"]
PT_MONTHS_SHORT = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]


class CalendarMini:
    """Mini-cal de 7 colunas por 6 linhas (mês visível) para navegação rápida."""

    def __init__(
        self,
        on_day_click: Callable[[date], None] | None = None,
        initial: date | None = None,
    ) -> None:
        self._on_day_click = on_day_click
        self._month = (initial or date.today()).replace(day=1)
        self._container: ui.column | None = None
        self._label: ui.label | None = None

    def render(self) -> None:
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.button(icon="chevron_left", on_click=self._prev).props(
                    "flat round dense size=xs color=grey-5"
                )
                self._label = ui.label("").style(
                    "color:#fff; font-size:13px; font-weight:600"
                )
                ui.button(icon="chevron_right", on_click=self._next).props(
                    "flat round dense size=xs color=grey-5"
                )

            self._container = ui.column().classes("w-full gap-0")
            self._draw()

    def _draw(self) -> None:
        if self._container is None or self._label is None:
            return
        self._container.clear()
        y, m = self._month.year, self._month.month
        self._label.text = f"{PT_MONTHS_SHORT[m - 1]} {y}"

        first = date(y, m, 1)
        first_wd = (first.weekday() + 1) % 7
        grid_start = first - timedelta(days=first_wd)

        _, last_day = monthrange(y, m)
        last = date(y, m, last_day)
        last_wd = (last.weekday() + 1) % 7
        grid_end = last + timedelta(days=(6 - last_wd))

        with self._container:
            with ui.row().classes("w-full no-wrap gap-0"):
                for wd in PT_WEEKDAYS_SHORT:
                    ui.label(wd).classes("flex-1 text-center").style(
                        "color:#888; font-size:10px; font-weight:600; padding:2px 0"
                    )

            day = grid_start
            while day <= grid_end:
                with ui.row().classes("w-full no-wrap gap-0"):
                    for _ in range(7):
                        is_other = day.month != m
                        is_today = day == date.today()
                        color = "#444" if is_other else "#ccc"
                        style_extra = ""
                        if is_today:
                            style_extra = (
                                "background:#0A84FF; color:white; "
                                "border-radius:50%;"
                            )
                            color = "white"
                        with ui.element("div").classes("flex-1").style(
                            f"text-align:center; padding:4px 0; "
                            f"color:{color}; font-size:11px; cursor:pointer; "
                            f"{style_extra}"
                        ).on("click", lambda _e=None, d=day: self._click(d)):
                            ui.label(str(day.day))
                        day += timedelta(days=1)

    def _click(self, d: date) -> None:
        if self._on_day_click:
            self._on_day_click(d)

    def _prev(self) -> None:
        y, m = self._month.year, self._month.month
        self._month = date(y - 1, 12, 1) if m == 1 else date(y, m - 1, 1)
        self._draw()

    def _next(self) -> None:
        y, m = self._month.year, self._month.month
        self._month = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        self._draw()

    def set_month(self, d: date) -> None:
        self._month = d.replace(day=1)
        self._draw()
