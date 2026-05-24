"""Input pill com menu '+' e histórico via setas — Fase 5."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from nicegui import ui

from src.ui.state import add_to_prompt_history, get_state


@dataclass
class DialogOption:
    label: str
    icon: str
    on_click: Callable[[], None]


class PromptInput:
    """Renderiza o pill: [+menu] [input] [seta-azul enviar]."""

    def __init__(
        self,
        on_submit: Callable[[str], Awaitable[None]],
        placeholder: str = "Pergunte alguma coisa",
    ) -> None:
        self._on_submit = on_submit
        self._placeholder = placeholder
        self._dialog_options: list[DialogOption] = []
        self._hist_idx = -1
        self.input_field: ui.input | None = None
        self.send_btn: ui.button | None = None

    def register_dialog(
        self, label: str, icon: str, on_click: Callable[[], None]
    ) -> None:
        self._dialog_options.append(DialogOption(label, icon, on_click))

    def render(self) -> None:
        with ui.row().classes("jarvis-pill items-center w-full no-wrap gap-2"):
            # Botão "+" com menu
            with ui.button(icon="add").props("flat round dense").style(
                "color:#dadada; min-width:32px"
            ):
                with ui.menu():
                    for opt in self._dialog_options:
                        ui.menu_item(
                            opt.label, on_click=opt.on_click
                        ).props(f'icon={opt.icon} auto-close')

            # Input
            self.input_field = ui.input(placeholder=self._placeholder).props(
                "borderless dense"
            ).classes("flex-1")
            self.input_field.on("keydown.up", self._on_arrow_up)
            self.input_field.on("keydown.down", self._on_arrow_down)
            self.input_field.on("keydown.enter", lambda _e=None: self._submit())

            # Botão enviar (circular azul)
            self.send_btn = ui.button(
                icon="arrow_upward", on_click=lambda: self._submit()
            ).props("round dense").classes("jarvis-send-btn").style(
                "background-color:#0A84FF; color:white; min-width:36px; height:36px"
            )

    async def _submit(self) -> None:
        if not self.input_field:
            return
        text = (self.input_field.value or "").strip()
        if not text:
            return
        self.input_field.value = ""
        add_to_prompt_history(text)
        self._hist_idx = -1
        await self._on_submit(text)

    def _on_arrow_up(self, _e=None) -> None:
        state = get_state()
        if not state.prompt_history or not self.input_field:
            return
        self._hist_idx = min(self._hist_idx + 1, len(state.prompt_history) - 1)
        self.input_field.value = state.prompt_history[self._hist_idx]

    def _on_arrow_down(self, _e=None) -> None:
        state = get_state()
        if not self.input_field:
            return
        if self._hist_idx <= 0:
            self._hist_idx = -1
            self.input_field.value = ""
            return
        self._hist_idx -= 1
        self.input_field.value = state.prompt_history[self._hist_idx]

    def set_value(self, text: str) -> None:
        if self.input_field:
            self.input_field.value = text
