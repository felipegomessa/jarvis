"""Modelos Pydantic da Lista de Tarefas — RF-004.1."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["pending", "done"]
# 0=normal, 1=alta, 2=urgente
TaskPriority = Literal[0, 1, 2]


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    due_at: datetime | None = None
    priority: TaskPriority = 0


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    id: int
    status: TaskStatus = "pending"
    created_at: datetime
    completed_at: datetime | None = None
