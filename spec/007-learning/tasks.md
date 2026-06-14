# Spec 007 — Melhorias de Aprendizado — Tasks

> Ordenadas por dependência. `[P]` = paralelizável com as irmãs do mesmo bloco.
> Implementação só começa após auditoria + aprovação humana (`aprovo a spec 007`).

## T-007.1 — Migration 005 + config

- `src/core/migrations/005_learning.sql` (5 tabelas + índices + `user_version=5`).
- `src/core/config.py`: `quiz_default_mc`, `quiz_default_open`,
  `quiz_max_chunks_per_doc`, `quiz_weak_threshold`.
- `.env.example`: `JARVIS_QUIZ_*` (4 vars).

## T-007.2 — Modelos de domínio [P]

- `src/domain/learning/__init__.py` + `models.py`: `Question`, `Quiz`, `Attempt`,
  `Answer`, `TopicScore`, `StudyPlanItem`, `StudyPlan`, `DifficultyReport`.
- Validators Pydantic (MC vs open).

## T-007.3 — Repositório

- `src/domain/learning/repo.py`: `create_quiz`, `add_questions`, `get_quiz`,
  `list_quizzes`, `create_attempt`, `save_answer`, `finalize_attempt`,
  `get_attempt`, `topic_breakdown`. Recebem `conn` (D-013).

## T-007.4 — Leitura por documento [P]

- `src/rag/retrieve.py`: `get_document_chunks(document_id, limit=None)`.
- Preencher `RetrievedChunk.distance=0.0` (campo é required em `types.py:35`).
- Habilita a tool `ler_documento` e a geração (corrige a **Falha 4**).

## T-007.5 — Infra de LLM compartilhada [P]

- `src/llm/json_utils.py`: extrair `parse_json_response` + `loads_lenient` de
  `src/llm/agent.py` **sem duplicar**; `agent.py` passa a importar de lá
  (manter assinaturas — os testes `test_agent_json_parse.py` devem continuar verdes).
- `src/llm/client.py`: `set_default_client`/`get_default_client` (singleton).
- `src/ui/app.py`: chamar `set_default_client(gemma)` no startup, junto da criação
  do `GemmaClient` (~linha 36) / `set_clients` — **não** em `main.py` (resolve Bloq. 1).

## T-007.6 — Geração da prova

- `src/learning/__init__.py` + `generator.py`: `generate_quiz(...)` (cota por doc,
  prompt aterrado numerado, parsing+validação+1 reparo, mapeia `source_chunk_id`).
- `src/learning/errors.py`: `LearningError`.

## T-007.7 — Correção e nota [P]

- `src/learning/grader.py`: `grade_mc`, `grade_open` (LLM-juiz), `aggregate_score`.

## T-007.8 — Coach (dificuldades + plano)

- `src/learning/coach.py`: `topic_scores`, `build_difficulty_report` (RAG + plano).

## T-007.9 — Tools

- `src/tools/tool_learning.py`: `gerar_prova`, `corrigir_prova`,
  `identificar_dificuldades`, `montar_plano_estudos`, `ler_documento`.
- Registrar no `get_registry()` (import com efeito colateral) + dica no system prompt.

## T-007.10 — UI da prova

- `src/ui/dialogs/exam.py`: fluxo de 4 passos (configurar → responder → resultado →
  dificuldades & plano) com `ui.refreshable`, async, spinner.
- Entrada "Estudar / Prova" no menu "+" (`src/ui/components/...`).
- Botão "Adicionar à agenda" reusando `adicionar_tarefa`/`adicionar_evento`.

## T-007.11 — Testes unit [P]

- `test_learning_models.py`, `test_grader.py`, `test_quiz_parse.py`,
  `test_coach.py`, `test_generator_prompt.py` (LLM mockado).

## T-007.12 — Testes integration

- `test_migration_005.py`, `test_learning_repo.py`, `test_get_document_chunks.py`,
  `test_generate_quiz_fake_llm.py`. (+ smoke `test_smoke_quiz_live.py`, opt-in.)

## T-007.13 — Documentação + dependência

- ADR **D-030** (módulo `learning/` + client LLM default + regra de camada §4.1 +
  migration 005 + leitura por documento / Falha 4 + `python-docx`) em `decisions.md`
  (copiar do rascunho em design.md §14).
- Adicionar `python-docx` ao `pyproject.toml` + `uv lock` (para RF-007.10).
- Atualizar CLAUDE.md §3 (stack: +learning, +python-docx) e §4 (estrutura) + §4.1
  (regra: `learning/` ⊂ {core, domain, rag, llm}; `tools/` pode importar `learning/`).
- README (funcionalidades + IAs) + STATUS.

## T-007.14 — Dataset (entrega humana, FORA de código, após implementação)

- Recuperar *The Origins* (OCR ou cópia com texto selecionável) e/ou adicionar
  materiais até **≥10 documentos indexados**. Atualizar `data/README.md`.
- **Antes dos testes funcionais**, conforme sequência combinada.

## T-007.15 — Relatório Word das 2 funcionalidades (RF-007.10, ENTREGÁVEL)

- Gerar `.docx` bem formatado em `docs/`: descrição de cada funcionalidade,
  fundamentação técnica, evidências (fluxos/prints), mapeamento ao requisito
  (incl. qual é a interativa). **Tarefa final**, após os testes.

## T-007.16 — Auditoria e aprovação

- `spec-auditor` audita esta spec → `spec/007-learning/audit.md`.
- Aprovação humana (`aprovo a spec 007`).
- Implementação executa T-007.1 a T-007.13; depois T-007.14 (dataset) → testes →
  T-007.15 (relatório Word).
