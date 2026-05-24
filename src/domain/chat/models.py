"""Modelos Pydantic do módulo de sessões de chat — Fase 3 (D-024)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

MessageRole = Literal["user", "assistant", "system", "tool"]


class ChatSession(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessage(BaseModel):
    id: int
    session_id: int
    role: MessageRole
    content: str
    metadata: dict[str, Any] | None = None
    position: int
    created_at: datetime


class ChatSessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class ChatMessageCreate(BaseModel):
    role: MessageRole
    content: str
    metadata: dict[str, Any] | None = None
