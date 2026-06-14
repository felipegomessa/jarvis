# Spec 007 — Melhorias de Aprendizado — Requirements

> Entrega o requisito **OBRIGATÓRIO** "Melhorias de Aprendizado" do Trabalho 2:
> ≥2 funcionalidades voltadas ao aprendizado, **≥1 interativa** (o sistema pergunta
> e avalia). Constrói sobre RAG (Spec 002), Tool Calling (Spec 005), Agenda/Tarefas
> (Specs 003/004) e a UI v2 (Spec 006 / D-026).

## Contexto

A partir dos materiais que o usuário carregou (item "Enviar material"), o sistema
deve oferecer duas funcionalidades de aprendizado:

1. **Prova eletrônica (interativa)** — gera uma lista de questões de **múltipla
   escolha + dissertativas** a partir de **vários documentos selecionados**, o
   usuário responde online, e o sistema **corrige e atribui nota de 0 a 10**.
2. **Identificação de dificuldades + plano de estudos** — a partir do desempenho
   na prova, identifica os tópicos mais fracos, recomenda revisão (citando o
   material) e **monta um plano de estudos** que o usuário pode adicionar à agenda.

A funcionalidade (1) satisfaz o requisito mínimo de interatividade ("o sistema
pergunta e avalia"). A funcionalidade (2) adianta a **Funcionalidade 3.4**
(planejamento de estudos) ao integrar materiais + agenda + tarefas.

Decisões de entrevista SDD (2026-06-13): fonte = vários documentos selecionados;
composição definida pelo usuário com padrões sugeridos; correção de dissertativa =
nota **sugerida** por rubrica + feedback (compõe o 0–10); plano de estudos = exibe
+ botão "Adicionar à agenda".

ADRs novos consolidados nesta spec: **D-030** (módulo `learning/` + migration 005 +
leitura por documento). ADRs herdados relevantes: D-007 (tool calling), D-009/D-013
(DB/Pydantic/conexão), D-010/D-015 (logs de tool call), D-014/D-018 (LLM client),
D-024 (persistência), D-025 (calendar VIEW), D-026 (UI v2), D-029 (qualidade de
ingestão).

## Requisitos funcionais

### RF-007.1 — Migration 005: tabelas de provas/aprendizado

Acrescenta ao schema (forward-only, `PRAGMA user_version = 5`):
- `quizzes`, `quiz_documents`, `quiz_questions`, `quiz_attempts`, `quiz_answers`.

**Critério de aceitação**:
- ✓ Arquivo `src/core/migrations/005_learning.sql` criado.
- ✓ Após aplicar 005 sobre DB v4: as 5 tabelas existem com FKs e índices.
- ✓ `quiz_documents` referencia `documents(id)`; `quiz_questions` referencia
      `quizzes(id)` e (opcional) `chunks(id)`/`documents(id)`; deletar um quiz faz
      CASCADE em questions/attempts/answers.
- ✓ `PRAGMA user_version = 5` ao final. Teste de integração cobre.

### RF-007.2 — Modelos de domínio (Pydantic)

`src/domain/learning/models.py` expõe `Quiz`, `Question`, `Attempt`, `Answer`,
`TopicScore`, `DifficultyReport`, `StudyPlan` (+ `StudyPlanItem`).

**Critério de aceitação**:
- ✓ `Question` tem `type ∈ {"mc","open"}`, `prompt`, `topic`, `max_points`,
      `source_document_id`, `source_chunk_id`; campos de MC (`options: list[str]`,
      `correct_index: int`) e de dissertativa (`answer_key: str`) são opcionais e
      validados conforme o tipo (validator Pydantic: MC exige options+correct_index;
      open exige answer_key).
- ✓ `Quiz` tem `documents: list[int]` (≥1) e `questions: list[Question]`.
- ✓ `Attempt` tem `score: float | None` (0–10) e `status ∈ {"in_progress","graded"}`.
- ✓ Modelos são puros (camada `domain/` importa apenas `core/`).

### RF-007.3 — Repositório de aprendizado

`src/domain/learning/repo.py` expõe funções CRUD que recebem `conn` (padrão D-013).

**Critério de aceitação**:
- ✓ `create_quiz(conn, title, document_ids) -> int`, `add_questions(conn, quiz_id,
      questions)`, `get_quiz(conn, quiz_id) -> Quiz`, `list_quizzes(conn, limit)`.
- ✓ `create_attempt(conn, quiz_id) -> int`, `save_answer(conn, attempt_id,
      question_id, response, awarded_points, is_correct, feedback)`,
      `finalize_attempt(conn, attempt_id, score)`, `get_attempt(conn, attempt_id)`.
- ✓ `topic_breakdown(conn, attempt_id) -> list[TopicScore]` agrega pontos
      obtidos/possíveis por `topic`.
- ✓ Erros de FK/constraint propagam como exceção tratável (não silenciosos).

### RF-007.4 — Leitura por documento (corrige a Falha 4)

`src/rag/retrieve.py` expõe `get_document_chunks(document_id: int, limit: int | None
= None) -> list[RetrievedChunk]` (ordenado por `position`).

**Critério de aceitação**:
- ✓ Retorna os chunks daquele documento em ordem de posição (sem embeddings).
- ✓ `limit` opcional restringe a N primeiros (para cota de contexto).
- ✓ Documento inexistente → lista vazia (sem exceção).
- ✓ Habilita a tool `ler_documento` (RF-007.8) e a geração de provas (RF-007.5).

### RF-007.5 — Geração da prova (LLM aterrado nos documentos)

`src/learning/generator.py` expõe `async generate_quiz(gemma, document_ids: list[int],
num_mc: int, num_open: int, *, title: str | None = None) -> Quiz`.

**Critério de aceitação**:
- ✓ Lê os chunks de **cada** documento via `get_document_chunks`, aplicando uma
      **cota por documento** (`JARVIS_QUIZ_MAX_CHUNKS_PER_DOC`, default 12) e
      distribuindo as questões entre os documentos selecionados.
- ✓ Monta prompt que envia os chunks **numerados** e instrui o LLM a gerar um
      **JSON único** com `num_mc` questões `mc` e `num_open` questões `open`, cada
      uma com `topic` e o **índice do chunk de origem** (aterramento) — sem inventar
      conteúdo fora dos trechos.
- ✓ Faz parsing tolerante (reusa a estratégia de `_loads_lenient`/extração de JSON);
      em JSON malformado, **1 reparo** via re-prompt; se falhar, levanta erro tratável.
- ✓ Valida o JSON contra o schema (nº de questões por tipo, campos por tipo,
      `correct_index` dentro de `options`); mapeia `source_index → source_chunk_id`.
- ✓ Persiste o quiz + questões (status `ready`) e retorna o `Quiz`.
- ✓ MC têm 4 alternativas como alvo (validação aceita **2–6** para robustez com a
      LLM real), 1 correta (`correct_index` dentro da faixa); dissertativas têm
      `answer_key` (rubrica/pontos esperados) usada na correção.
- ✓ Parâmetro `idioma` (`"pt"` default | `"original"`): em `"pt"`, enunciados,
      alternativas e gabaritos saem em **português** mesmo que o material esteja em
      inglês; em `"original"`, no idioma da fonte. Feedback/correção e plano são
      sempre PT-BR (P6).

### RF-007.6 — Correção e nota 0–10

`src/learning/grader.py` expõe `grade_mc(question, response) -> tuple[float, bool]`,
`async grade_open(gemma, question, response) -> tuple[float, str]` e
`aggregate_score(answers, questions) -> float`.

**Critério de aceitação**:
- ✓ **MC**: determinística — compara índice escolhido com `correct_index`;
      `max_points` se acerta, 0 caso contrário; resposta em branco = 0.
- ✓ **Dissertativa**: LLM-juiz recebe enunciado + `answer_key` + trecho-fonte +
      resposta do aluno e devolve JSON `{"score": 0..1, "feedback": str,
      "pontos_faltantes": [...]}`. `awarded_points = score * max_points`. A nota é
      tratada e exibida como **sugestão**.
- ✓ Resposta dissertativa em branco = 0 com feedback "não respondida" (sem chamar LLM).
- ✓ Erro do LLM-juiz numa questão → questão fica "não avaliada" (pontos 0 + nota de
      rodapé), **não derruba** a correção das demais (loga warning).
- ✓ `aggregate_score = soma(awarded_points)/soma(max_points) * 10`, arredondado a
      1 casa. Persiste em `quiz_attempts.score` e finaliza a tentativa.

### RF-007.7 — Identificação de dificuldades + plano de estudos

`src/learning/coach.py` expõe `topic_scores(conn, attempt_id) -> list[TopicScore]` e
`async build_difficulty_report(gemma, conn, attempt_id) -> DifficultyReport`.

**Critério de aceitação**:
- ✓ Agrega desempenho por `topic`; marca **fracos** os tópicos com aproveitamento
      `< JARVIS_QUIZ_WEAK_THRESHOLD` (default 0.6).
- ✓ Para cada tópico fraco, recupera trechos do material (RAG) e o LLM gera uma
      **recomendação de revisão** citando a fonte.
- ✓ Monta um `StudyPlan` **didático e consciente da agenda**: ações de estudo
      concretas e progressivas; **dimensiona pela profundidade** (tópicos com menor
      aproveitamento recebem mais/maiores sessões); **consulta a agenda** do aluno
      (eventos dos próximos 7 dias) e **distribui as sessões em dias/horários livres**
      (`StudyPlanItem`: tópico, ação, material, minutos, `day`/`time`), evitando
      conflito com compromissos.
- ✓ Se não houver tópico fraco (prova boa), retorna relatório positivo sem plano
      de revisão (mensagem de parabéns + sugestão de aprofundamento opcional).

### RF-007.8 — Tools (decisão de chamada pela LLM)

`src/tools/tool_learning.py` registra: `gerar_prova`, `corrigir_prova`,
`identificar_dificuldades`, `montar_plano_estudos`, `ler_documento`.

**Critério de aceitação**:
- ✓ `gerar_prova(documentos, num_mc, num_dissertativas)` cria a prova e retorna
      `quiz_id` + resumo (e instrui o usuário a abrir a prova na UI para responder).
- ✓ `identificar_dificuldades(attempt_id?)` e `montar_plano_estudos(attempt_id?)`
      retornam a análise/plano da última tentativa (ou da informada).
- ✓ `ler_documento(titulo|document_id)` retorna o conteúdo do documento (em ordem),
      resolvendo "leia o documento X / me dê o índice / resuma o material X".
- ✓ `identificar_dificuldades`/`montar_plano_estudos` sem `attempt_id` usam a última
      tentativa **graded**; sem nenhuma, retornam mensagem amigável (não erro).
- ✓ As tools obtêm o LLM via `llm.get_default_client()` (não pelo `AppState`);
      `tools/tool_learning` importa apenas `learning/` (§4.1 preservado).
- ✓ Todas registram em `tool_call_logs` (D-015) com entrada/saída/duração/status.
- ✓ Descrições em PT-BR orientam a LLM a escolher a tool certa.

### RF-007.9 — UI interativa da prova (menu "+")

Nova entrada **"Estudar / Prova"** no menu "+" do chat (`src/ui/dialogs/exam.py`).

**Critério de aceitação**:
- ✓ **Passo 1 (configurar)**: multiseleção dos documentos do acervo + campos de nº
      de questões MC e dissertativas (pré-preenchidos com padrões) + **seletor de
      idioma** (Português default | Original do material) → "Gerar prova" com
      indicador de progresso durante a chamada ao LLM.
- ✓ **Passo 2 (responder)**: questões MC com `radio`, dissertativas com `textarea`;
      botão "Enviar respostas".
- ✓ **Passo 3 (resultado)**: **nota 0–10** em destaque, acerto/erro por questão,
      **a resposta do aluno** (MC: alternativa marcada; dissertativa: texto) ao lado
      da **resposta correta**, **gabarito comentado** e feedback das dissertativas
      (rotulado "nota sugerida").
- ✓ **Passo 4**: ao "Adicionar à agenda", sessões com data/hora viram **eventos**
      no horário sugerido; itens sem data viram **tarefas**.
- ✓ **Passo 4 (dificuldades & plano)**: relatório de tópicos fracos + plano de
      estudos + botão **"Adicionar à agenda"** (cria tarefas/eventos via as tools
      existentes). Async (não bloqueia o event loop — D-016/§6).

### RF-007.10 — Relatório Word das 2 funcionalidades (ENTREGÁVEL OBRIGATÓRIO)

Ao final da implementação, produzir um **relatório acadêmico em formato Word**
(`.docx`), **bem formatado e pronto para entrega**, comprovando o cumprimento do
requisito "Melhorias de Aprendizado".

**Critério de aceitação**:
- ✓ Documento `.docx` com: capa/título, descrição de **cada** funcionalidade,
      fundamentação técnica (RAG/LLM/tool calling), **evidências** (fluxos/prints),
      e o **mapeamento explícito** ao requisito do enunciado (incl. qual é a
      interativa). Gerado em `docs/` (ou pasta de entrega) do repositório.
- ✓ É **tarefa final** da spec (não um extra), executada após os testes.

## Critérios de qualidade transversais

Herdados de Spec 000 (CT-1 a CT-7): type hints públicos, erros tratados (nunca
silenciosos), logs em nível apropriado, async nos handlers/LLM, código explicável.

## Fora de escopo desta spec

- **NÃO** implementa banco de questões reutilizável / SRS (spaced repetition) — T2 futuro.
- **NÃO** implementa correção colaborativa ou revisão humana das notas.
- **NÃO** implementa exportação da prova para PDF/impressão.
- **NÃO** implementa cronômetro/limite de tempo na prova.
- **NÃO** implementa a avaliação ≥10 perguntas nem a análise de erros (entregáveis
      Word próprios, fora desta spec).
- **NÃO** resolve o dataset (recuperar *The Origins* / chegar a ≥10 docs) — passo
      humano separado, **após** a implementação e **antes** dos testes.

## Riscos identificados

| Risco | Mitigação |
|---|---|
| LLM gera questão fora do material (alucinação) | Geração aterrada nos chunks + `source_chunk_id` por questão; revisão na avaliação. |
| Correção de dissertativa subjetiva | Rubrica (`answer_key`) + nota rotulada "sugerida" + feedback + gabarito visível. |
| Documentos grandes estouram o contexto do LLM | Cota de chunks por documento (`MAX_CHUNKS_PER_DOC`) + amostragem; logar o que foi truncado. |
| JSON da prova malformado | 1 reparo via re-prompt (igual D-007/§8); falhou → erro amigável, prova não criada. |
| LLM offline (modo degradado) | Bloqueia geração/correção com aviso na UI (banner D-017); MC poderia ser corrigida offline (determinística). |
| Documento selecionado sem chunks legíveis (pós D-029) | Pula o doc com aviso; se nenhum usável, erro orientando trocar a seleção. |
| Plano de estudos polui a agenda | Só cria tarefas/eventos sob clique explícito ("Adicionar à agenda"). |
