# Spec 000 — Foundation — Design

## Resumo

Esta spec não introduz design de feature. Ela formaliza o **design transversal**
(arquitetura, processo, convenções) que vive em `CLAUDE.md` e em `decisions.md`.

Considere este documento um **índice** para o design transversal.

## Arquitetura

Ver [CLAUDE.md §4 — Estrutura de Diretórios](../../CLAUDE.md#4-estrutura-de-diretórios)
e [§4.1 — Regras de dependência entre camadas](../../CLAUDE.md#41-regras-de-dependência-entre-camadas).

Resumo: layered architecture com módulos por feature em `domain/`. Importações respeitam
hierarquia: `ui → tools/llm → domain/rag → core`.

## Decisões técnicas (ADRs)

| ID | Tema | Decisão |
|---|---|---|
| [D-001](../../decisions.md#d-001) | Abordagem geral | Híbrida leve |
| [D-002](../../decisions.md#d-002) | GUI | NiceGUI |
| [D-003](../../decisions.md#d-003) | Vector store | sqlite-vec |
| [D-004](../../decisions.md#d-004) | Embeddings | multilingual-e5-small (local) |
| [D-005](../../decisions.md#d-005) | PDF parser | pdfplumber |
| [D-006](../../decisions.md#d-006) | Chunking | Recursive Character Splitter (800/150) |
| [D-007](../../decisions.md#d-007) | Tool calling | Prompt-based JSON + agent loop próprio |
| [D-008](../../decisions.md#d-008) | Arquitetura | Layered + feature modules |
| [D-009](../../decisions.md#d-009) | DB access | sqlite3 nativo + Pydantic v2 |
| [D-010](../../decisions.md#d-010) | Logging | loguru + tabela `tool_call_logs` |
| [D-011](../../decisions.md#d-011) | Deps/venv | uv + pyproject.toml + uv.lock |

## Processo SDD

Ver [CLAUDE.md §5 — Processo SDD](../../CLAUDE.md#5-processo-sdd).

Diagrama de fluxo: entrevista → geração → auditoria → aprovação humana → implementação.

## Convenções de código

Ver [CLAUDE.md §6](../../CLAUDE.md#6-convenções-de-código).

## Política de erros (transversal)

Ver [CLAUDE.md §8 — Tratamento de Erros](../../CLAUDE.md#8-tratamento-de-erros-política-global).

## Variáveis de ambiente

Todas declaradas em `.env.example`. Lidas via `pydantic-settings` no
`src/core/config.py` (a ser implementado em Spec 001).

| Variável | Default | Origem |
|---|---|---|
| `JARVIS_LLM_BASE_URL` | `https://llm.liaufms.org/v1/gemma-3-12b-it` | Enunciado do trabalho |
| `JARVIS_LLM_MODEL` | `google/gemma-3-12b-it` | Enunciado |
| `JARVIS_LLM_API_KEY` | (sem default) | Token do professor |
| `JARVIS_LLM_TIMEOUT_S` | `60` | Razoável para chamadas longas |
| `JARVIS_LLM_MAX_TOKENS` | `2048` | Suficiente para respostas + tool calls |
| `JARVIS_LLM_TEMPERATURE` | `0.2` | Baixa para reduzir alucinação em RAG |
| `JARVIS_DB_PATH` | `./data/jarvis.db` | SQLite local |
| `JARVIS_EMBED_MODEL` | `intfloat/multilingual-e5-small` | D-004 |
| `JARVIS_CHUNK_SIZE` | `800` | D-006 |
| `JARVIS_CHUNK_OVERLAP` | `150` | D-006 |
| `JARVIS_RAG_TOP_K` | `5` | Default razoável |
| `JARVIS_LOG_LEVEL` | `INFO` | |
| `JARVIS_LOG_DIR` | `./logs` | |
| `JARVIS_UI_HOST` | `127.0.0.1` | Local apenas |
| `JARVIS_UI_PORT` | `8080` | |
| `JARVIS_UI_DARK` | `true` | Default escuro (moderno) |

## Modelo de dados (visão geral — detalhado em Spec 001)

```
documents       (id, title, source_path, type, ingested_at, ...)
chunks          (id, document_id, text, position, embedding BLOB)  ← sqlite-vec
events          (id, title, description, starts_at, ends_at, kind, ...)
tasks           (id, title, description, due_at, status, created_at, completed_at, ...)
tool_call_logs  (id, ts, tool_name, input_json, output_json, duration_ms, status, error)
```

## Fluxos críticos (alto nível)

### Fluxo RAG (Spec 002)
```
[arquivo PDF/TXT] → ingest → chunk → embed → store(chunks+vec)
[pergunta] → embed(query) → retrieve top_k → LLM(contexto + pergunta) → resposta
```

### Fluxo Tool Calling (Spec 005)
```
[user msg] → LLM(prompt c/ tool descriptions)
     ↓ resposta = JSON { tool, args } | { reply }
     se tool: executar → log → re-injetar resultado → LLM novamente (loop)
     se reply: devolver para UI
```

## Riscos transversais identificados

| Risco | Mitigação |
|---|---|
| Endpoint LIA UFMS instável/indisponível durante demo | Implementar retry exponencial; UI mostra erro amigável; permitir uso offline das features locais (agenda/tarefas). |
| Modelo `multilingual-e5-small` baixar lento na 1ª execução | Mostrar progresso na inicialização; documentar no README. |
| `sqlite-vec` não disponível em Windows | Validar instalação no setup; documentar no README. Fallback: NumPy brute-force seria a próxima ADR. |
| LLM retorna JSON malformado em tool calls | 1 retry com re-prompt explicando o erro (CLAUDE.md §8). Logar a falha. |
| SQLite `database is locked` ou journal corrompido | Retry com backoff (3x, CLAUDE.md §8). Em corrupção: alertar usuário e parar (sem dados, melhor falhar cedo do que continuar inconsistente). Usar modo `journal_mode=WAL` no Spec 001 para reduzir contenção. |
| Conflito de schema futuro | Documentar versão em pragma `user_version` do SQLite. |

## Critérios de pronto (DoD) para esta spec

A Spec 000 está "pronta" quando os artefatos abaixo existem **E** os portões de
aprovação foram cumpridos. As caixas refletem dois estados distintos: artefato já
produzido nesta entrega vs. etapa que depende de ação subsequente.

### Artefatos entregues (produzidos pela Spec 000)

- [x] `CLAUDE.md` criado com §1–§11.
- [x] `decisions.md` criado com D-001 a D-011.
- [x] `.claude/agents/spec-auditor.md` criado.
- [x] `.claude/settings.json` criado.
- [x] Estrutura de diretórios criada (com `__init__.py` em todos pacotes).
- [x] `pyproject.toml`, `.gitignore`, `.env.example`, `README.md` criados.
- [x] `data/README.md` criado documentando estratégia de chunking (D-006).
- [x] `audit.md` gerado pelo `spec-auditor` (em `spec/000-foundation/audit.md`).

### Etapas pós-aprovação (gates dependentes de ação humana ou subsequente)

- [x] Mantenedor humano aprovou explicitamente — sessão 2026-05-23 (chat).
- [ ] `uv sync` executado, `.venv/` criado e `uv.lock` gerado/commitado.
- [ ] Smoke test de import: `uv run python -c "import src; print(src.__version__)"`
      retorna `0.1.0` sem erro.
- [ ] `git init` + commit inicial executado (quando o usuário decidir).
