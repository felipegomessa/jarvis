# Spec 001 — Core Infrastructure — Requirements

> Esta spec entrega a **fundação operacional** sobre a qual as Specs 002–6 serão
> construídas: schema do banco, cliente LLM, configuração, logging e infraestrutura
> de testes.

## Contexto

A Spec 000-foundation deixou pronto o scaffolding (estrutura de pastas, pyproject.toml,
constituição, ADRs estratégicos). Agora precisamos **código operacional** que:

- crie e mantenha o schema SQLite (com migrations versionadas),
- exponha um cliente para a LLM Gemma 12B (async, com retry, streaming dual),
- carregue configuração tipada e segura,
- emita logs amigáveis e auditáveis,
- estabeleça padrões de teste reutilizáveis pelas próximas Specs.

ADRs novos consolidados durante a entrevista desta spec: **D-012 a D-019**
(ver [../../decisions.md](../../decisions.md)).

## Requisitos funcionais

### RF-001.1 — Migrations versionadas com PRAGMA user_version

O sistema deve aplicar migrations forward-only ao iniciar, baseado em `user_version`
do SQLite.

**Critério de aceitação**:
- ✓ Pasta `src/core/migrations/` contém ao menos `001_initial.sql`.
- ✓ `001_initial.sql` cria 5 tabelas: `documents`, `chunks`, `events`, `tasks`,
      `tool_call_logs` (schemas detalhados em design.md).
- ✓ Função `apply_migrations(conn)` em `src/core/db.py` lê `PRAGMA user_version`,
      identifica scripts pendentes em ordem alfabética, executa em transação por arquivo,
      bumpa `user_version` ao final de cada um.
- ✓ Re-executar `apply_migrations()` em DB já atualizado é **no-op** (não erra).
- ✓ Teste de integração cobre: DB vazio → 5 tabelas criadas; DB já em v1 → idempotente.

### RF-001.2 — Conexão SQLite padronizada com sqlite-vec

O sistema deve abrir conexões SQLite com PRAGMAs corretos e a extensão `sqlite-vec`
carregada.

**Critério de aceitação**:
- ✓ Função `get_connection()` em `src/core/db.py` é um context manager.
- ✓ Toda conexão aplica: `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=3000`,
      `synchronous=NORMAL`.
- ✓ Conexão tem `sqlite-vec` carregado (verificável via `SELECT vec_version()`).
- ✓ Teste de integração verifica os 4 PRAGMAs e a extensão.

### RF-001.3 — Cliente LLM Gemma 12B com retry e dual streaming

O sistema deve expor um cliente assíncrono que fala com o endpoint OpenAI-compatible
da LIA UFMS, com retry e dois modos de resposta.

**Critério de aceitação**:
- ✓ Classe `GemmaClient` em `src/llm/gemma_client.py` recebe `settings` (LLM config).
- ✓ Método `stream_chat(messages, max_tokens=None) -> AsyncIterator[str]` faz `yield`
      de cada delta de token.
- ✓ Método `complete_chat(messages, max_tokens=None) -> str` retorna a resposta
      completa como string.
- ✓ Método `healthcheck() -> bool` faz 1 chamada rápida (timeout 5s, max_tokens=1) e
      retorna True/False.
- ✓ Ambos `stream_chat` e `complete_chat` aplicam retry com `tenacity` (3 tentativas,
      backoff exponencial 1→8s) em `APITimeoutError`, `APIConnectionError` e
      `RateLimitError` (429). 5xx também re-tenta (via `LLMServerError` capturado
      no wrapping de `APIStatusError`).
- ✓ Erros 4xx **exceto 429** (auth 401/403, validation 400/422 etc.) não re-tentam
      e propagam como `LLMAuthError`/`LLMRequestError`.
- ✓ Tipo `Message` (TypedDict ou Pydantic) define `{role, content}`.

### RF-001.4 — Configuração tipada via pydantic-settings + .env

O sistema deve carregar configuração de variáveis de ambiente, com tipos validados
e defaults sensatos.

**Critério de aceitação**:
- ✓ `src/core/config.py` define classe `Settings(BaseSettings)` com TODAS as 16
      variáveis `JARVIS_*` declaradas em `.env.example`.
- ✓ Pydantic v2 valida tipos (URL, int, float, path, bool).
- ✓ Prioridade: variáveis explícitas no shell > `.env` > defaults da classe.
- ✓ `Settings.llm_api_key` é exigida (sem default); se ausente, erro claro
      (`ValidationError`) no startup.
- ✓ Função `get_settings()` retorna singleton (`@lru_cache`).

### RF-001.5 — Logging via loguru

O sistema deve configurar loguru com sink de console (colorido) e arquivo (rotativo).

**Critério de aceitação**:
- ✓ `src/core/logging.py` expõe `configure_logging(log_level: str, log_dir: Path)` que:
  - Remove handlers default.
  - Adiciona sink stderr com cores e nível `log_level`.
  - Adiciona sink em arquivo `<log_dir>/jarvis-{time:YYYY-MM-DD}.log`, rotação diária,
        retenção 14 dias, compressão `.zip` em rotação.
- ✓ Format inclui: timestamp ISO, level, módulo, linha, mensagem.
- ✓ Configurada uma única vez por processo (idempotente).
- ✓ `main.py` invoca como: `configure_logging(settings.log_level, settings.log_dir)`.

### RF-001.6 — Tabela tool_call_logs auditável

A primeira migration cria a tabela `tool_call_logs` (Spec 005 a consome).

**Critério de aceitação**:
- ✓ `001_initial.sql` cria a tabela com schema da ADR [D-015](../../decisions.md#d-015).
- ✓ 2 índices criados: `idx_tool_call_logs_ts` e `idx_tool_call_logs_tool`.
- ✓ Função helper `log_tool_call(tool_name, input_json, output_json, status,
      error_msg, duration_ms, llm_call_id)` em `src/core/db.py` insere uma linha.
- ✓ Teste verifica inserção e leitura.

### RF-001.7 — Healthcheck e degraded mode

O sistema deve checar a LLM no startup e expor o estado para a UI.

**Critério de aceitação**:
- ✓ `src/core/health.py` (ou `src/llm/health.py`) expõe `class LLMHealth` com
      estado `ONLINE`/`OFFLINE` e timestamp da última checagem.
- ✓ Função `async run_healthcheck() -> LLMHealth` chama `GemmaClient.healthcheck()`,
      atualiza estado e retorna.
- ✓ Logging em nível `info` quando ONLINE, `warning` quando OFFLINE.
- ✓ Estado é um singleton acessível por toda a app.

### RF-001.8 — Infraestrutura de testes (pirâmide)

A spec entrega `tests/conftest.py` com fixtures e exemplos básicos.

**Critério de aceitação**:
- ✓ `tests/conftest.py` define fixtures:
  - `tmp_db` (pytest tmp_path + apply_migrations).
  - `sample_messages` (lista de Messages mock).
  - `fake_llm` (stub de GemmaClient com respostas pré-programadas).
- ✓ Marker `live_llm` registrado em `pyproject.toml` (`[tool.pytest.ini_options].markers`).
- ✓ Testes marcados `@pytest.mark.live_llm` são **skipped** se
      `JARVIS_RUN_LIVE_LLM != 1`.
- ✓ Ao menos 1 teste unit + 1 teste integration entregues nesta spec (validação básica).

### RF-001.9 — Tipos comuns (Message, LLMHealth, exceptions)

A spec define tipos Pydantic compartilhados que outras specs usarão.

**Critério de aceitação**:
- ✓ `src/llm/types.py` define `Message`, `Role` (Literal), `LLMHealthStatus`.
- ✓ `src/llm/exceptions.py` define `LLMError`, `LLMAuthError`, `LLMRequestError`,
      `LLMTimeoutError`.
- ✓ Imports a partir de `src/llm/__init__.py` re-exportam o necessário.

## Critérios de qualidade (transversais, herdados de Spec 000)

- CT-1 a CT-7 (ver `spec/000-foundation/requirements.md`).
- Cobertura de teste: cada RF-001.X com função implementada tem ≥1 teste.

## Fora de escopo desta spec

- **NÃO** implementa parsing/chunking de PDFs (Spec 002).
- **NÃO** implementa retrieval RAG (Spec 002).
- **NÃO** implementa modelos de agenda/tasks (Specs 003, 004).
- **NÃO** implementa o agent loop de tool calling (Spec 005) — só cria a tabela
  e o helper de logging.
- **NÃO** implementa NiceGUI (Spec 006).
- **NÃO** carrega o modelo de embeddings — só prepara a abstração lazy
  (carregamento real fica em Spec 002 que de fato vai usá-lo).

## Riscos identificados nesta spec

| Risco | Mitigação |
|---|---|
| `sqlite-vec` pode não instalar em algumas plataformas via uv | Teste de smoke: `SELECT vec_version()` no startup; mensagem clara se falhar. |
| Healthcheck no startup adiciona ~5s ao boot | Timeout estrito (5s), executa em background async para não travar UI. |
| `multilingual-e5-small` ainda não baixou na 1ª execução | Não é problema desta spec (Spec 002 lida com isso). |
| Token inválido (401) | Healthcheck pega cedo; UI mostra banner; usuário corrige `.env`. |
| Migration falha no meio (corrupção parcial) | Cada migration em transação; rollback automático em erro; log de erro com SQL exato. |
