# Spec 007 — Melhorias de Aprendizado — Design

## Visão geral

Duas funcionalidades sobre o material já indexado:

1. **Prova eletrônica** (interativa): `gerar → responder → corrigir → nota 0–10`.
2. **Dificuldades + plano de estudos**: agrega o desempenho por tópico, recomenda
   revisão (RAG) e monta um plano que pode virar tarefas/eventos na agenda.

### Arquitetura e camadas (§4.1)

```
src/domain/learning/        # PURO (importa só core/)
    models.py               # Quiz, Question, Attempt, Answer, TopicScore, DifficultyReport, StudyPlan
    repo.py                 # CRUD recebendo conn (D-013)
src/learning/               # NOVO módulo de orquestração (importa core, domain, rag, llm)
    generator.py            # gera questões (LLM) a partir dos chunks dos documentos
    grader.py               # corrige MC (determinístico) + dissertativa (LLM-juiz) + nota
    coach.py                # dificuldades por tópico + plano de estudos (RAG + agenda)
src/rag/retrieve.py         # + get_document_chunks() (leitura por documento — Falha 4)
src/tools/tool_learning.py  # tools: gerar_prova, corrigir_prova, identificar_dificuldades,
                            #        montar_plano_estudos, ler_documento
src/ui/dialogs/exam.py      # fluxo interativo (4 passos) + entrada no menu "+"
```

**Por que `learning/` é um módulo novo (e não cabe em `domain/` nem `tools/`)**: a
orquestração precisa de **LLM + RAG**, mas `domain/` só pode importar `core/` e
`tools/` não pode importar `llm/` (evita o ciclo `llm/agent ↔ tools/registry`). A
camada `learning/` pode importar `core`, `domain`, `rag`, `llm`. **Não há ciclo**:
`llm/gemma_client.py` importa apenas `core` + `llm/{exceptions,types}` (verificado),
nunca `tools/` nem `agent`.

**Como `learning/` (e as tools) obtêm o `GemmaClient` — sem violar §4.1**
(resolve o Bloqueador 1 da auditoria):

- O contrato atual de handler é `await tool_def.handler(args)` (`agent.py:216`) —
  handlers recebem **só `args`**; o `AppState.gemma` mora em `src/ui/state.py` e
  `tools/` **não pode** importar `ui/`. Portanto a tool **não** recebe o client por
  argumento nem o lê do estado da UI.
- **Mecanismo adotado — client default no pacote `llm/`**: novo
  `src/llm/client.py` expõe `set_default_client(c: GemmaClient)` e
  `get_default_client() -> GemmaClient` (singleton de processo, no estilo de
  `get_settings`/`get_embedder`/`get_registry`). O **boot** chama
  `set_default_client(gemma)` em **`src/ui/app.py`** (onde o `GemmaClient` é criado
  no startup, linha ~36, junto de `healthcheck`/`set_clients`) — **não** em
  `main.py` (que só faz `run()`).
- As funções de `learning/*` aceitam `gemma: GemmaClient | None = None` e fazem
  `gemma = gemma or get_default_client()`. Assim: a **UI** injeta `state.gemma`
  explicitamente; os **testes** injetam um fake (D-019); o **caminho via tool** usa
  o client default.
- `tools/tool_learning.py` importa **apenas `learning/`** (chama
  `learning.generate_quiz(...)` etc.) — **não importa `llm/` nem `ui/`**. A cadeia
  fica `tools → learning → llm/gemma_client`: `tools/` continua sem importar `llm/`
  diretamente (§4.1 preservado **literalmente**), e não há ciclo (gemma_client não
  importa tools).

Regra a registrar em **D-030** e em CLAUDE.md §4.1: `learning/` ⊂ {core, domain,
rag, llm}; importado por `ui/` e `tools/`. `tools/` pode importar `learning/`.

## 1. Migration 005 — `src/core/migrations/005_learning.sql`

```sql
-- Provas geradas a partir de materiais
CREATE TABLE quizzes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'ready',  -- ready | completed
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Documentos-fonte da prova (N:N) — escolha de "vários documentos"
CREATE TABLE quiz_documents (
    quiz_id     INTEGER NOT NULL REFERENCES quizzes(id)   ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (quiz_id, document_id)
);

CREATE TABLE quiz_questions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id            INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    position           INTEGER NOT NULL,
    type               TEXT    NOT NULL,           -- 'mc' | 'open'
    prompt             TEXT    NOT NULL,
    options_json       TEXT,                       -- MC: JSON array de 4 strings
    correct_index      INTEGER,                    -- MC: 0..3
    answer_key         TEXT,                       -- open: rubrica/pontos esperados
    topic              TEXT    NOT NULL DEFAULT '',
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    source_chunk_id    INTEGER REFERENCES chunks(id)    ON DELETE SET NULL,
    max_points         REAL    NOT NULL DEFAULT 1.0
);
CREATE INDEX idx_quiz_questions_quiz ON quiz_questions(quiz_id);

CREATE TABLE quiz_attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id     INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    started_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    score       REAL,                              -- 0..10 (NULL enquanto em curso)
    status      TEXT    NOT NULL DEFAULT 'in_progress'  -- in_progress | graded
);
CREATE INDEX idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);

CREATE TABLE quiz_answers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id    INTEGER NOT NULL REFERENCES quiz_attempts(id)  ON DELETE CASCADE,
    question_id   INTEGER NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    response      TEXT    NOT NULL DEFAULT '',
    awarded_points REAL,
    is_correct    INTEGER,                         -- MC: 0/1; open: NULL
    feedback      TEXT
);
CREATE INDEX idx_quiz_answers_attempt ON quiz_answers(attempt_id);

PRAGMA user_version = 5;
```

> Nota de migração (D-012): forward-only. Atenção ao `sqlite3.executescript` +
> `PRAGMA foreign_keys` (ver `jarvis_gotchas` — aplicar pragmas fora do script).

## 2. Modelos — `src/domain/learning/models.py`

```python
QuestionType = Literal["mc", "open"]

class Question(BaseModel):
    id: int | None = None
    type: QuestionType
    prompt: str
    topic: str = ""
    options: list[str] | None = None      # MC
    correct_index: int | None = None      # MC
    answer_key: str | None = None         # open
    source_document_id: int | None = None
    source_chunk_id: int | None = None
    max_points: float = 1.0
    # validator: MC exige options(len==4)+correct_index∈[0..3]; open exige answer_key

class Quiz(BaseModel):
    id: int | None = None
    title: str
    documents: list[int]                  # ≥1 document_id
    questions: list[Question] = []
    status: str = "ready"

class Answer(BaseModel):
    question_id: int
    response: str = ""
    awarded_points: float | None = None
    is_correct: bool | None = None
    feedback: str | None = None

class Attempt(BaseModel):
    id: int | None = None
    quiz_id: int
    score: float | None = None
    status: str = "in_progress"
    answers: list[Answer] = []

class TopicScore(BaseModel):
    topic: str
    earned: float
    possible: float
    @property
    def ratio(self) -> float: ...         # earned/possible

class StudyPlanItem(BaseModel):
    topic: str
    action: str
    material: str | None = None           # doc/seção citada
    minutes: int = 30

class StudyPlan(BaseModel):
    items: list[StudyPlanItem] = []

class DifficultyReport(BaseModel):
    weak_topics: list[TopicScore] = []
    recommendations: list[str] = []
    plan: StudyPlan = StudyPlan()
    positive: bool = False                # True se não houve tópico fraco
```

## 3. Repo — `src/domain/learning/repo.py`

Funções recebendo `conn` (padrão chat/agenda). Principais:
`create_quiz`, `add_questions`, `get_quiz`, `list_quizzes`, `create_attempt`,
`save_answer`, `finalize_attempt`, `get_attempt`, `topic_breakdown`.
`topic_breakdown` faz `SELECT topic, SUM(max_points), SUM(awarded_points) ...
JOIN quiz_questions ... GROUP BY topic`.

## 4. Leitura por documento — `src/rag/retrieve.py`

```python
def get_document_chunks(document_id: int, limit: int | None = None) -> list[RetrievedChunk]:
    """Chunks de um documento em ordem de posição (sem embeddings). Corrige a Falha 4."""
    # SELECT c.id, c.text, c.position, c.document_id, d.title
    #   FROM chunks c JOIN documents d ON d.id=c.document_id
    #  WHERE c.document_id = ? ORDER BY c.position [LIMIT ?]
    # distance=0.0 (não se aplica)
```

## 5. Geração — `src/learning/generator.py`

Fluxo de `generate_quiz(gemma, document_ids, num_mc, num_open, title=None)`:
1. Para cada `document_id`: `get_document_chunks(doc, limit=MAX_CHUNKS_PER_DOC)`.
   Distribui a cota de questões entre os documentos (round-robin).
2. Monta o prompt com chunks **numerados globalmente** (`[T1] ... [T2] ...`) e pede
   um JSON único:

```json
{ "questions": [
  {"type":"mc","topic":"...","prompt":"...","options":["...","...","...","..."],
   "correct_index":2,"source":"T3","explanation":"..."},
  {"type":"open","topic":"...","prompt":"...","answer_key":"pontos esperados...","source":"T5"}
]}
```

3. Parsing tolerante (reusa a lógica de `agent._parse_json_response`/`_loads_lenient`
   — extrair para helper compartilhável em `src/llm/json_utils.py` para não duplicar).
4. Validação: contagem por tipo, `len(options)==4`, `correct_index∈[0..3]`,
   `source` mapeia para um chunk fornecido → `source_chunk_id`/`source_document_id`.
   JSON malformado/insuficiente → 1 reparo via re-prompt; falhou → `LearningError`.
5. Persiste quiz + questões; retorna `Quiz`.

Prompt do sistema (resumo): "Gere questões SOMENTE com base nos trechos numerados.
Cada questão deve indicar o trecho de origem (`source`). Não invente fatos fora dos
trechos. MC tem exatamente 4 alternativas e 1 correta. Responda APENAS o JSON."

## 6. Correção — `src/learning/grader.py`

- `grade_mc(question, response) -> (points, is_correct)`: compara índice; branco→0.
- `grade_open(gemma, question, response) -> (points, feedback)`: prompt do LLM-juiz:

```json
{"score": 0.0, "feedback": "...", "pontos_faltantes": ["..."]}
```

  recebe enunciado + `answer_key` + texto do `source_chunk` + resposta. `points =
  score * max_points`. Branco → (0, "não respondida") sem chamar LLM. Erro do LLM →
  (0, "não avaliada — erro do corretor") + warning, sem derrubar as demais.
- `aggregate_score(answers, questions) -> round(Σpoints/Σmax * 10, 1)`.

## 7. Coach — `src/learning/coach.py`

- `topic_scores(conn, attempt_id)` ← `repo.topic_breakdown`.
- `build_difficulty_report(gemma, conn, attempt_id)`:
  - fracos = tópicos com `ratio < WEAK_THRESHOLD` (0.6).
  - para cada fraco: `rag.retrieve.search(topic)` → contexto → LLM gera recomendação
    citando `[Doc N]`.
  - monta `StudyPlan` (ordena por menor `ratio`). Sem fracos → `positive=True`.
- Conversão plano→agenda: a UI usa as tools `adicionar_tarefa`/`adicionar_evento`
  existentes (1 tarefa por `StudyPlanItem`).

## 8. Tools — `src/tools/tool_learning.py`

| Tool | Args | Retorno |
|---|---|---|
| `gerar_prova` | `documentos` (títulos/ids), `num_mc`, `num_dissertativas` | `quiz_id`, resumo, instrução p/ abrir na UI |
| `corrigir_prova` | `attempt_id`, `respostas` | nota 0–10 + por questão |
| `identificar_dificuldades` | `attempt_id?` | tópicos fracos + ratios |
| `montar_plano_estudos` | `attempt_id?` | `StudyPlan` |
| `ler_documento` | `titulo` \| `document_id`, `limit?` | conteúdo ordenado (Falha 4) |

Todas logam em `tool_call_logs` (já via agent loop, D-015). `tools/` importa
**apenas** `learning/` (que importa `llm/gemma_client`) — sem ciclo e sem `tools/`→
`llm/`/`ui/`. O `GemmaClient` vem do **client default** (`llm.get_default_client()`,
setado no boot), nunca do `AppState`. `identificar_dificuldades`/`montar_plano_estudos`
sem `attempt_id` usam a última tentativa **graded**; se não houver nenhuma, retornam
mensagem amigável ("nenhuma prova concluída ainda") em vez de erro.

## 9. UI — `src/ui/dialogs/exam.py` (+ menu "+")

Diálogo em 4 passos (state machine simples por `ui.refreshable`):
1. Configurar: `ui.select(multiple=True)` dos documentos + `ui.number` MC/dissert.
   (defaults `JARVIS_QUIZ_DEFAULT_MC`/`_OPEN`) → "Gerar prova" + `ui.spinner`.
2. Responder: `ui.radio` (MC) / `ui.textarea` (open) → "Enviar respostas".
3. Resultado: nota em `ui.circular_progress`/badge + lista com acerto/erro,
   gabarito e feedback (rótulo "nota sugerida" nas dissertativas).
4. Dificuldades & plano: tópicos fracos + `StudyPlan` + botão "Adicionar à agenda".

Geração/correção rodam `async` (chamadas LLM) — não bloquear o event loop (§6).
Entrada no menu "+" ao lado de Material/Calendário/Tarefas/Auditoria (D-026).

## 10. Config — variáveis novas (`src/core/config.py` + `.env.example`)

| Var | Default | Uso |
|---|---|---|
| `JARVIS_QUIZ_DEFAULT_MC` | 5 | nº padrão de múltipla escolha |
| `JARVIS_QUIZ_DEFAULT_OPEN` | 3 | nº padrão de dissertativas |
| `JARVIS_QUIZ_MAX_CHUNKS_PER_DOC` | 12 | cota de contexto por documento |
| `JARVIS_QUIZ_WEAK_THRESHOLD` | 0.6 | corte de tópico fraco |

## 11. Política de erros (estende CLAUDE.md §8)

| Cenário | Política |
|---|---|
| LLM offline na geração/correção de aberta | Bloqueia com aviso (banner D-017); MC ainda corrige (determinística). |
| JSON da prova malformado | 1 reparo via re-prompt; falhou → `LearningError`, prova não criada, msg amigável. |
| Documento-fonte sem chunks legíveis | Pula com warning; nenhum usável → erro orientando trocar seleção. |
| LLM-juiz falha numa dissertativa | Questão "não avaliada" (0 + nota de rodapé), demais seguem; warning. |
| Resposta em branco | MC/aberta = 0; aberta recebe feedback "não respondida". |
| `attempt_id?` omitido e sem tentativa graded | Retorna mensagem amigável ("nenhuma prova concluída ainda"), não erro. |
| Tool error | Capturado pelo agent loop, logado em `tool_call_logs` com status='error' (D-015). |

## 12. Plano de testes

### Unit (`tests/unit/`)
- `test_learning_models.py`: validators (MC vs open), `TopicScore.ratio`.
- `test_grader.py`: `grade_mc` (acerto/erro/branco), `aggregate_score` (0–10).
- `test_quiz_parse.py`: parsing/validação do JSON de geração (válido, malformado→reparo,
  contagem errada, `correct_index` fora de faixa) com LLM **mockado**.
- `test_coach.py`: `topic_scores` agrega certo; seleção de fracos pelo threshold.
- `test_generator_prompt.py`: montagem de prompt/cota por documento (pura, sem LLM).

### Integration (`tests/integration/`)
- `test_migration_005.py`: aplica 005 sobre v4 → `user_version=5`, tabelas/FKs/CASCADE.
- `test_learning_repo.py`: CRUD contra SQLite temp (quiz→attempt→answers→breakdown).
- `test_get_document_chunks.py`: ordem por posição + `limit`.
- `test_generate_quiz_fake_llm.py`: `generate_quiz` com `GemmaClient` fake (JSON canned)
  → quiz persistido com `source_chunk_id` mapeado.

### Smoke (live_llm, opt-in)
- `test_smoke_quiz_live.py`: gera prova pequena de 1 doc real + corrige 1 aberta.

## 13. Definition of Done

### Artefatos de código
- Migration 005 + `domain/learning/{models,repo}.py` + `learning/{generator,grader,coach}.py`.
- `rag/retrieve.get_document_chunks` + `llm/json_utils.py` (helper extraído).
- `tools/tool_learning.py` (5 tools registradas) + `ui/dialogs/exam.py` + entrada no menu "+".
- Config + `.env.example` atualizados.

### Qualidade
- `pytest -q` verde (unit + integration; smoke opt-in), `ruff check .` limpo, mypy ok.
- Migrations aplicam até v5; app sobe; prova gera/corrige/pontua na UI.

### Funcional (mapeado ao enunciado)
- ✓ ≥2 funcionalidades de aprendizado; ✓ a prova é **interativa** (pergunta e avalia).
- ✓ Decisão de chamada de tool pela LLM + logs (`tool_call_logs`).

### Documentação e entrega
- ADR **D-030** (módulo learning + migration 005 + regra de camada + leitura por doc).
- README (seção de funcionalidades + IAs usadas) + STATUS atualizados.
- **RF-007.10**: relatório **Word** das 2 funcionalidades, pronto para entrega.

### Sequência pós-aprovação (combinada com o mantenedor)
implementar → **resolver dataset** → testar → relatório Word das 2 funcionalidades.

## 14. Rascunho do ADR D-030 (fixado pós-auditoria — copiar para decisions.md em T-007.13)

> Promovido para a spec por ser decisão **transversal** (nova camada + contrato de
> client + dependência). Será copiado para `decisions.md` em T-007.13.

**D-030 — Camada `learning/`, client LLM default e geração de relatório `.docx`**

- **Contexto**: a Spec 007 precisa de orquestração que combina **LLM + RAG +
  domínio**, o que não cabe em `domain/` (só importa `core/`) nem em `tools/` (não
  pode importar `llm/`, para não fechar o ciclo `llm/agent ↔ tools/registry`).
- **Decisão 1 — nova camada `src/learning/`**: pode importar `core`, `domain`,
  `rag`, `llm`; é importada por `ui/` e `tools/`. Atualizar CLAUDE.md §4/§4.1.
- **Decisão 2 — client LLM default** (`src/llm/client.py`): `set_default_client` no
  boot em **`src/ui/app.py`** (~linha 36, onde o `GemmaClient` é criado) +
  `get_default_client()`. `learning/*` recebe `gemma` opcional e cai no default.
  Mantém `tools/` sem importar `llm/`/`ui/` (importa só `learning/`) e sem ciclo
  (`gemma_client` não importa `tools/`, verificado em 29-37).
- **Decisão 3 — leitura por documento** (`rag.get_document_chunks`): habilita
  geração de prova e a tool `ler_documento`; **corrige a Falha 4** da análise de
  erros (recuperação sem escopo por documento).
- **Decisão 4 — dependência `python-docx`**: adicionada ao `pyproject` para gerar o
  relatório Word (RF-007.10). É de uso pontual (entregável acadêmico), não afeta o
  runtime do app. Alternativa rejeitada: gerar `.docx` à mão (frágil) ou só `.md`
  (não cumpre "formato Word bem formatado"). Lockfile re-gerado (`uv lock`).
- **Consequências**: +1 camada, +1 módulo `llm/client.py`, +1 função de retrieve,
  +1 dependência. `tools/tool_learning` importa só `learning/`. Sem violação §4.1.
- **Relacionada a**: D-007, D-013, D-019, D-022, D-029.
