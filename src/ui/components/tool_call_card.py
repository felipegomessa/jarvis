"""Chip discreto de tool call + dialog modal com I/O detalhado."""

from __future__ import annotations

import json
from typing import Any

from nicegui import ui

_STATUS_ICON = {"ok": "✓", "error": "✗", "pending": "…"}
_STATUS_COLOR = {"ok": "#19C37D", "error": "#E53935", "pending": "#FB8C00"}


def render_tool_call_chip(
    event_call: dict[str, Any],
    event_result: dict[str, Any] | None,
) -> None:
    """Renderiza um chip clicável. Click abre dialog com Entrada/Saída."""
    tool_name = event_call.get("tool", "?")
    args = event_call.get("args", {})
    status = (event_result or {}).get("status", "pending")
    duration = (event_result or {}).get("duration_ms", 0)
    output = (event_result or {}).get("output", {})
    icon_str = _STATUS_ICON.get(status, "•")
    color = _STATUS_COLOR.get(status, "#888")

    def _open_detail() -> None:
        with ui.dialog() as d, ui.card().classes(
            "jarvis-dialog-card w-full max-w-2xl"
        ):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label(f"🔧 {tool_name}").style(
                    "font-size:16px; font-weight:600; color:#fff"
                )
                ui.button(icon="close", on_click=d.close).props(
                    "flat round size=sm color=white"
                )
            ui.label(f"Status: {status} · {duration} ms").style(
                f"color:{color}; font-size:12px"
            )
            ui.label("Entrada").style(
                "color:#aaa; font-weight:600; margin-top:8px; font-size:13px"
            )
            ui.code(
                json.dumps(args, ensure_ascii=False, indent=2),
                language="json",
            ).classes("w-full")
            if event_result is not None:
                ui.label("Saída").style(
                    "color:#aaa; font-weight:600; margin-top:8px; font-size:13px"
                )
                ui.code(
                    json.dumps(
                        output, ensure_ascii=False, indent=2, default=str
                    ),
                    language="json",
                ).classes("w-full")
        d.open()

    with (
        ui.row()
        .classes("jarvis-tool-chip items-center no-wrap gap-1")
        .on("click", lambda _e=None: _open_detail())
    ):
        ui.icon("build").style(f"font-size:13px; color:{color}")
        ui.label(tool_name).style("font-size:12px; color:#ddd")
        ui.label(f"· {duration} ms").style("font-size:11px; color:#888")
        ui.label(icon_str).style(
            f"font-size:12px; color:{color}; margin-left:2px"
        )
        ui.tooltip("Ver Entrada/Saída").style(
            "background:#1a1a1a; color:#ddd; font-size:11px"
        )
