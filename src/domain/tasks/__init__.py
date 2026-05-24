"""Lista de tarefas — modelo, repositorio, servico (Funcionalidade 3.3)."""

from src.domain.tasks.models import Task, TaskCreate, TaskPriority, TaskStatus
from src.domain.tasks.repo import (
    complete_task,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)
from src.domain.tasks.service import (
    done_tasks,
    overdue_tasks,
    pending_tasks,
    tasks_due_this_week,
    tasks_due_today,
)

__all__ = [
    "Task",
    "TaskCreate",
    "TaskPriority",
    "TaskStatus",
    "complete_task",
    "create_task",
    "delete_task",
    "done_tasks",
    "get_task",
    "list_tasks",
    "overdue_tasks",
    "pending_tasks",
    "tasks_due_this_week",
    "tasks_due_today",
    "update_task",
]
