# Spec 003 — Agenda Academica (Funcionalidade 3.2)

> **Modo MVP**: spec consolidada em arquivo unico para acelerar entrega do Trabalho 1.
> Auditoria diferida (sera revisada em Trabalho 2).

## Contexto

Funcionalidade 3.2 do enunciado: o sistema deve permitir consultas tipo "o que tenho hoje?",
"quais sao minhas aulas esta semana?", "tenho prova amanha?".

Schema `events` ja criado pela migration 001 (Spec 001):
```sql
events (id, title, description, starts_at, ends_at, kind, location, created_at, updated_at)
kind CHECK IN ('aula','prova','trabalho','outro')
```

## Requisitos funcionais

### RF-003.1 — Modelo Pydantic `Event`

`src/domain/agenda/models.py`:
- `EventKind = Literal['aula','prova','trabalho','outro']`
- `Event` (id, title, description?, starts_at: datetime, ends_at?: datetime, kind, location?, created_at, updated_at)
- `EventCreate` (sem id/created_at/updated_at) — usado para INSERT.

### RF-003.2 — Repositorio CRUD

`src/domain/agenda/repo.py` (funcoes puras que recebem `conn: sqlite3.Connection`):
- `create_event(conn, EventCreate) -> Event`
- `get_event(conn, id) -> Event | None`
- `list_events(conn, start: datetime, end: datetime, kind: str | None = None) -> list[Event]`
- `update_event(conn, id, **patch) -> Event | None`
- `delete_event(conn, id) -> bool`

### RF-003.3 — Service com consultas temporais

`src/domain/agenda/service.py`:
- `events_today(conn, tz: ZoneInfo) -> list[Event]`
- `events_tomorrow(conn, tz) -> list[Event]`
- `events_this_week(conn, tz) -> list[Event]` (segunda-domingo)
- `has_event_kind_tomorrow(conn, kind: str, tz) -> bool` (ex.: "tem prova amanha?")
- `next_event(conn, tz) -> Event | None`

### RF-003.4 — Testes

- `tests/unit/test_agenda_models.py` — validacao Pydantic (ends_at > starts_at, kind valido).
- `tests/integration/test_agenda_repo.py` — CRUD + list_events com filtro de range.
- `tests/integration/test_agenda_service.py` — eventos hoje/amanha/semana com TZ.

## Design (decisoes locais)

- **Timezone**: TODOS os timestamps em SQLite sao ISO8601 UTC; a UI converte
  para timezone local. Service recebe `tz: ZoneInfo` para calcular "hoje" no
  fuso do usuario (default `America/Campo_Grande`).
- **Janela "hoje"**: `[00:00, 24:00)` no tz local, convertido para UTC para
  comparar com `starts_at`.
- **Janela "semana"**: segunda 00:00 a domingo 24:00 no tz local.
- **CHECK no DB**: `kind` ja tem CHECK; Pydantic Literal espelha.

## Fora de escopo

- Notificacoes/lembretes (Trabalho 2 ou nao implementado).
- Recorrencia (toda semana, todo mes) — apenas eventos pontuais.
- Import iCal/Google Calendar — entrada manual.

## DoD

- [ ] `src/domain/agenda/{__init__,models,repo,service}.py` implementados.
- [ ] Testes verdes.
- [ ] `ruff check src/domain/agenda tests/` limpo.
- [ ] Tools `consultar_agenda` (Spec 005) consegue chamar essas funcoes.
