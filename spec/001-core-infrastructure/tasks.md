# Spec 001 — Core Infrastructure — Tasks

> Ordem por dependência. `[P]` = pode rodar em paralelo com a anterior.
> Cada task referencia o requirement (RF-001.X) e/ou seção do design.md.

## T-001.1 — Implementar `src/core/config.py` (RF-001.4)

- Classe `Settings(BaseSettings)` com 16 campos JARVIS_* + validações.
- `get_settings()` com `@lru_cache`.
- Validar: faltando `JARVIS_LLM_API_KEY` → `ValidationError` claro.

## T-001.2 — Implementar `src/core/logging.py` (RF-001.5) [P]

- `configure_logging(log_level, log_dir)`: remove handlers default, adiciona sink
  stderr colorido + arquivo rotativo diário em `logs/jarvis-{date}.log` (retenção
  14d, zip).
- Idempotente: chamar 2× não dobra handlers.

## T-001.3 — Criar migration `001_initial.sql` (RF-001.1, RF-001.6)

- Conteúdo conforme design.md §1: tabelas `documents`, `chunks`, `events`, `tasks`,
  `tool_call_logs` + 6 índices (`idx_chunks_doc`, `idx_events_starts_at`,
  `idx_tasks_status`, `idx_tasks_due_at`, `idx_tool_call_logs_ts`,
  `idx_tool_call_logs_tool`).
- Inclui `PRAGMA user_version = 1` no final.
- Arquivo em `src/core/migrations/001_initial.sql`.

## T-001.4 — Implementar `src/core/db.py` — conexão (RF-001.2)

- `get_connection(db_path=None)` como context manager.
- Carrega `sqlite_vec.load(conn)`.
- Aplica PRAGMAs: `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=3000`,
  `synchronous=NORMAL`.
- Row factory `sqlite3.Row`.
- Cria diretório de `db_path.parent` se não existir.
- Validar via `SELECT vec_version()` (logar em info; erro fatal se falhar).

## T-001.5 — Implementar `src/core/db.py` — migrations (RF-001.1)

- `_current_version(conn)` lê `PRAGMA user_version`.
- `_list_migrations()` lista `migrations/*.sql` em ordem alfabética/numérica.
- `_split_statements(sql)` parsea SQL em statements (descarta `-- comentários`,
  split por `;`).
- `apply_migrations(conn) -> int`:
  1. Lê `current = _current_version(conn)`.
  2. Calcula `max_available` entre migrations em disco. Se `current > max_available`
     → `RuntimeError("DB user_version > maior migration disponível...")`.
  3. Para cada migration pendente: `BEGIN`; loop `conn.execute(stmt)` para cada
     statement (pulando `PRAGMA user_version` embutido no .sql); `PRAGMA user_version = v`;
     `COMMIT`. Em erro: `ROLLBACK` + re-raise.
- **Crítico (bloqueador 1 da auditoria)**: NÃO usar `conn.executescript()` porque
  emite COMMIT implícito antes de rodar o script — anularia o `BEGIN` manual.
  Loop de `execute()` statement-por-statement preserva a transação.
- **Teste de atomicidade obrigatório** (em T-001.14): criar `tmp/002_broken.sql`
  com 2 statements (1º válido, 2º inválido), aplicar e verificar que `user_version`
  permanece em 1 e a tabela do 1º statement NÃO foi criada.

## T-001.6 — Implementar `src/core/db.py` — `log_tool_call()` (RF-001.6) [P]

- Helper que insere uma linha em `tool_call_logs` com todos os campos da ADR D-015.
- Timestamp UTC em ISO8601 com sufixo `Z`.
- Retorna `lastrowid`.

## T-001.7 — Implementar `src/core/health.py` (RF-001.7) [P]

- Dataclass `LLMHealth` + globals `_state` + `_lock` (threading.Lock).
- `get_health()`, `set_health(status, error)`.

## T-001.8 — Implementar `src/llm/types.py` e `exceptions.py` (RF-001.9) [P]

- `Message` (TypedDict), `Role` (Literal), `LLMHealthStatus`.
- `LLMError`, `LLMAuthError`, `LLMRequestError`, `LLMTimeoutError`, `LLMServerError`.

## T-001.9 — Implementar `src/llm/gemma_client.py` (RF-001.3)

- Classe `GemmaClient(settings: Settings)`.
- Método interno `_request(messages, stream, max_tokens)` com tenacity
  `AsyncRetrying` (3 tentativas, backoff exp 1→8s, retry em
  `APITimeoutError|APIConnectionError|RateLimitError`).
- Tratamento de `APIStatusError`: 401/403 → `LLMAuthError`; 4xx → `LLMRequestError`;
  5xx → `LLMServerError`.
- `stream_chat(messages, max_tokens=None) -> AsyncIterator[str]`.
- `complete_chat(messages, max_tokens=None) -> str`.
- `healthcheck() -> bool` (timeout 5s).

## T-001.10 — Implementar `src/llm/__init__.py` re-export (RF-001.9) [P]

- Re-exporta `GemmaClient`, `Message`, `Role`, e exceções principais.
- **Nota sobre `[P]`**: pode ser **escrita** em paralelo a T-001.8/9 (basta importar
  símbolos esperados), mas validação só ocorre depois que ambas tasks completarem.

## T-001.11 — Criar `tests/conftest.py` (RF-001.8)

- Fixtures globais:
  - `tmp_db(tmp_path)` — copia/cria DB temporário e aplica migrations.
  - `sample_messages` — lista de Messages mock.
  - `fake_llm` — stub de `GemmaClient` que retorna strings pré-programadas (sem
    bater no endpoint real).
- Registrar marker `live_llm`.

## T-001.12 — Configurar marker `live_llm` em `pyproject.toml` (RF-001.8) [P]

- Adicionar bloco em `[tool.pytest.ini_options]`:
  ```toml
  markers = ["live_llm: chama o endpoint real do LLM (skip a menos que JARVIS_RUN_LIVE_LLM=1)"]
  ```
- Hook em `conftest.py` para skip automático se `JARVIS_RUN_LIVE_LLM != "1"`.

## T-001.13 — Implementar testes unit (RF-001.8)

- `tests/unit/test_config.py` — Settings com .env mocado; faltando API_KEY
  levanta ValidationError; defaults corretos.
- `tests/unit/test_logging.py` — `configure_logging` é idempotente.
- `tests/unit/test_health.py` — `get_health()` inicia `UNKNOWN`; `set_health("ONLINE")`
  é refletido; 10 threads chamando `set_health`/`get_health` em loop não causam
  exceções (smoke de thread-safety via `threading.Lock`).

## T-001.14 — Implementar testes integration (RF-001.8)

- `tests/integration/test_db_migrations.py`:
  - DB vazio → v1 + 5 tabelas + 6 índices.
  - Re-aplicar é idempotente (sem efeito, sem erro).
  - **Teste de atomicidade**: injeta migration `002_broken.sql` com 2º stmt inválido →
        `user_version` permanece em 1, 1º statement NÃO persistiu (rollback efetivo).
  - **Teste DB-ahead-of-code**: força `PRAGMA user_version = 99` e verifica
        `RuntimeError`.
- `tests/integration/test_db_pragmas.py` — PRAGMAs corretos; `vec_version()` retorna.
- `tests/integration/test_db_log_tool_call.py` — insere + recupera; campos corretos
  incluindo timestamp UTC com sufixo `Z`.

## T-001.15 — Implementar smoke test LLM opt-in (RF-001.8)

- `tests/integration/test_gemma_smoke.py` com `@pytest.mark.live_llm`.
- Cria `GemmaClient` real, chama `healthcheck()`; asserção é resposta não-vazia
  do `complete_chat([ping])`.

## T-001.16 — Smoke test de import básico

- `tests/unit/test_smoke_import.py` — `import src; import src.core; import src.llm`
  funcionam sem erro (cobre o smoke test de reprodutibilidade pendente da Spec 000).

## T-001.17 — Auditoria pelo `spec-auditor`

- Invocar subagente `spec-auditor` com a pasta `spec/001-core-infrastructure/`.
- Output → `spec/001-core-infrastructure/audit.md`.
- Resolver bloqueadores se houver.

## T-001.18 — Aprovação humana

- Mantenedor humano lê audit.md e a spec. Aprova com `aprovo a spec 001`.

## T-001.19 — Implementação (executar T-001.1 a T-001.16 após aprovação)

- A implementação efetiva começa **após aprovação humana**.
- Validar gates: `ruff check .` e `mypy src` passam; `pytest tests/unit
  tests/integration` verde (smoke LLM skipped).

## Mapa de cobertura (rastreabilidade RF ↔ Tasks)

| Requisito | Tasks |
|-----------|-------|
| RF-001.1 (migrations versionadas) | T-001.3, T-001.5, T-001.14 |
| RF-001.2 (conexão + PRAGMAs + sqlite-vec) | T-001.4, T-001.14 |
| RF-001.3 (GemmaClient retry + dual stream) | T-001.9, T-001.15 |
| RF-001.4 (config tipada) | T-001.1, T-001.13 |
| RF-001.5 (logging loguru) | T-001.2, T-001.13 |
| RF-001.6 (tool_call_logs table + helper) | T-001.3, T-001.6, T-001.14 |
| RF-001.7 (healthcheck + degraded) | T-001.7, T-001.9 |
| RF-001.8 (test infra pirâmide) | T-001.11, T-001.12, T-001.13, T-001.14, T-001.15 |
| RF-001.9 (tipos comuns + exceções) | T-001.8, T-001.10 |
