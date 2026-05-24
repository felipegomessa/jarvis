"""Modelos Pydantic da Agenda — RF-003.1."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

EventKind = Literal["aula", "prova", "trabalho", "outro"]


class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    kind: EventKind = "outro"
    location: str | None = None

    @model_validator(mode="after")
    def _check_end_after_start(self) -> EventBase:
        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at deve ser >= starts_at")
        return self


class EventCreate(EventBase):
    pass


class Event(EventBase):
    id: int
    created_at: datetime
    updated_at: datetime
