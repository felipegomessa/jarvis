# Spec 004 — Lista de Tarefas (Funcionalidade 3.3)

> **Modo MVP**: spec consolidada.

## Contexto

Funcionalidade 3.3 do enunciado: adicionar tarefa, listar tarefas, marcar tarefa
como concluida.

Schema `tasks` ja criado pela migration 001:
```sql
tasks (id, title, description, due_at, status, priority, created_at, completed_at)
status CHECK IN ('pending','done')
priority INTEGER (0=normal, 1=alta, 2=urgente)
```

## Requisitos funcionais

### RF-004.1 — Modelo Pydantic `Task`

- `TaskStatus = Literal['pending','done']`
- `TaskPriority = Literal[0, 1, 2]`
- `Task` (id, title, description?, due_at?, status, priority, created_at, completed_at?)
- `TaskCreate` (title, description?, due_at?, priority?)

### RF-004.2 — Repositorio CRUD

`src/domain/tasks/repo.py`:
- `create_task(conn, TaskCreate) -> Task`
- `get_task(conn, id) -> Task | None`
- `list_tasks(conn, status?, only_due_until?, priority_min?) -> list[Task]`
- `update_task(conn, id, **patch) -> Task | None`
- `complete_task(conn, id) -> Task | None` (seta status='done' + completed_at=now)
- `delete_task(conn, id) -> bool`

### RF-004.3 — Service

`src/domain/tasks/service.py`:
- `pending_tasks(conn) -> list[Task]`
- `done_tasks(conn, limit: int = 50) -> list[Task]`
- `overdue_tasks(conn, tz) -> list[Task]` (status=pending AND due_at < now)
- `tasks_due_today(conn, tz) -> list[Task]`
- `tasks_due_this_week(conn, tz) -> list[Task]`

### RF-004.4 — Testes

- `tests/integration/test_tasks_repo.py` — CRUD + complete_task + list com filtros.

## Fora de escopo

- Subtarefas, recorrencia, lembretes.
- Atribuicao multi-usuario.

## DoD

- [ ] `src/domain/tasks/{__init__,models,repo,service}.py` implementados.
- [ ] Testes verdes.
