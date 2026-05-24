"""Agenda academica — modelo, repositorio, servico (Funcionalidade 3.2)."""

from src.domain.agenda.models import Event, EventCreate, EventKind
from src.domain.agenda.repo import (
    create_event,
    delete_event,
    get_event,
    list_all_events,
    list_events,
    update_event,
)
from src.domain.agenda.service import (
    DEFAULT_TZ,
    events_this_week,
    events_today,
    events_tomorrow,
    has_event_kind_tomorrow,
    next_event,
)

__all__ = [
    "DEFAULT_TZ",
    "Event",
    "EventCreate",
    "EventKind",
    "create_event",
    "delete_event",
    "events_this_week",
    "events_today",
    "events_tomorrow",
    "get_event",
    "has_event_kind_tomorrow",
    "list_all_events",
    "list_events",
    "next_event",
    "update_event",
]
