# HANDOFF — Continuação do projeto JARVIS Acadêmico

> **Quem é você que está lendo isto?** Provavelmente: (a) eu mesmo voltando ao
> projeto depois de um tempo, ou (b) outro Claude Code em nova sessão, ou (c)
> meu colega de dupla. Este documento deve te dar tudo o que precisa para
> continuar de onde paramos.

> **Última atualização**: 2026-05-24
> **Estado da entrega**: Trabalho 1 ~95% pronto (faltam só itens humanos —
> dataset, vídeo, git push). UI v2 ChatGPT-style + Calendário unificado já
> implementados e validados.

---

## 1. Leitura obrigatória (ordem)

1. **`CLAUDE.md`** — constituição: princípios, stack, processo SDD, regras de
   dependência entre camadas, política global de erros.
2. **`decisions.md`** — todas as 26 ADRs (D-001 a D-026). Cada uma tem
   contexto, decisão, alternativas e consequências.
3. **`STATUS.md`** — situação atual e o que falta (entregas humanas).
4. **Este arquivo** (HANDOFF.md) — comandos práticos + gotchas + onde está
   tudo.
5. **`NOTES.md`** — aprendizados, conceitos não-óbvios, troubleshooting.

---

## 2. Setup em máquina nova (10 minutos)

```powershell
# 1. Clone (se ainda não tem)
# git clone <repo>
# cd Trabalho1

# 2. Instalar uv (Python package manager — Astral)
python -m pip install --user uv

# 3. Criar venv com Python 3.12 + instalar deps (main + dev)
python -m uv sync --extra dev
# ⏱ ~3-5 min na 1ª vez (baixa torch, sentence-transformers, nicegui, etc.)

# 4. Configurar token Gemma (vem no PDF do enunciado)
copy .env.example .env
# editar .env e preencher JARVIS_LLM_API_KEY=<token>
# Token do enunciado: Cxt2ftLF7d3mHS2JdiFqB-eSDAQeZvFATPXPs02lV9A

# 5. Validar baseline
.venv\Scripts\python.exe -m pytest tests/unit tests/integration -q
# Esperado: 75 passed, 3 skipped (smoke LLM opt-in)

.venv\Scripts\python.exe -m ruff check .
# Esperado: All checks passed!

# 6. Rodar a app
.venv\Scripts\python.exe -m src.main
# → http://127.0.0.1:8080
# ⏱ Boot: ~10s (carrega DB + healthcheck LLM)
# ⏱ 1ª query RAG: +5-10s (baixa modelo de embeddings ~120MB)
```

### Para rodar smoke LLM tests (consome token):

```powershell
$env:JARVIS_RUN_LIVE_LLM="1"
.venv\Scripts\python.exe -m pytest tests/integration/test_gemma_smoke.py -v
```

---

## 3. Estado do projeto agora (snapshot 2026-05-24)

### O que está pronto e validado

| Funcionalidade | Status | Onde |
|---|---|---|
| RAG (ingest + chunk + embed + retrieve + prompt + pipeline) | ✅ | `src/rag/` |
| Agenda (CRUD + service temporal) | ✅ | `src/domain/agenda/` |
| Tarefas (CRUD + status + prioridade) | ✅ | `src/domain/tasks/` |
| Tool Calling (8 tools + agent loop com logs SQLite) | ✅ | `src/tools/`, `src/llm/agent.py` |
| Chat sessions persistidas (D-024) | ✅ | `src/domain/chat/` |
| Calendário unificado (D-025) | ✅ | `src/domain/calendar_view/` |
| UI v2 ChatGPT-style (D-026) | ✅ | `src/ui/` |
| Migrations 001 + 002 + 003 + 004 (v=4) | ✅ | `src/core/migrations/` |
| 75 testes pytest passando | ✅ | `tests/` |
| ruff limpo | ✅ | — |
| Bootstrap end-to-end | ✅ | — |

### O que falta (entregas humanas, NÃO de código)

| Item | Onde | Prazo |
|---|---|---|
| **Dataset** ≥10 documentos acadêmicos em `/data/` | `data/` | Antes da entrega Trabalho 1 |
| Atualizar `data/README.md` com inventário/origem/limitações | `data/README.md` | Idem |
| **Vídeo demo** ≤3 min (arquitetura + sistema funcionando) | — | Idem |
| `git init` + commit + push para GitHub | — | Idem |
| Adicionar nomes da dupla em `README.md` | `README.md` | Idem |

### Pendências adiadas para Trabalho 2

- Funcionalidade 3.4 (planejamento de estudos integrando agenda+tarefas+materiais)
- ≥2 funcionalidades de aprendizado (1 interativa: sistema pergunta e avalia)
- Avaliação ≥10 perguntas (correta / parcial / incorreta)
- Análise de erros (≥3 falhas: tipo, causa, possível solução)

---

## 4. Como continuar o trabalho

### Cenário A: Apenas finalizar Trabalho 1 (caminho mais curto)

1. **Coletar dataset**: pegar 10+ PDFs/textos acadêmicos (slides de aula,
   capítulos de livro, apostilas em IA/ML) e colocar em `data/`.
2. **Indexar**: `.venv\Scripts\python.exe -m src.rag.populate`
3. **Validar via UI**: subir app, abrir "+", "Enviar material" → ver
   documentos. Fazer 3 perguntas RAG, ver respostas com citações `[Doc N]`.
4. **Atualizar `data/README.md`**: tabela com nome, tipo, origem, limitações.
5. **Atualizar `README.md`**: nomes da dupla.
6. **Gravar vídeo** (3 min): mostrar (1) arquitetura no papel/diagrama,
   (2) chat fazendo tool call de agenda/tarefa, (3) RAG respondendo com
   citações, (4) calendário com eventos e tarefas misturados, (5) tab
   Auditoria mostrando logs do `tool_call_logs`.
7. **Git**: `git init && git add . && git commit -m "Trabalho 1 — MVP completo"`
   → criar repo no GitHub → `git remote add origin ... && git push -u origin main`.

### Cenário B: Avançar para Trabalho 2

Ver `STATUS.md` seção "Trabalho 2". Sugestão de nova Spec 007:

```
spec/007-study-planner/
├── requirements.md   # 3.4 planejamento estudos
└── design.md         # nova tool consultar_calendario JÁ EXISTE; agente
                     # combina agenda + tarefas + materiais via prompts
                     # tipo "monte um plano de estudos para a prova X"
```

E Spec 008 (aprendizado):
- `tool_gerar_exercicio(material_id, dificuldade)` — LLM cria 3 questões.
- `tool_avaliar_resposta(pergunta, resposta_usuario, gabarito)` — score
  + feedback.

---

## 5. Comandos do dia-a-dia

```powershell
# Rodar app (modo dev, sem reload)
.venv\Scripts\python.exe -m src.main

# Rodar testes
.venv\Scripts\python.exe -m pytest tests/unit tests/integration -q

# Rodar 1 teste específico
.venv\Scripts\python.exe -m pytest tests/integration/test_agent_loop.py -v

# Indexar dataset /data
.venv\Scripts\python.exe -m src.rag.populate

# Lint
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff check . --fix   # auto-fix

# Type-check (não-estrito, opcional)
.venv\Scripts\python.exe -m mypy src --ignore-missing-imports

# Reset do DB (cuidado! perde dados)
del data\jarvis.db data\jarvis.db-wal data\jarvis.db-shm

# Adicionar nova dep
python -m uv add <pacote>

# Atualizar deps existentes
python -m uv sync --extra dev --upgrade
```

---

## 6. Onde está cada coisa

### Configuração
- **`.env`** (não-commitado): variáveis JARVIS_* — token LLM, paths, modelos.
- **`.env.example`**: template versionado. 17 variáveis no total.
- **`pyproject.toml`**: deps + config ruff/pytest/mypy + marker `live_llm`.
- **`src/core/config.py`**: classe `Settings(BaseSettings)` com `@lru_cache`.

### Database
- **Arquivo**: `data/jarvis.db` (+ `-wal` e `-shm` em runtime).
- **Schema**: `src/core/migrations/00X_*.sql` (forward-only).
  - 001_initial: documents, chunks, events, tasks, tool_call_logs (6 índices)
  - 002_rag: content_hash + chunk_vecs (virtual table sqlite-vec)
  - 003_chat: chat_sessions + chat_messages
  - 004_calendar_view: VIEW calendar_items_view
- **Acesso**: `from src.core.db import get_connection`. Sempre via context
  manager: `with get_connection() as conn:` (gerencia close + sqlite-vec load).
- **Migration runner**: `apply_migrations(conn)` em `src/core/db.py` —
  usa loop manual de `execute()` (NÃO `executescript()` — esse faz COMMIT
  implícito que quebra rollback).

### LLM
- **Cliente**: `src/llm/gemma_client.py` (`GemmaClient` async, com tenacity
  para retry de 5xx/timeout/429).
- **Agent loop**: `src/llm/agent.py` (`AgentLoop.respond(user_msg,
  history=None, session_id=None)`).
- **Tipos**: `src/llm/types.py` (Message, Role) + `exceptions.py`.
- **Token**: `JARVIS_LLM_API_KEY` no `.env`. Endpoint LIA UFMS Gemma 3 12B IT.

### Tools (8 registradas)
- `src/tools/registry.py`: `ToolRegistry` + `build_system_prompt(registry)`.
- `src/tools/tool_agenda.py`: `consultar_agenda`, `adicionar_evento`.
- `src/tools/tool_tasks.py`: `listar_tarefas`, `adicionar_tarefa`,
  `concluir_tarefa`.
- `src/tools/tool_rag.py`: `buscar_material_rag`.
- `src/tools/tool_materials.py`: `listar_materiais`.
- `src/tools/tool_calendar.py`: `consultar_calendario` (D-025).
- Registry global lazy via `get_registry()`.

### RAG
- **Modelo embed**: `intfloat/multilingual-e5-small` (384 dim, ~120MB).
  Carrega lazy na 1ª chamada (singleton). Prefixos `query:` / `passage:`.
- **Chunking**: Recursive Character Splitter, 800 chars / 150 overlap.
- **Vector store**: sqlite-vec (`chunk_vecs USING vec0`).
- **Threshold de relevância**: `JARVIS_RAG_DISTANCE_THRESHOLD=0.6` (cosseno).
- **Pipeline**: `src/rag/pipeline.py::ask()` async generator.

### UI v2
- **Entry**: `src/ui/app.py::run()` (chamado por `src/main.py`).
- **Página única**: `@ui.page("/")` com `ui.left_drawer` (sidebar) +
  `ui.column` (chat).
- **Tema**: `src/ui/theme.py::apply_theme()` (CSS + Inter + locale Quasar).
- **Estado**: `src/ui/state.py` (singleton: gemma, agent, session_id,
  prompt_history).
- **Componentes** (`src/ui/components/`):
  - `sidebar.py`: logo + Novo chat + Recentes + avatar
  - `chat_view.py`: título + scroll + pill input + integração agent
  - `prompt_input.py`: pill com "+" menu + ↑/↓ history
  - `tool_call_card.py`: render discreto de tool calls (expansion)
  - `date_picker.py`: helper `date_picker_ptbr` (dd/mm/aaaa + Quasar)
  - `calendar_colors.py`: paleta + `render_item_chip`
  - `calendar_month_view.py`: grid mensal 7×6
  - `calendar_mini.py`: mini-calendário sidebar do calendar_dialog
  - `calendar_wizard.py`: wizard 2 passos (Evento vs Tarefa)
- **Dialogs** (`src/ui/dialogs/`):
  - `materials_dialog.py`: upload + lista documentos
  - `calendar_dialog.py`: fullscreen com mini + filtros + grid + edit/delete
  - `tasks_list_dialog.py`: modo to-do puro (checkboxes)
  - `audit_dialog.py`: tabela tool_call_logs

### Specs SDD
- `spec/000-foundation/`: scaffold + ADRs (auditado, aprovado).
- `spec/001-core-infrastructure/`: requirements/design/tasks/audit.md.
- `spec/002-rag/`: idem.
- `spec/003-agenda/`, `spec/004-tasks/`, `spec/005-tool-calling/`,
  `spec/006-gui/`: modo MVP (auditoria diferida).
- Plano detalhado UI v2: `~/.claude/plans/melhorias-necess-rias-fancy-lollipop.md`.

### Testes (75 passed, 3 skipped)
- `tests/unit/` (23): config, logging, health, message_type, smoke_import,
  chunk, prompt, chat_service.
- `tests/integration/` (52): db_migrations, db_pragmas, db_log_tool_call,
  agenda_repo, tasks_repo, chat_repo, agent_loop, calendar_view,
  migration_002.
- `tests/integration/test_gemma_smoke.py`: 3 skipped (live_llm opt-in via
  `JARVIS_RUN_LIVE_LLM=1`).

---

## 7. Gotchas conhecidos

### Encoding em Windows
- Console PowerShell pode mostrar `?` em vez de `ç/ã/é` nos logs — é só
  visualização, o arquivo de log (`logs/jarvis-*.log`) está OK em UTF-8.
- Em arquivos `.sql`, USE UTF-8 explícito (já é, mas se editar manualmente
  cuidado).

### sqlite-vec
- Precisa `conn.enable_load_extension(True)` + `sqlite_vec.load(conn)`.
- Tabela virtual `chunk_vecs` NÃO suporta `JOIN ON FK` — fazer JOIN por
  igualdade de `chunk_id`.
- `vec_search` retorna `distance` (menor = mais relevante; ≈ cosseno).

### NiceGUI 3.x
- `@ui.page("/")` NÃO convive com chamadas de UI no escopo global.
  Todo `ui.colors`, `ui.dark_mode`, etc. precisa estar DENTRO da função da
  página.
- `nicegui_app.on_startup(_async_hook)` aceita async direto (NiceGUI await).
- Para layout fullscreen sem barra: `ui.dialog().props("maximized")`.
- `ui.expansion(value=False)` = começa fechado.
- Para iniciais em avatar: usar `ui.html('<div style="...">XY</div>')` —
  `ui.avatar` não tem prop nativa pra texto.

### Locale Quasar PT-BR
- Aplicado via `ui.add_head_html` com script JS que aguarda
  `window.Quasar.lang` ficar disponível antes de chamar
  `Quasar.lang.set({...})`.
- Sem isso, calendários ficam em inglês ("January", "Monday").

### LLM Gemma 12B
- O endpoint LIA UFMS é OpenAI-compatible mas suporte a `tools=` é
  desconhecido — usamos prompt-based JSON (D-007).
- Healthcheck timeout aumentado para 15s (default 5s era pouco).
- 401 (token inválido) NÃO re-tenta; 429 (rate-limit), 5xx, timeout RE-tentam
  3x com backoff exponencial via tenacity.
- LLM às vezes manda "amanha" sem acento mesmo com prompt em PT — por isso
  `_strip_accents` no `tool_agenda._consultar_agenda`.

### Migrations
- Schema versionado em `PRAGMA user_version` (forward-only).
- Runner em `apply_migrations(conn)` usa loop de `execute()` NÃO
  `executescript()` (esse último faz COMMIT implícito quebrando
  `BEGIN/ROLLBACK`).
- Se DB tem `user_version > max(migrations)` → `RuntimeError` (DB ahead of
  code). Sinal de que o usuário rodou versão mais nova do código em outra
  máquina.
- Para resetar: `del data\jarvis.db data\jarvis.db-wal data\jarvis.db-shm`.

### Agent loop + chat sessions
- `AgentLoop.respond(session_id=None)` é o modo "efêmero" (não persiste).
  Usado em testes e fluxos rápidos.
- `AgentLoop.respond(session_id=N)` grava cada mensagem em
  `chat_messages` para restauração via sidebar Recentes.
- `tool` role guarda metadata estruturada (tool, args, status, duration_ms)
  no `metadata_json` para restauração fiel dos cards visuais.
- `next_position()` calcula automaticamente a posição livre.

### Calendar VIEW
- `calendar_items_view` UNION ALL de events + tasks.
- Tarefas SEM `due_at` NÃO aparecem no calendário (só na "Lista de tarefas"
  pura). Intencional.
- `item_uid` formato `event:N` ou `task:N` para distinguir.
- Filtro `kinds` aplica-se SÓ a eventos (tarefas passam direto).

---

## 8. Processo SDD (resumo)

```
ENTREVISTA → SPEC (req/design/tasks) → AUDITORIA → APROVAÇÃO HUMANA → CÓDIGO
```

1. **Entrevista**: perguntas UMA por vez sobre ambiguidades, design,
   cenários de erro.
2. **Spec**: 3 arquivos em `spec/NNN-nome/`:
   - `requirements.md`: RF-xxx.x com critérios de aceitação testáveis +
     "Fora de escopo".
   - `design.md`: modelo de dados, contratos, fluxos, política de erros, DoD.
   - `tasks.md`: T-xxx.x ordenados por dependência, `[P]` para paralelismo.
3. **Auditoria**: subagente `spec-auditor` (definido em
   `.claude/agents/spec-auditor.md`) lê tudo e gera `audit.md` com
   veredito (🟢/🟡/🔴) + bloqueadores + ressalvas.
4. **Aprovação humana**: usuário diz `aprovo a spec NNN`.
5. **Código**: implementação segue `tasks.md`.

> Em **MVP mode** (UI v2 fases 4-10), a auditoria foi diferida — foi acordado
> com o usuário para acelerar entrega.

---

## 9. ADRs (decisões registradas) — quick reference

| ID | Tema |
|---|---|
| D-001 | Abordagem: Híbrida leve (bibliotecas focadas + pipeline próprio) |
| D-002 | GUI: NiceGUI |
| D-003 | Vector store: sqlite-vec |
| D-004 | Embeddings: intfloat/multilingual-e5-small |
| D-005 | PDF parser: pdfplumber |
| D-006 | Chunking: Recursive Character Splitter (800/150) |
| D-007 | Tool calling: prompt-based JSON + agent loop próprio |
| D-008 | Arquitetura: Layered + feature modules |
| D-009 | DB: sqlite3 nativo + Pydantic v2 |
| D-010 | Logging: loguru + tabela SQLite auditável |
| D-011 | Deps: uv + pyproject.toml + uv.lock + Python 3.12 |
| D-012 | Migrations: PRAGMA user_version + .sql numerados |
| D-013 | DB conn: per-op + WAL + foreign_keys + busy_timeout |
| D-014 | LLM client: AsyncOpenAI + tenacity (3 retries 5xx/timeout/429) |
| D-015 | tool_call_logs: full JSON I/O + metadata, retenção indefinida |
| D-016 | Embeddings: lazy load + indicador de progresso |
| D-017 | LLM offline: degraded mode + healthcheck + banner UI |
| D-018 | LLM streaming: dual (stream_chat + complete_chat) |
| D-019 | Testes: pirâmide unit + integration + smoke LLM opt-in |
| D-020 | chunk_vecs: vec0(chunk_id PK, embedding FLOAT[384]) 1:1 com chunks |
| D-021 | Dedupe ingest: SHA-256 do conteúdo + cascade re-ingestão |
| D-022 | RAG retrieval vazio: threshold 0.6 + prompt anti-hallucination + UI hint |
| D-023 | Prompt RAG: PT-BR + chunks numerados + citação obrigatória |
| **D-024** | **Chat sessions persistidas (migration 003 + domain/chat)** |
| **D-025** | **Calendário unificado via VIEW SQL + tool_calendar** |
| **D-026** | **UI v2 ChatGPT-style (sidebar + chat + dialogs do menu "+")** |

---

## 10. Quando algo der errado

| Problema | Verificar | Solução |
|---|---|---|
| App não sobe | logs em `logs/jarvis-*.log` | verificar `.env` (especialmente API_KEY) |
| `ModuleNotFoundError` | venv ativo? | `.venv\Scripts\python.exe ...` (não `python ...`) |
| `RuntimeError: DB user_version=X > maior migration` | DB de versão mais nova rodado em código antigo | `git pull` ou resetar DB |
| `sqlite-vec não carregou` | extensão instalada? | `uv sync` de novo; verificar `sqlite-vec` em `.venv/Lib/site-packages/` |
| LLM healthcheck timeout | rede / endpoint LIA UFMS | tentar de novo; subir em degraded mode é OK |
| Calendário em inglês | locale Quasar não aplicou | recarregar página (script JS roda no DOMContentLoaded) |
| Tabs antigos aparecem | cache do browser | Ctrl+Shift+R (hard reload) |
| ruff falhando após mudança | char `×` ou `;` na mesma linha | substituir por palavra ou separar em 2 linhas |
| pytest do agent_loop falhando | fixture `shared_db` precisa de env vars | está em `tests/integration/test_agent_loop.py::shared_db` — copia padrão |
| Acento `?` no terminal | encoding PowerShell | só visual — arquivos em UTF-8 |

---

## 11. Caminhos críticos de arquivos

```
PARA EDITAR LLM/PROMPT:
- src/tools/registry.py (build_system_prompt) — system prompt do agent
- src/rag/prompt.py (SYSTEM_PROMPT) — system prompt do RAG

PARA ADICIONAR NOVA TOOL:
- src/tools/tool_NOME.py (copiar padrão de tool_tasks.py)
- registrar em src/tools/registry.py::get_registry()

PARA NOVA MIGRATION:
- src/core/migrations/00N_NOME.sql (PRAGMA user_version = N no final)
- atualizar testes em test_db_migrations.py (esperar v=N)

PARA NOVO DIALOG NO MENU "+":
- src/ui/dialogs/NOME_dialog.py
- registrar em src/ui/app.py::index_page() dentro de chat_view.render(dialog_openers=...)

PARA MUDAR COR/FONTE:
- src/ui/theme.py (constantes COLOR_* + CSS no apply_theme)

PARA NOVA FEATURE DE DOMÍNIO:
- src/domain/NOME/{__init__,models,repo,service}.py
- migration se precisar de tabela nova
- tool se precisar ser invocável pela LLM
```

---

## 12. Contato / continuidade

Se for **outro Claude Code** lendo isto em sessão futura:
- Memórias persistentes desta sessão estão em `~/.claude/projects/.../memory/`.
- Plano original detalhado em `~/.claude/plans/melhorias-necess-rias-fancy-lollipop.md`.

Se for **outro humano** (colega de dupla):
- Documentação acima é suficiente para começar.
- Em caso de dúvida sobre arquitetura, ver `CLAUDE.md` + `decisions.md`.
- Para entender o "porquê" de algo não-óbvio: `NOTES.md`.

Boa sorte! O sistema está estável e funcional. Tudo o que falta é trabalho
humano de coleta de material e gravação de vídeo.
