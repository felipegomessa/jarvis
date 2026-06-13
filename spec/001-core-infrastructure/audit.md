# Auditoria — Spec 001: Core Infrastructure

**Auditor**: spec-auditor
**Data**: 2026-05-23
**Spec**: spec/001-core-infrastructure/
**Versão dos arquivos**: requirements.md, design.md, tasks.md (auditados juntos)

## Veredito

- 🟡 **APROVADA COM RESSALVAS**

## Resumo executivo

A Spec 001 entrega uma infraestrutura concreta sólida: configuração tipada, conexão
SQLite com `sqlite-vec` e PRAGMAs corretos, runner de migrations forward-only, cliente
LLM async com retry e dual streaming, logging via loguru, healthcheck/degraded mode,
infraestrutura de testes em pirâmide, e tabela `tool_call_logs`. As 8 ADRs novas
(D-012 a D-019) propostas durante a entrevista estão consistentemente refletidas em
requirements/design/tasks. `pyproject.toml` já inclui `tenacity` (D-014). O `.env.example`
e a classe `Settings` cobrem exatamente as mesmas 16 variáveis. As ressalvas são pontuais
(timestamps UTC, modo de transação SQLite, classificação 4xx) e algumas merecem atenção
antes da implementação, mas não bloqueiam aprovação humana.

## A. Coerência constitucional

- [✓] **Princípios P1–P7 respeitados**
  - P1 (simplicidade): runner de migrations próprio em ~30 linhas, sem `alembic`
    (D-012); `tenacity` é uma adição pequena e justificada (D-014).
  - P2 (decisões não-voláteis): tudo novo entrou como D-012 a D-019.
  - P3 (SDD): requirements → design → tasks bem articulados.
  - P5 (logs auditáveis): RF-001.6 + helper `log_tool_call` + schema D-015.
  - P7 (reprodutibilidade): tasks T-001.16 cobre smoke import (atende ressalva
    pendente da Spec 000).
- [✓] **Sem contradição com ADRs** — As 8 ADRs novas (D-012 a D-019) estão
  literalmente implementadas: migrations versionadas (D-012, RF-001.1), conexão por
  operação com 4 PRAGMAs (D-013, RF-001.2), AsyncOpenAI+tenacity (D-014, RF-001.3),
  schema completo de `tool_call_logs` (D-015, design §1 linhas 100–113), healthcheck
  e degraded mode (D-017, RF-001.7), dual streaming (D-018, RF-001.3), pirâmide de
  testes com marker `live_llm` (D-019, RF-001.8). D-016 (lazy embedder) está
  explicitamente fora de escopo desta spec (linhas 156–158 requirements.md),
  delegado a Spec 002 — coerente.
- [✓] **Stack restrita a CLAUDE.md §3** — `tenacity` é a única adição nova ao
  pyproject vs. Spec 000, e está autorizada por D-014.

## B. Requirements.md

- [✓] **Seção "Fora de escopo" explícita** — linhas 149–158 enumeram 6 não-objetivos
  claros (parsing PDF, retrieval RAG, modelos agenda/tasks, agent loop, NiceGUI,
  carregamento real de embedder). Cobertura adequada e evita escopo difuso.
- [✓] **Critérios de aceitação testáveis** — Cada RF-001.x tem bullets `✓`
  binários e verificáveis ("Função X existe", "Aplica PRAGMA Y", "Helper Z retorna
  lastrowid"). RF-001.1 chega a citar o teste de idempotência ("re-aplicar é no-op").
- [✓] **Rastreabilidade** — RF-001.6 ↔ trabalho (logs de tool calls); RF-001.3 ↔
  enunciado (integração LLM); RF-001.1 (migrations) ↔ D-012; RF-001.4 ↔ §6 de
  CLAUDE.md (config); restante coberto por D-012 a D-019.
- [✓] **Linguagem clara** — sem termos ambíguos. Verbos checáveis ("aplica",
  "retorna", "valida", "carrega", "registra marker").
- [⚠] **RF-001.5 não impõe que `configure_logging` aceite `Settings`** —
  requirements.md linha 89 diz "expõe `configure_logging(settings)`" mas o design.md
  linha 188 implementa assinatura como `configure_logging(log_level, log_dir)`.
  Pequena divergência cosmética entre requisito e design (assinatura). Sugestão:
  alinhar — preferir `configure_logging(settings: Settings)` para consistência com o
  resto do código, ou aceitar parâmetros primitivos e documentar a chamada
  conveniente em `main.py` (`configure_logging(settings.log_level, settings.log_dir)`).
  Não bloqueia.

## C. Design.md

- [✓] **Modelo de dados explícito e válido** — design.md §1 traz DDL completo das
  5 tabelas + 5 índices. Verificação sintática:
  - `documents` (id, title, source_path UNIQUE, type CHECK, char_count, chunk_count,
    ingested_at) — válido.
  - `chunks` (id, document_id FK ON DELETE CASCADE, position, text, char_start,
    char_end, UNIQUE(document_id, position)) — válido; FK requer `foreign_keys=ON`
    (garantido por D-013).
  - `events` (id, title, description, starts_at, ends_at, kind CHECK, location,
    created_at, updated_at) — válido.
  - `tasks` (id, title, description, due_at, status CHECK, priority, created_at,
    completed_at) — válido.
  - `tool_call_logs` — bate exatamente com o schema da ADR D-015. ✓
  - Índices: 5 declarados (idx_chunks_doc, idx_events_starts_at, idx_tasks_status,
    idx_tasks_due_at, idx_tool_call_logs_ts, idx_tool_call_logs_tool) — totalizam
    6 índices, não 5 (T-001.3 e tasks §8 dizem "5 índices"). Pequena inconsistência
    numérica — ver Ressalva 1.
- [✓] **Contratos de função/API definidos** — assinaturas explícitas para
  `get_connection`, `apply_migrations`, `log_tool_call`, `Settings`, `get_settings`,
  `configure_logging`, `GemmaClient.{stream_chat, complete_chat, healthcheck,
  _request}`, `LLMHealth`/`get_health`/`set_health`. Tipos de retorno claros.
- [✓] **Fluxo de dados** — §6.1 (startup) e §6.2 (tool call logging) estão claros e
  ordenados. §6.1 inclui o passo de healthcheck e `set_health(...)`, completando o
  ciclo OFFLINE/ONLINE de D-017.
- [✓] **Regras de dependência respeitadas (CLAUDE.md §4.1)**:
  - `src/core/db.py` importa `src.core.config` — OK (core → core stdlib + lib
    externa `sqlite_vec` + `loguru`).
  - `src/llm/gemma_client.py` importa `src.core.config`, `src.llm.types`,
    `src.llm.exceptions` — OK (llm → core).
  - `src/core/health.py` é stdlib only — OK.
  - Nenhuma importação de `domain`, `ui`, `tools` em `core/`/`llm/`. ✓
- [✓] **Tratamento de erros explícito** — design.md §7 (linhas 501–512) tabela com
  8 cenários: migration falha, vec_version falha, API_KEY ausente, healthcheck
  falha, 401 durante uso, 5xx/timeout, SQLite locked, DB ahead-of-code. Coerente
  com CLAUDE.md §8 e estende com 3 cenários específicos (vec_version, ahead-of-code,
  migration). Cada um tem comportamento prescrito.
- [✓] **Decisões novas justificadas** — todas as decisões novas (retry com
  `AsyncRetrying`, transação por migration, timestamp UTC com sufixo `Z`,
  classificação de erros HTTP em 4 subclasses) decorrem das ADRs D-012 a D-019,
  todas com alternativas registradas em `decisions.md`.
- [⚠] **`apply_migrations` usa `BEGIN/COMMIT/ROLLBACK` manual com
  `isolation_level=None`** — a combinação está correta em princípio (autocommit
  + transação explícita), mas há um detalhe sutil: `conn.executescript()` em
  `sqlite3` faz `COMMIT` implícito antes de executar o script, o que pode
  **fechar a transação `BEGIN` previamente aberta**. Resultado: o rollback no
  `except` pode não desfazer o que `executescript` já executou. Ver Bloqueador 1
  e a ressalva 2 abaixo.
- [⚠] **`_request` em design.md §5.3 classifica 4xx em duas categorias mas mistura
  ordem com 5xx** — Confronto com CLAUDE.md §8 (linhas 248–256): a política manda
  retry em 5xx/timeout e NÃO em 4xx. O código (linhas 409–414) trata
  `APIStatusError` somente DENTRO do bloco retriável; isso é correto porque
  `APIStatusError` não está em `_RETRYABLE` (somente `APITimeoutError`,
  `APIConnectionError`, `RateLimitError`). Porém, `RateLimitError` (429) está em
  `_RETRYABLE` e é tecnicamente um 4xx — comportamento conflita com a regra
  literal "4xx não re-tenta". A intenção é correta (429 deve ser re-tentado), mas
  RF-001.3 (requirements §RF-001.3, bullet 6) diz "Erros 4xx (auth, validation)
  não re-tentam" sem ressalvar 429. Ver Ressalva 3.
- [⚠] **`datetime.utcnow()` no `log_tool_call`** (linha 318) e em `set_health`
  (linha 473) está **deprecado em Python 3.12** (`DeprecationWarning`). Substituir
  por `datetime.now(timezone.utc)`. Ver Ressalva 4.

## D. Tasks.md

- [✓] **Ordem por dependência** — T-001.1 (config) e T-001.2 (logging) precedem
  T-001.4 (db) que precede T-001.5 (migrations); T-001.3 (.sql) precede T-001.5;
  T-001.8 (types/exceptions) precede T-001.9 (GemmaClient); T-001.11 (conftest)
  precede T-001.13/14/15 (testes); T-001.17 (auditoria) precede T-001.18 (aprovação)
  precede T-001.19 (impl). Ordem correta.
- [✓] **`[P]` em independentes** — T-001.2, T-001.6, T-001.7, T-001.8, T-001.10,
  T-001.12 marcadas `[P]`. Verificação:
  - T-001.2 (logging) é independente de T-001.1 (config) — OK em paralelo.
  - T-001.6 (log_tool_call helper) depende do schema (T-001.3) — `[P]` aqui
    significa "paralelo com T-001.5", o que é válido (helper SQL não depende do
    runner de migrations). ✓
  - T-001.7 (health.py) é stdlib only — OK paralelo.
  - T-001.8 (types/exceptions) é independente — OK.
  - T-001.10 (re-export) depende de T-001.8 e T-001.9 — `[P]` indica paralelo
    com T-001.9? Discutível: re-exportar precisa que os símbolos existam.
    Sugestão menor: mover T-001.10 para depois de T-001.9 sem `[P]`, ou
    documentar que `[P]` aqui significa "pode editar em paralelo enquanto T-001.9
    progride". Ver Ressalva 5.
  - T-001.12 (pyproject marker) é independente — OK.
- [✓] **Cobertura RF ↔ Tasks** — tabela em tasks.md linhas 134–147 mapeia cada
  RF a 1+ tasks de implementação e 1+ tasks de teste. Verificação manual confirma:
  RF-001.1 → T-001.3+5+14 ✓, RF-001.2 → T-001.4+14 ✓, RF-001.3 → T-001.9+15 ✓,
  RF-001.4 → T-001.1+13 ✓, RF-001.5 → T-001.2+13 ✓, RF-001.6 → T-001.3+6+14 ✓,
  RF-001.7 → T-001.7+9 ✓ (T-001.7 cria estado, T-001.9 contém healthcheck;
  observação: nenhuma task de teste específica para health.py — ver Ressalva 6),
  RF-001.8 → T-001.11+12+13+14+15 ✓, RF-001.9 → T-001.8+10 ✓.
- [✓] **Tasks de teste presentes** — T-001.13 (unit: config, logging), T-001.14
  (integration: migrations, pragmas, log_tool_call), T-001.15 (smoke live LLM),
  T-001.16 (smoke import). Cobre os 5 componentes implementados.
- [✓] **Tasks de logging** — T-001.2 implementa o sink; T-001.6 implementa o
  helper de tool call. Coerente com D-010.
- [✓] **Granularidade adequada** — 19 tasks bem dimensionadas: a maior (T-001.9
  GemmaClient) é um único arquivo de ~80 linhas; a menor (T-001.12 marker) é uma
  linha de pyproject. Não há tasks gigantes nem micro-tasks de ruído.
- [⚠] **Sem task explícita para `live_llm` skip-by-default hook** — T-001.12 diz
  "Hook em `conftest.py` para skip automático se `JARVIS_RUN_LIVE_LLM != '1'`"
  como bullet secundário dentro de T-001.12 (que é sobre o marker no pyproject).
  Sugestão: separar em `T-001.12.bis` ou tornar o bullet explícito como sub-item
  de T-001.11 (que cria o conftest.py). Não bloqueia.

## E. Cobertura de cenários de erro

> design.md §7 estende CLAUDE.md §8 com cenários específicos de infra.
> Confronto literal:

- [✓] **Falha de I/O externo (LLM, rede)** — design.md §7 linhas 510–511: "LLM
  5xx/timeout — 3 retries via tenacity; após esgotar, LLMServerError/LLMTimeoutError
  propaga". Coerente com CLAUDE.md §8 ("2 retries com backoff exponencial" —
  design especifica 3, justificado por D-014). Reportar pequena divergência
  numérica (2 em CLAUDE.md vs. 3 em D-014/design): D-014 prevalece sobre §8
  porque é mais recente e específico. Recomenda-se sincronizar CLAUDE.md §8 →
  "3 retries" para evitar confusão futura. Ver Ressalva 7.
- [✓] **Entrada malformada vinda da LLM (JSON inválido)** — fora de escopo desta
  spec (RF-001.3 só estabelece o cliente; parsing JSON de tool calls é Spec 005).
  Aceita pelas linhas 154–155 de requirements.md. ✓
- [✓] **Estado inconsistente do DB** — design.md §7 cobre:
  - SQLite locked → `busy_timeout=3000` (D-013). ✓
  - Migration falha → BEGIN/ROLLBACK + log + re-raise. ✓ (mas ver ressalva
    técnica sobre `executescript`).
  - DB ahead-of-code → erro fatal. ✓
- [✓] **Cenários de domínio** — N/A para Spec 001 (sem entidades de domínio).
  Delegado às Specs 003/004 (agenda, tasks).

## F. Testabilidade

- [✓] **Funções puras testáveis sem mocks pesados** — `Settings` testa-se com
  variáveis de ambiente; `configure_logging` é função estática; `apply_migrations`
  testa-se contra `tmp_path` (T-001.14); `log_tool_call` idem. Excelente.
- [✓] **Componentes que dependem de LLM têm camada de abstração** — `GemmaClient`
  é injetado via construtor e o fixture `fake_llm` (T-001.11) é um stub completo.
  RF-001.8 explicitamente prevê isso. Spec respeita D-019.
- [✓] **≥1 task de teste por componente novo** — config (T-001.13), logging
  (T-001.13), db.connection (T-001.14), db.migrations (T-001.14), db.log_tool_call
  (T-001.14), GemmaClient (T-001.15 opt-in + fake_llm via conftest). Cobertura
  satisfatória para a pirâmide de D-019.
- [⚠] **`health.py` não tem teste dedicado** — RF-001.7 critério "estado é
  singleton acessível por toda a app" é facilmente testável (get/set, thread-safe
  via Lock). Sugestão de task adicional T-001.13bis ou item em T-001.13. Ver
  Ressalva 6.

## Bloqueadores (precisam ser resolvidos antes da aprovação humana)

1. **`executescript` faz COMMIT implícito antes de executar — quebra a transação
   `BEGIN/ROLLBACK`** *(design.md §4.2, linhas 280–289)*. Em Python `sqlite3`,
   `Connection.executescript(sql)` chama `COMMIT` implicitamente antes do script
   e depois processa o script com gerenciamento próprio. Resultado: o `BEGIN`
   na linha 281 é encerrado *antes* do script rodar, e o `ROLLBACK` na linha 287
   pode não desfazer DDL que já foi auto-commitada dentro do `executescript`.
   Para SQLite, DDL (CREATE TABLE) **é** transacional, mas o problema é que o
   COMMIT prematuro de `executescript` impede que o `BEGIN` explícito proteja o
   bloco inteiro. **O que mudar**: ou (a) usar `conn.execute(sql)` repetidamente
   após `split` por `;` (mais controle), ou (b) usar `conn.execute("BEGIN")`
   seguido de `for stmt in sql.split(";"): conn.execute(stmt)`, ou (c) confirmar
   pela documentação Python que o comportamento desejado é alcançado e
   acrescentar comentário no código. A solução mais simples é (b): substituir
   `conn.executescript(sql)` por um loop que executa statement por statement
   dentro da mesma transação aberta. Adicionar teste de integração que injeta
   um SQL propositalmente quebrado (segundo statement) e verifica que o
   primeiro statement **não** persistiu — esse é o teste real de atomicidade.
   *Onde mudar*: `spec/001-core-infrastructure/design.md` §4.2 (substituir
   `executescript` por loop manual) e `spec/001-core-infrastructure/tasks.md`
   T-001.5 (adicionar bullet "teste de atomicidade: SQL parcialmente válido →
   tabela não criada").

## Ressalvas (não bloqueiam, mas recomenda-se endereçar)

1. **Inconsistência numérica de índices** — design.md §1 declara 6 índices
   (`idx_chunks_doc`, `idx_events_starts_at`, `idx_tasks_status`,
   `idx_tasks_due_at`, `idx_tool_call_logs_ts`, `idx_tool_call_logs_tool`), mas
   `tasks.md` T-001.3 e design.md §8 dizem "5 índices". *Onde mudar*:
   `spec/001-core-infrastructure/tasks.md` T-001.3 ("+ 5 índices" → "+ 6
   índices") e `spec/001-core-infrastructure/design.md` §8 linha 522
   ("5 tabelas + 5 índices" → "5 tabelas + 6 índices").

2. **`apply_migrations` deveria validar `current > max(arquivos)` antes do loop**
   *(tasks.md T-001.5 já menciona isso, mas o pseudocódigo do design.md §4.2 não
   implementa)*. *Onde mudar*: `spec/001-core-infrastructure/design.md` §4.2
   acrescentar antes do `for f in pending:`:
   ```python
   max_available = max((int(p.name.split("_",1)[0]) for p in MIGRATIONS_DIR.glob("*.sql")), default=0)
   if current > max_available:
       raise RuntimeError(f"DB version {current} > max migration {max_available}")
   ```

3. **Classificação 4xx vs 429** — design.md §5.3 retém `RateLimitError` (429,
   tecnicamente 4xx) em `_RETRYABLE`, mas RF-001.3 (requirements.md linhas 66–67)
   diz "Erros 4xx (auth, validation) não re-tentam" sem ressalvar 429. O
   comportamento do código é o correto. *Onde mudar*: ajustar RF-001.3 para
   "Erros 4xx **exceto 429 (rate-limit)** não re-tentam" ou similar. CLAUDE.md
   §8 também merece nota.

4. **`datetime.utcnow()` deprecado em Python 3.12** — substituir em:
   - `design.md` linha 318 (`log_tool_call`): `datetime.now(timezone.utc).isoformat(...)`.
   - `design.md` linha 473 (`set_health`): `datetime.now(timezone.utc)`.
   Sem isso, o código gerará `DeprecationWarning` toda inserção. *Onde mudar*:
   `spec/001-core-infrastructure/design.md` §4.3 e §5.4 (importar
   `from datetime import datetime, timezone`).

5. **T-001.10 marcada `[P]` mas depende de T-001.8 e T-001.9** — o re-export do
   `__init__.py` só faz sentido depois que os símbolos existem. Sugestão:
   manter `[P]` se o significado for "pode ser escrito em paralelo, com
   placeholders, e ajustado quando T-001.9 estabilizar", mas explicitar em
   comentário. *Onde mudar*: `spec/001-core-infrastructure/tasks.md` T-001.10
   (acrescentar nota).

6. **Sem task explícita de teste para `health.py`** — RF-001.7 critério "estado
   singleton acessível" é trivial mas testável (3–5 linhas). *Onde mudar*:
   adicionar a T-001.13: `tests/unit/test_health.py` — `get_health()` retorna
   UNKNOWN inicial; `set_health("ONLINE")` reflete; thread-safety básica
   (`threading.Thread × 10` chamando `set_health` e `get_health` em loop sem
   raise).

7. **Divergência de número de retries entre CLAUDE.md §8 e D-014/design** —
   CLAUDE.md §8 diz "2 retries", D-014 e design.md §7 dizem "3 retries". D-014
   é a fonte autoritativa; convém atualizar CLAUDE.md §8 para refletir. *Onde
   mudar*: `CLAUDE.md` §8 linha 250 ("Tentar 2 retries" → "Tentar 3 retries").
   Pode ser tratado como melhoria fora desta spec.

8. **Pequena inconsistência de assinatura: `configure_logging(settings)` em
   requirements vs. `configure_logging(log_level, log_dir)` em design** — Ver
   item B (⚠). Alinhar para a forma escolhida.

## Observações adicionais

**Pontos positivos**:

- A entrevista de Spec 001 produziu 8 ADRs limpas e bem fundamentadas (D-012 a
  D-019), cobrindo precisamente os pontos em aberto da Spec 000.
- `pyproject.toml` já contém `tenacity>=8.5.0` conforme D-014 — não é uma
  promessa, está commitado.
- A coerência `.env.example` ↔ `Settings` é absoluta: 16 variáveis em cada
  lado, mesma ordem semântica, mesmos defaults. Verificado linha-por-linha.
- Schema SQLite em design.md §1 é sintaticamente válido (CREATE TABLE com
  constraints corretas, índices nomeados, FK com `ON DELETE CASCADE`, CHECKs
  com listas de literais).
- O `complete_chat` retorna `""` em vez de `None` se `message.content` for
  None — defensivo e correto para o agent loop downstream.
- `LLMServerError`/`LLMTimeoutError` separados (em vez de uma única exceção)
  facilita o tratamento granular na UI da Spec 006.
- `tests/conftest.py` com `fake_llm` é o padrão certo para que Specs 002–6
  não dependam do endpoint real em CI/local.
- D-019 (pirâmide com smoke opt-in) está perfeitamente refletido em T-001.11
  a T-001.15.

**Sugestões para evolução** (não acionáveis nesta spec):

- Quando Spec 005 chegar, considerar acrescentar coluna `agent_loop_step
  INTEGER` em `tool_call_logs` para correlacionar tool calls sequenciais de
  uma mesma conversa (extensão via migration 002).
- O fixture `fake_llm` poderia, em uma migration futura, evoluir para um
  "scripted LLM" que aceita uma sequência de respostas e levanta erro se a
  Spec X consumir mais do que registrou — útil para garantir determinismo de
  tests integration de agent loop.
- Considerar adicionar um hook `PostToolUse` em `.claude/settings.json` que
  roda `ruff check` em arquivos `.py` modificados, eliminando a ressalva 3 da
  Spec 000.

**Veredito final**: A spec é tecnicamente sólida, com 1 bloqueador real
(comportamento de `executescript` vs. transação manual) que precisa ser
endereçado para garantir atomicidade real das migrations, e 8 ressalvas
menores. Recomenda-se que o mantenedor humano endereçe o Bloqueador 1
(crítico: integridade do DB em erro parcial de migration) e a Ressalva 4
(`datetime.utcnow()` deprecado) antes da aprovação canônica `aprovo a spec
001`; as demais podem ser absorvidas durante a implementação.
