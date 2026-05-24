"""Testes da paleta dupla (primary por tipo, secondary por kind/priority)."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.calendar_view import CalendarItem
from src.ui.components.calendar_colors import (
    EVENT_KIND_COLORS,
    EVENT_PRIMARY,
    TASK_PRIMARY,
    TASK_PRIORITY_COLORS,
    primary_for,
    secondary_for,
)


def _event(kind: str = "outro") -> CalendarItem:
    return CalendarItem(
        item_uid="event:1",
        item_type="event",
        source_id=1,
        title="Reunião",
        starts_at=datetime(2026, 5, 24, 10, 0),
        category=kind,
    )


def _task(priority: int = 0, status: str = "pending") -> CalendarItem:
    return CalendarItem(
        item_uid="task:1",
        item_type="task",
        source_id=1,
        title="Estudar",
        starts_at=datetime(2026, 5, 24, 23, 59),
        status=status,
        priority=priority,
    )


# ---------------- primary_for ----------------

@pytest.mark.parametrize("kind", ["aula", "prova", "trabalho", "outro"])
def test_primary_for_event_is_always_cyan(kind: str) -> None:
    assert primary_for(_event(kind=kind)) == EVENT_PRIMARY


@pytest.mark.parametrize("priority", [0, 1, 2])
def test_primary_for_task_is_always_pink(priority: int) -> None:
    assert primary_for(_task(priority=priority)) == TASK_PRIMARY


# ---------------- secondary_for ----------------

@pytest.mark.parametrize(
    "kind,expected_color",
    [
        ("aula", "#1E88E5"),
        ("prova", "#E53935"),
        ("trabalho", "#F57C00"),
        ("outro", "#757575"),
    ],
)
def test_secondary_for_event_returns_kind_color(kind: str, expected_color: str) -> None:
    assert secondary_for(_event(kind=kind)) == expected_color
    assert EVENT_KIND_COLORS[kind] == expected_color


@pytest.mark.parametrize(
    "priority,expected_color",
    [(0, "#9E9E9E"), (1, "#FB8C00"), (2, "#E91E63")],
)
def test_secondary_for_task_returns_priority_color(
    priority: int, expected_color: str
) -> None:
    assert secondary_for(_task(priority=priority)) == expected_color
    assert TASK_PRIORITY_COLORS[priority] == expected_color


def test_secondary_for_event_with_none_category_uses_outro() -> None:
    item = _event(kind="outro")
    item.category = None
    assert secondary_for(item) == "#757575"


def test_secondary_for_task_with_none_priority_uses_normal() -> None:
    item = _task(priority=0)
    item.priority = None
    assert secondary_for(item) == "#9E9E9E"


# ---------------- macro-categorias casam com filtros ----------------

def test_event_primary_matches_quasar_cyan_7() -> None:
    """Quasar color=cyan-7 corresponde a #00B8D4 — usado nos filtros."""
    assert EVENT_PRIMARY == "#00B8D4"


def test_task_primary_matches_quasar_pink_6() -> None:
    """Quasar color=pink-6 corresponde a #EC407A — usado nos filtros."""
    assert TASK_PRIMARY == "#EC407A"
