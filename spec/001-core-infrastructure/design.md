# Spec 001 — Core Infrastructure — Design

## Visão geral

Esta spec implementa os módulos **`src/core/*`** e **`src/llm/*`** sem entregar
funcionalidades de usuário — ela é a base sobre a qual as Specs 002–6 vão se apoiar.

Arquitetura (referência: [CLAUDE.md §4](../../CLAUDE.md#4-estrutura-de-diretórios)):

```
src/
├── core/
│   ├── __init__.py
│   ├── config.py              # Settings via pydantic-settings
│   ├── logging.py             # Configuração loguru
│   ├── db.py                  # Conexão SQLite, migrations, helpers
│   ├── health.py              # Estado degraded mode
│   └── migrations/
│       └── 001_initial.sql    # 5 tabelas + índices
├── llm/
│   ├── __init__.py
│   ├── types.py               # Message, Role, status
│   ├── exceptions.py          # LLMError + subclasses
│   └── gemma_client.py        # AsyncOpenAI wrapper
```

## 1. Modelo de dados (schema inicial)

`src/core/migrations/001_initial.sql`:

```sql
-- ============================================================
-- JARVIS Acadêmico — Migration 001 (initial)
-- Cria as 5 tabelas base. Bumpa user_version para 1 ao final.
-- ============================================================

-- ---------- RAG: documents & chunks ----------
CREATE TABLE documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    source_path   TEXT    NOT NULL UNIQUE,
    type          TEXT    NOT NULL CHECK (type IN ('pdf','txt','md')),
    char_count    INTEGER NOT NULL DEFAULT 0,
    chunk_count   INTEGER NOT NULL DEFAULT 0,
    ingested_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE chunks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id   INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,            -- ordem do chunk no documento
    text          TEXT    NOT NULL,
    char_start    INTEGER NOT NULL,
    char_end      INTEGER NOT NULL,
    UNIQUE (document_id, position)
);

CREATE INDEX idx_chunks_doc ON chunks(document_id);

-- Tabela vetorial separada (sqlite-vec usa virtual table 'vec0')
-- Será criada por Spec 002, ao iniciar o módulo rag. Aqui apenas comentamos
-- para documentar a estrutura prevista:
--   CREATE VIRTUAL TABLE chunk_vecs USING vec0(
--       chunk_id INTEGER PRIMARY KEY,
--       embedding FLOAT[384]
--   );

-- ---------- Agenda ----------
CREATE TABLE events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    description  TEXT,
    starts_at    TEXT    NOT NULL,             -- ISO8601 (datetime('now') format)
    ends_at      TEXT,                          -- pode ser NULL (sem fim definido)
    kind         TEXT    NOT NULL CHECK (kind IN ('aula','prova','trabalho','outro')),
    location     TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_events_starts_at ON events(starts_at);

-- ---------- Tarefas ----------
CREATE TABLE tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    description  TEXT,
    due_at       TEXT,                          -- ISO8601, NULL = sem prazo
    status       TEXT    NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','done')),
    priority     INTEGER NOT NULL DEFAULT 0,    -- 0=normal, 1=alta, 2=urgente
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_at ON tasks(due_at);

-- ---------- Audit de tool calls ----------
CREATE TABLE tool_call_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL DEFAULT (datetime('now')),
    tool_name   TEXT    NOT NULL,
    input_json  TEXT    NOT NULL,
    output_json TEXT,
    status      TEXT    NOT NULL CHECK (status IN ('ok','error')),
    error_msg   TEXT,
    duration_ms INTEGER NOT NULL,
    llm_call_id TEXT
);

CREATE INDEX idx_tool_call_logs_ts   ON tool_call_logs(ts);
CREATE INDEX idx_tool_call_logs_tool ON tool_call_logs(tool_name);

-- ============================================================
-- Atualiza versão
-- ============================================================
PRAGMA user_version = 1;
```

> Nota: o `PRAGMA user_version` aparece no final do arquivo, mas o **runner** em
> `db.py` aplica todo o `.sql` em uma transação e em seguida re-aplica o pragma
> programaticamente (pragmas dentro de transação podem ser tricky em SQLite).
> Detalhe na seção 4.

## 2. Configuração tipada (`src/core/config.py`)

```python
from functools import lru_cache
from pathlib import Path
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="JARVIS_",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    llm_base_url: HttpUrl = Field(default="https://llm.liaufms.org/v1/gemma-3-12b-it")
    llm_model: str = Field(default="google/gemma-3-12b-it")
    llm_api_key: str = Field(...)   # obrigatório, sem default
    llm_timeout_s: float = Field(default=60.0, gt=0)
    llm_max_tokens: int = Field(default=2048, gt=0)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # DB
    db_path: Path = Field(default=Path("./data/jarvis.db"))

    # RAG / embeddings
    embed_model: str = Field(default="intfloat/multilingual-e5-small")
    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)
    rag_top_k: int = Field(default=5, gt=0)

    # Logging
    log_level: str = Field(default="INFO")
    log_dir: Path = Field(default=Path("./logs"))

    # UI
    ui_host: str = Field(default="127.0.0.1")
    ui_port: int = Field(default=8080, gt=0, lt=65536)
    ui_dark: bool = Field(default=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

**Contrato**:
- `get_settings()` é o ponto único de leitura — sempre retorna mesma instância.
- Se `JARVIS_LLM_API_KEY` ausente, `ValidationError` no boot (intencional).
- Atributos imutáveis em runtime.

## 3. Logging (`src/core/logging.py`)

```python
import sys
from pathlib import Path
from loguru import logger


def configure_logging(log_level: str = "INFO", log_dir: Path = Path("./logs")) -> None:
    """Configura loguru com sink stderr (colorido) + arquivo rotativo diário."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{line}</cyan> | "
            "{message}"
        ),
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "jarvis-{time:YYYY-MM-DD}.log",
        level=log_level,
        rotation="00:00",                   # rotaciona à meia-noite
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{line} | {message}",
    )
```

## 4. Banco e migrations (`src/core/db.py`)

### 4.1 Conexão

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import sqlite_vec
from loguru import logger

from src.core.config import get_settings


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Abre conexão SQLite com PRAGMAs e sqlite-vec carregado."""
    path = db_path or get_settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)  # autocommit; usar BEGIN explícito
    try:
        conn.row_factory = sqlite3.Row
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        # PRAGMAs
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 3000")
        conn.execute("PRAGMA synchronous = NORMAL")
        yield conn
    finally:
        conn.close()
```

### 4.2 Migrations

> ⚠ **Nota técnica (Bloqueador 1 da auditoria endereçado)**: `sqlite3.Connection.executescript()`
> emite um `COMMIT` implícito *antes* de executar o script, o que tornaria nosso
> `BEGIN/COMMIT/ROLLBACK` manual ineficaz. Por isso usamos um loop de
> `conn.execute(stmt)` statement-por-statement dentro da transação aberta — assim
> uma falha no meio do script é desfeita pelo `ROLLBACK`.

```python
import re

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Split simples e robusto para o nosso schema:
# - remove linhas de comentário `-- ...`
# - split por `;`, descartando vazios após strip
_COMMENT_RE = re.compile(r"--[^\n]*")


def _split_statements(sql: str) -> list[str]:
    no_comments = _COMMENT_RE.sub("", sql)
    return [s.strip() for s in no_comments.split(";") if s.strip()]


def _current_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _list_migrations() -> list[tuple[int, Path]]:
    items: list[tuple[int, Path]] = []
    for f in MIGRATIONS_DIR.glob("*.sql"):
        v = int(f.name.split("_", 1)[0])
        items.append((v, f))
    items.sort(key=lambda x: x[0])
    return items


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Aplica migrations pendentes (forward-only). Retorna a versão final.

    Levanta RuntimeError se o DB estiver em versão maior que a maior migration
    disponível (sinal de que o código está desatualizado em relação ao DB).
    """
    current = _current_version(conn)
    all_migrations = _list_migrations()
    max_available = max((v for v, _ in all_migrations), default=0)

    if current > max_available:
        raise RuntimeError(
            f"DB user_version={current} > maior migration disponível "
            f"({max_available}). Atualize o código antes de prosseguir."
        )

    pending = [(v, f) for v, f in all_migrations if v > current]
    for v, f in pending:
        sql = f.read_text(encoding="utf-8")
        statements = _split_statements(sql)
        logger.info(f"applying migration {f.name} (v{current} → v{v}, {len(statements)} stmts)")
        try:
            conn.execute("BEGIN")
            for stmt in statements:
                # Ignora pragmas embutidos no .sql (gerenciados fora da transação)
                if stmt.upper().startswith("PRAGMA USER_VERSION"):
                    continue
                conn.execute(stmt)
            conn.execute(f"PRAGMA user_version = {v}")
            conn.execute("COMMIT")
            current = v
        except Exception:
            conn.execute("ROLLBACK")
            logger.exception(f"migration {f.name} failed; rolled back")
            raise
    return current
```

**Teste de atomicidade obrigatório** (T-001.5 / T-001.14): injetar uma migration
artificial em `tmp_path/migrations/002_broken.sql` cujo segundo statement contém
SQL inválido. Após o erro, verificar que: (a) `user_version` permaneceu em 1
(não foi para 2); (b) o primeiro statement (válido) NÃO persistiu (rollback fez
seu trabalho).

### 4.3 Helper de tool call logging

```python
import json
from datetime import datetime, timezone


def log_tool_call(
    conn: sqlite3.Connection,
    tool_name: str,
    input_json: str,
    output_json: str | None,
    status: str,                  # 'ok' | 'error'
    error_msg: str | None,
    duration_ms: int,
    llm_call_id: str | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO tool_call_logs
            (ts, tool_name, input_json, output_json, status, error_msg, duration_ms, llm_call_id)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            tool_name,
            input_json,
            output_json,
            status,
            error_msg,
            duration_ms,
            llm_call_id,
        ),
    )
    return cur.lastrowid
```

> Nota: `datetime.now(timezone.utc)` substitui `datetime.utcnow()` (deprecado em
> Python 3.12). O `replace("+00:00", "Z")` normaliza para formato `...Z` esperado.

## 5. Cliente LLM (`src/llm/`)

### 5.1 Tipos

```python
# src/llm/types.py
from typing import Literal, TypedDict

Role = Literal["system", "user", "assistant", "tool"]

class Message(TypedDict):
    role: Role
    content: str

LLMHealthStatus = Literal["ONLINE", "OFFLINE", "UNKNOWN"]
```

### 5.2 Exceções

```python
# src/llm/exceptions.py
class LLMError(Exception): ...
class LLMAuthError(LLMError): ...          # 401 / 403
class LLMRequestError(LLMError): ...       # 4xx outros
class LLMTimeoutError(LLMError): ...       # timeout/connection
class LLMServerError(LLMError): ...        # 5xx
```

### 5.3 GemmaClient

```python
# src/llm/gemma_client.py
import asyncio
from typing import AsyncIterator

from loguru import logger
from openai import AsyncOpenAI
from openai import APIConnectionError, APITimeoutError, RateLimitError, APIStatusError
from tenacity import (
    AsyncRetrying, RetryError, retry_if_exception_type, stop_after_attempt,
    wait_exponential,
)

from src.core.config import Settings
from src.llm.types import Message
from src.llm.exceptions import (
    LLMAuthError, LLMRequestError, LLMServerError, LLMTimeoutError,
)


_RETRYABLE = (APITimeoutError, APIConnectionError, RateLimitError)


class GemmaClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = AsyncOpenAI(
            base_url=str(settings.llm_base_url),
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_s,
        )

    async def _request(self, messages: list[Message], stream: bool, max_tokens: int | None):
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type(_RETRYABLE),
            reraise=True,
        ):
            with attempt:
                try:
                    return await self._client.chat.completions.create(
                        model=self._settings.llm_model,
                        messages=messages,
                        max_tokens=max_tokens or self._settings.llm_max_tokens,
                        temperature=self._settings.llm_temperature,
                        stream=stream,
                    )
                except APIStatusError as e:
                    if e.status_code in (401, 403):
                        raise LLMAuthError(str(e)) from e
                    if 400 <= e.status_code < 500:
                        raise LLMRequestError(str(e)) from e
                    raise LLMServerError(str(e)) from e

    async def stream_chat(
        self,
        messages: list[Message],
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        resp = await self._request(messages, stream=True, max_tokens=max_tokens)
        async for chunk in resp:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def complete_chat(
        self,
        messages: list[Message],
        max_tokens: int | None = None,
    ) -> str:
        resp = await self._request(messages, stream=False, max_tokens=max_tokens)
        return resp.choices[0].message.content or ""

    async def healthcheck(self) -> bool:
        try:
            await asyncio.wait_for(
                self.complete_chat(
                    [{"role": "user", "content": "ping"}], max_tokens=1
                ),
                timeout=5.0,
            )
            return True
        except Exception as e:
            logger.warning(f"LLM healthcheck failed: {e!r}")
            return False
```

### 5.4 Health state

```python
# src/core/health.py
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

@dataclass
class LLMHealth:
    status: str = "UNKNOWN"     # ONLINE | OFFLINE | UNKNOWN
    last_check: datetime | None = None
    last_error: str | None = None

_state = LLMHealth()
_lock = Lock()

def get_health() -> LLMHealth:
    with _lock:
        return LLMHealth(_state.status, _state.last_check, _state.last_error)

def set_health(status: str, error: str | None = None) -> None:
    with _lock:
        _state.status = status
        _state.last_check = datetime.now(timezone.utc)
        _state.last_error = error
```

## 6. Fluxos críticos

### 6.1 Startup
```
main.py
  → configure_logging()
  → settings = get_settings()      [se .env falta JARVIS_LLM_API_KEY → erro claro]
  → with get_connection() as conn: apply_migrations(conn)
  → gemma = GemmaClient(settings)
  → ok = await gemma.healthcheck()
  → set_health("ONLINE" if ok else "OFFLINE")
  → start_ui(...)
```

### 6.2 Tool call logging
```
[chamada de tool durante agent loop]
  → registra t_start
  → executa tool
  → t_end
  → with get_connection() as conn:
        log_tool_call(conn, name, input_json, output_json, status, error, t_end - t_start, llm_id)
```

## 7. Política de erros (estende CLAUDE.md §8)

| Cenário | Comportamento |
|---|---|
| Migration falha | Rollback do BEGIN; loga SQL + exceção; re-raise (boot aborta). |
| `vec_version()` falha (extensão não carregada) | Erro fatal de inicialização com mensagem clara para reinstalar via `uv sync`. |
| `JARVIS_LLM_API_KEY` ausente | `ValidationError` no `get_settings()` — boot aborta com mensagem. |
| Healthcheck falha | `set_health("OFFLINE")` — UI consulta e mostra banner. App não aborta. |
| LLM 401 durante uso | `LLMAuthError` → UI mostra toast; `set_health("OFFLINE")`. |
| LLM 5xx/timeout | 3 retries via tenacity; após esgotar, `LLMServerError`/`LLMTimeoutError` propaga. |
| SQLite locked | `busy_timeout=3000` retry automático; após 3s, erro. |
| DB user_version > maior migration disponível | Loga `error("DB ahead of code")`; boot aborta com mensagem clara. |

## 8. Plano de testes

### Unit (`tests/unit/`)
- `test_config.py` — Settings carrega de .env, default funciona, faltando key → ValidationError.
- `test_logging.py` — configure_logging é idempotente.
- `test_message_type.py` — type checks Message/Role.
- `test_health.py` — `get_health()` inicia em `UNKNOWN`; `set_health("ONLINE")` reflete;
      thread-safety básica (10 threads chamando `set_health`/`get_health` em loop não levantam).

### Integration (`tests/integration/`)
- `test_db_migrations.py` — `apply_migrations` em DB vazio cria 5 tabelas + 6 índices;
      re-aplicar é no-op; `user_version == 1`. Inclui teste de atomicidade: injeta
      migration `002_broken.sql` com 2º statement inválido e verifica rollback
      (user_version não bumpa, 1º statement não persiste). Inclui teste de
      DB-ahead-of-code: força `PRAGMA user_version = 99` e verifica que
      `apply_migrations` levanta `RuntimeError`.
- `test_db_pragmas.py` — conexão tem WAL/foreign_keys/busy_timeout/synchronous corretos;
      `vec_version()` retorna string.
- `test_db_log_tool_call.py` — insere + recupera linha.

### Smoke LLM (opt-in via `JARVIS_RUN_LIVE_LLM=1`)
- `test_gemma_smoke.py` — `healthcheck()` retorna True com endpoint+token reais;
      `complete_chat([ping]) ` retorna não-vazio. **Skipped por default**.

## 9. Contratos exportados (consumíveis por outras Specs)

```python
# Outras Specs vão usar:
from src.core.config import get_settings, Settings
from src.core.db import get_connection, apply_migrations, log_tool_call
from src.core.logging import configure_logging
from src.core.health import LLMHealth, get_health, set_health
from src.llm import GemmaClient, Message, Role
from src.llm.exceptions import LLMError, LLMAuthError, LLMRequestError, LLMTimeoutError, LLMServerError
```

## 10. Definition of Done

A Spec 001 está pronta quando:

### Artefatos de código
- [x] `src/core/config.py` implementado.
- [x] `src/core/logging.py` implementado.
- [x] `src/core/db.py` (conexão + migrations + log_tool_call + smoke_check_vec) implementado.
- [x] `src/core/migrations/001_initial.sql` criado com 5 tabelas + 6 índices.
- [x] `src/core/health.py` implementado.
- [x] `src/llm/types.py`, `exceptions.py`, `gemma_client.py` implementados.
- [x] `src/llm/__init__.py` re-exporta.
- [x] `src/main.py` atualizado para fazer bootstrap (logging + DB + healthcheck).

### Testes
- [x] `tests/conftest.py` com fixtures `tmp_db`, `tmp_db_path`, `sample_messages`, `fake_llm`.
- [x] Hook `pytest_collection_modifyitems` skipa `live_llm` se `JARVIS_RUN_LIVE_LLM != 1`.
- [x] Marker `live_llm` registrado em `pyproject.toml`.
- [x] Testes unit: `test_config.py`, `test_logging.py`, `test_health.py`,
      `test_message_type.py`, `test_smoke_import.py`.
- [x] Testes integration: `test_db_migrations.py` (com atomicidade + DB-ahead),
      `test_db_pragmas.py`, `test_db_log_tool_call.py`.
- [x] Smoke LLM marcado `live_llm`: `test_gemma_smoke.py`.
- [ ] **Executar a suite** (`pytest tests/unit tests/integration -q`) — depende de
      `uv sync` ter sido rodado para instalar deps.

### Gates
- [ ] `ruff check .` passa.
- [ ] `mypy src` passa (modo não-estrito).
- [x] Auditoria `spec-auditor` realizada (`spec/001-core-infrastructure/audit.md` —
      veredito APROVADA COM RESSALVAS; bloqueador B1 + ressalvas R1–R8 endereçadas).
- [x] Aprovação humana explícita — sessão 2026-05-23 (chat).
