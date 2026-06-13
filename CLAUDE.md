# CLAUDE.md — Constituição do Projeto JARVIS Acadêmico

> Este arquivo é a **constituição** do projeto. Toda decisão arquitetural, padrão de código
> e processo aqui descritos têm precedência sobre preferências individuais ou padrões da
> indústria. Mudanças nesta constituição exigem registro em [decisions.md](decisions.md)
> e aprovação explícita do mantenedor humano.

---

## 1. Visão do Projeto

**JARVIS Acadêmico** é um assistente pessoal para estudantes que integra:

- **RAG** (Retrieval-Augmented Generation) sobre materiais de estudo (PDFs, textos, anotações).
- **Tool Calling** com loop agentivo onde a LLM decide quais ferramentas chamar.
- **LLM Gemma 12B** via endpoint OpenAI-compatível da LIA UFMS.

**Escopo do Trabalho 1** (esta entrega): funcionalidades 3.1 (consulta a materiais via RAG),
3.2 (agenda acadêmica) e 3.3 (lista de tarefas) + tool calling + GUI moderna.

**Escopo do Trabalho 2** (entrega futura): funcionalidade 3.4 (planejamento de estudos),
melhorias de aprendizado interativas, avaliação ≥10 perguntas, análise de erros (≥3 falhas).

**Contexto**: Trabalho acadêmico em duplas, sem fins comerciais. Será avaliado e o grupo
**deve conseguir explicar todo o código**.

---

## 2. Princípios

P1. **Simplicidade explícita** — Preferir bibliotecas pequenas e código próprio a frameworks
   pesados (LangChain, etc.). Implementar RAG, embeddings, tool calling de forma que o
   grupo possa explicar cada linha. Ver [D-001](decisions.md#d-001).

P2. **Decisões não-voláteis** — Toda decisão técnica vai em `decisions.md` (formato ADR).
   Trabalho continua em outra máquina/sessão sem perda de contexto.

P3. **SDD (Spec-Driven Development)** — Nada é implementado sem `spec/NNN-name/` aprovado.
   Ver [§5 Processo SDD](#5-processo-sdd).

P4. **Auditoria obrigatória** — Toda spec passa pelo subagente `spec-auditor` antes da
   aprovação humana. Ver [§5.3](#53-auditoria-pelo-subagente).

P5. **Logs auditáveis** — Toda chamada de tool é persistida em tabela SQLite com
   ferramenta, entrada, saída, duração, status. Ver [D-010](decisions.md#d-010).

P6. **Português é o idioma do usuário final** — UI, mensagens da LLM, dataset são em PT-BR.
   Código, comentários técnicos e docs internas podem ser em inglês ou português.

P7. **Reprodutibilidade** — Setup em máquina nova com `uv sync` instala tudo. Lockfile
   versionado. Ver [D-011](decisions.md#d-011).

---

## 3. Stack Técnica (Resumo)

| Camada | Tecnologia | ADR |
|---|---|---|
| Linguagem / Python | 3.12 | [D-011](decisions.md#d-011) |
| Deps / Venv | uv + pyproject.toml + uv.lock | [D-011](decisions.md#d-011) |
| LLM | Qwen2.5-14B-Instruct-AWQ via endpoint LIA UFMS (OpenAI-compatible). Antes Gemma 12B — migrado em 2026-06-13 (LIA aposentou o Gemma); classe `GemmaClient` mantida por compat. | [D-028](decisions.md#d-028) |
| LLM client | `openai` AsyncOpenAI + dual streaming + retries via `tenacity` | [D-014](decisions.md#d-014), [D-018](decisions.md#d-018) |
| Tool Calling | Prompt-based JSON + agent loop próprio | [D-007](decisions.md#d-007) |
| Embeddings | `intfloat/multilingual-e5-small` via sentence-transformers | [D-004](decisions.md#d-004) |
| Vector store | `sqlite-vec` (extensão SQLite) | [D-003](decisions.md#d-003) |
| DB | SQLite via `sqlite3` nativo, conexão per-operação, WAL + foreign_keys | [D-009](decisions.md#d-009), [D-013](decisions.md#d-013) |
| Migrations | PRAGMA user_version + arquivos .sql numerados (forward-only) | [D-012](decisions.md#d-012) |
| Tool call logs | Tabela SQLite com full JSON I/O + metadados | [D-010](decisions.md#d-010), [D-015](decisions.md#d-015) |
| PDFs | `pdfplumber` | [D-005](decisions.md#d-005) |
| Chunking | Recursive Character Splitter (~800/150) | [D-006](decisions.md#d-006) |
| Modelos | Pydantic v2 | [D-009](decisions.md#d-009) |
| Config | `pydantic-settings` + `.env` (16 vars JARVIS_*) | — |
| GUI | NiceGUI | [D-002](decisions.md#d-002) |
| Logging | loguru (console + arquivo rotativo diário) | [D-010](decisions.md#d-010) |
| Testes | pytest + pytest-asyncio, pirâmide unit + integration + smoke LLM opt-in | [D-019](decisions.md#d-019) |
| Lint / Format | ruff | — |
| Type check | mypy (não-estrito) | — |
| Healthcheck LLM | Startup ping → estado ONLINE/OFFLINE → banner UI (degraded mode) | [D-017](decisions.md#d-017) |
| Embed lifecycle | Lazy load (1ª chamada) + indicador de progresso | [D-016](decisions.md#d-016) |
| Chat sessions | Persistidas em SQLite (chat_sessions + chat_messages) | [D-024](decisions.md#d-024) |
| Calendário unificado | VIEW SQL `calendar_items_view` (events ∪ tasks) | [D-025](decisions.md#d-025) |
| UI v2 | ChatGPT-style: sidebar Recentes + chat central pill + menu "+" + dialogs | [D-026](decisions.md#d-026) |
| Locale Quasar | PT-BR via `ui.add_head_html` com `Quasar.lang.set({...})` | [D-026](decisions.md#d-026) |

---

## 4. Estrutura de Diretórios

```
projeto/
├── CLAUDE.md                       # Esta constituição
├── README.md                       # Visão geral, setup, demo
├── decisions.md                    # ADRs (registro não-volátil de decisões)
├── pyproject.toml                  # uv project config
├── uv.lock                         # Lockfile (commitado)
├── .env.example                    # Template de variáveis (commitado)
├── .env                            # Variáveis reais (NÃO commitado)
├── .gitignore
├── .claude/
│   ├── agents/
│   │   └── spec-auditor.md         # Subagente auditor
│   ├── skills/                     # Skills sob demanda (vazio inicialmente)
│   └── settings.json               # Permissões/hooks
├── spec/
│   ├── 000-foundation/             # Decisões transversais (atalho para CLAUDE.md+decisions.md)
│   ├── 001-core-infra/             # DB schema, LLM client, logging, config
│   ├── 002-rag/                    # Funcionalidade 3.1
│   ├── 003-agenda/                 # Funcionalidade 3.2
│   ├── 004-tasks/                  # Funcionalidade 3.3
│   ├── 005-tool-calling/           # 5+ tools + agent loop
│   └── 006-gui/                    # NiceGUI frontend
├── src/
│   ├── core/                       # config, db (4 migrations), logging, health
│   ├── llm/                        # gemma_client, agent (com session_id opcional)
│   ├── rag/                        # ingest, chunk, embed, retrieve, prompt, populate
│   ├── domain/
│   │   ├── agenda/                 # models, repo, service (3.2)
│   │   ├── tasks/                  # models, repo, service (3.3)
│   │   ├── chat/                   # models, repo, service (D-024 - sessões persistidas)
│   │   └── calendar_view/          # service (D-025 - VIEW unificada eventos+tarefas)
│   ├── tools/                      # registry + 10 tools em tool_*.py (incl. tool_calendar)
│   ├── ui/                         # UI v2 ChatGPT-style (D-026)
│   │   ├── theme.py                # CSS global + Inter + locale Quasar PT-BR
│   │   ├── state.py                # singleton: gemma, agent, session_id, prompt_history
│   │   ├── app.py                  # @ui.page("/") com left_drawer + chat central
│   │   ├── components/             # sidebar, chat_view, prompt_input, tool_call_card,
│   │   │                           #   date_picker, calendar_colors, calendar_month_view,
│   │   │                           #   calendar_mini, calendar_wizard
│   │   └── dialogs/                # materials, calendar (unificado), tasks_list, audit
│   └── main.py
├── tests/
│   ├── unit/
│   └── integration/
└── data/                           # Dataset RAG (≥10 documentos acadêmicos — pendente)
```

### 4.1 Regras de dependência entre camadas

- `ui/` pode importar de `domain/`, `tools/`, `llm/`, `rag/`, `core/`.
- `tools/` pode importar de `domain/`, `rag/`, `core/`.
- `llm/` pode importar de `tools/` (para o agent loop) e `core/`.
- `rag/` pode importar de `core/`.
- `domain/` pode importar apenas de `core/`.
- `core/` não importa de nada interno (apenas stdlib + libs externas).
- **Importações circulares são proibidas**.

---

## 5. Processo SDD (Spec-Driven Development)

> Esta seção é normativa. Não pode ser ignorada.

Cada funcionalidade nova vive em `spec/NNN-nome-feature/` com **três arquivos obrigatórios**:

| Arquivo | Conteúdo |
|---|---|
| `requirements.md` | Requisitos funcionais, critérios de aceitação, **fora de escopo** explícito. |
| `design.md` | Decisões técnicas, contratos de API/funções, modelo de dados, fluxos. |
| `tasks.md` | Tarefas ordenadas por dependência, com marcação de paralelismo `[P]`. |

### 5.1 Fluxo

```
┌────────────────────────────┐
│ 1. Entrevista detalhada    │   Perguntas UMA por vez sobre:
│    com o mantenedor humano │     - Ambiguidades nos requisitos
│                            │     - Decisões de design não documentadas
│                            │     - Cenários de erro não cobertos
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│ 2. Geração da Spec         │   requirements.md + design.md + tasks.md
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│ 3. Auditoria automática    │   Subagente `spec-auditor` valida:
│    pelo spec-auditor       │     - Conflitos com CLAUDE.md/decisions.md
│                            │     - Falhas, gaps, ambiguidades
│                            │     - Cobertura de cenários de erro
└──────────────┬─────────────┘
               │ ✅ Aprovada
               ▼
┌────────────────────────────┐
│ 4. Aprovação do mantenedor │   Humano lê o relatório do auditor + spec
│    humano (você)           │   e aprova explicitamente.
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│ 5. Implementação           │   Código segue tasks.md em ordem.
│                            │   Testes + logs + tratamento de erros.
└────────────────────────────┘
```

### 5.2 Entrevista (passo 1)

**Regra absoluta**: **UMA pergunta por vez**, com opções de múltipla escolha e
**recomendação justificada** do agente.

Categorias de perguntas (cobrir todas antes de gerar a spec):

1. **Ambiguidades nos requisitos** — o que o trabalho/usuário pede deixa em aberto?
2. **Decisões de design não documentadas** — modelo de dados, contratos, fronteiras.
3. **Cenários de erro não cobertos** — falhas externas, edge cases, recovery.

As respostas alimentam a spec. Decisões com impacto transversal são promovidas para
`decisions.md` (novo ADR).

### 5.3 Auditoria pelo subagente

O subagente `spec-auditor` (ver [.claude/agents/spec-auditor.md](.claude/agents/spec-auditor.md))
recebe a spec recém-gerada e produz um **relatório estruturado** verificando:

- ✓ Coerência com `CLAUDE.md` (esta constituição).
- ✓ Coerência com `decisions.md` (ADRs já aprovados).
- ✓ Completude (todos os critérios de aceitação cobertos por tasks).
- ✓ Tratamento de erros explícito.
- ✓ Sem violações das regras de dependência entre camadas (§4.1).
- ✓ Testabilidade (tasks de teste presentes).

O relatório vem em `spec/NNN-nome/audit.md`. Se houver **bloqueadores**, a spec é
revisada antes de submeter à aprovação humana.

### 5.4 Aprovação humana

**Sem aprovação explícita do mantenedor humano, o código NÃO é escrito**. A frase
de aprovação canônica é: `aprovo a spec NNN`.

### 5.5 Mudanças na spec após aprovação

Mudanças significativas exigem nova rodada de auditoria. Mudanças cosméticas
(typo, clareza) podem ser feitas direto e mencionadas no commit.

---

## 6. Convenções de Código

- **Nomes**: snake_case para funções/variáveis, PascalCase para classes, UPPER_SNAKE
  para constantes.
- **Imports**: `ruff` configura ordenação (stdlib → terceiros → local).
- **Type hints obrigatórios** em funções públicas. Privadas (`_func`) são opcionais.
- **Docstrings**: em funções/classes públicas, formato breve (1–3 linhas).
- **Comentários**: explicar o **PORQUÊ**, não o **O QUÊ**. Código óbvio não recebe
  comentário.
- **Erros**: sempre tratados — silencioso é proibido. Logs em nível apropriado
  (`logger.error` para falhas, `logger.warning` para degradações).
- **Async**: handlers da NiceGUI e chamadas ao LLM são `async`. Operações CPU-bound
  (embeddings) rodam em `asyncio.to_thread` ou similar para não bloquear o event loop.

---

## 7. Testes

- **Unit**: lógica pura (chunking, parsing de JSON da LLM, validação Pydantic).
- **Integration**: repositórios contra SQLite real (em arquivo temporário),
  smoke test do LLM client (opcional, depende da disponibilidade do endpoint).
- **Cobertura mínima**: critérios de aceitação de cada spec devem ter teste correspondente
  (não é cobertura de linhas, é cobertura de critério).

---

## 8. Tratamento de Erros (Política Global)

| Cenário | Política |
|---|---|
| LLM API timeout / 5xx / 429 (rate limit) | 3 retries com backoff exponencial 1→8s (via tenacity, ver D-014). Falhou: mostrar erro amigável na UI; logar em `error`. 4xx exceto 429 (auth/validation) não re-tentam — propagam como `LLMAuthError`/`LLMRequestError`. |
| LLM retorna JSON malformado para tool call | Tentar 1 reparo via re-prompt explicando o erro. Falhou: responder ao usuário com mensagem de fallback. |
| Tool execution erro | Capturar exceção, registrar em `tool_call_logs` com `status='error'`, retornar mensagem de erro para o agent loop continuar. |
| PDF corrompido / sem texto extraível | Skipar arquivo, logar `warning`, continuar ingestão dos outros. |
| Embedding model não baixou | Erro fatal de inicialização — instrução clara no README/UI. |
| SQLite locked | Retry com backoff (até 3x). |
| Retrieval vazio (nenhum chunk relevante) | LLM responde "não encontrei nada no material" em vez de alucinar. |

---

## 9. IAs e Ferramentas Usadas no Desenvolvimento

(será mantida atualizada no README; lista mínima conforme exigência do trabalho)

- **Claude Code** (Anthropic) — desenvolvimento assistido, geração de boilerplate,
  revisões.
- Outras ferramentas serão listadas no README à medida que forem usadas.

---

## 10. Checklist da Entrega (Trabalho 1)

- [x] Funcionalidades 3.1 (RAG), 3.2 (Agenda), 3.3 (Tarefas) funcionais.
- [x] ≥5 tools com tool calling decidido pela LLM (na verdade entregamos 10).
- [x] Logs estruturados de cada tool call (`tool_call_logs`).
- [ ] Dataset em `/data` com ≥10 documentos acadêmicos. **(pendente — entrega humana)**
- [x] Documentação do dataset: origem, tipo, limitações, chunking ([data/README.md](data/README.md)).
- [x] README com setup + placeholder de IAs usadas.
- [ ] Vídeo demo ≤3 min (arquitetura + sistema funcionando). **(pendente)**
- [ ] Repositório GitHub. **(pendente — `git init` + push)**

Diferenciais entregues (bônus de até 2 pontos):

- [x] GUI moderna (NiceGUI tema escuro, 5 tabs polidas).
- [x] Auditoria de tool calls consultável pela própria UI (tab "Auditoria").
- [x] Processo SDD com 23 ADRs e auditor automático (qualidade de engenharia).

> Status detalhado: ver [STATUS.md](STATUS.md).

---

## 11. Como continuar este projeto em outra sessão

1. `git clone` o repositório.
2. Ler `CLAUDE.md` (este arquivo) e `decisions.md` (todas as decisões aprovadas).
3. Ver `spec/` para entender o estado de cada feature.
4. `uv sync` para criar venv e instalar deps.
5. `cp .env.example .env` e preencher o token.
6. Continuar a partir do TODO atual (ver com o mantenedor humano).
