# PLANO DE MELHORIAS — Trabalho 1 (Funcionalidades 3.1, 3.2, 3.3)

> **Status**: AGUARDANDO APROVAÇÃO HUMANA (em discussão item a item).
> **Criado em**: 2026-06-12.
>
> **Decisões já tomadas pelo mantenedor (2026-06-12)**:
> - **A2 → opção (a)**: reforçar a tool `buscar_material_rag` no agent loop
>   (texto completo do chunk + instrução de grounding/citação). NÃO rotear para
>   `pipeline.ask`. Caminho único (agent).
> - **C1 → o mantenedor fornece os documentos** (.pdf/.txt) em `/data`; o agente
>   cuida da ingestão + inventário + doc de limitações/chunking.
> **Método**: auditoria de código real (não baseada no STATUS.md). Cada item lista
> arquivo afetado, razão e prioridade. Nenhum código será escrito sem aprovação
> explícita (`aprovo o item X`), conforme [CLAUDE.md §5.4](CLAUDE.md).

---

## Veredito geral

| Funcionalidade | Implementada no código? | Demonstrável hoje? |
|---|---|---|
| **3.1 — RAG (consulta a materiais)** | ✅ Sim (ingest→chunk→embed→retrieve→geração via agent) | ⚠️ **NÃO** — falta dataset em `/data` |
| **3.2 — Agenda acadêmica** | ✅ Sim (consultar_agenda + adicionar_evento) | ⚠️ Parcial — sem dados seed |
| **3.3 — Lista de tarefas** | ✅ Sim (adicionar/listar/concluir) | ⚠️ Parcial — sem dados seed |
| **Tool calling (≥5)** | ✅ Sim (8 tools, decisão pela LLM, logs SQLite) | ✅ Sim |

Conclusão: as três funcionalidades **estão implementadas** no nível de código.
Os problemas são de **qualidade do RAG** e de **entregabilidade** (dataset, dados
de demonstração, ambiente reprodutível), não de ausência de funcionalidade.

---

## CRÍTICO (bloqueia nota / demonstração)

> **C1 — ✅ RESOLVIDO (2026-06-12).** Importados **10 documentos** acadêmicos da
> pasta Drive do professor (via `gdown`) para `data/` (Artigos/Livros/Material de
> Aula). **5 indexados** no RAG (3 artigos + 2 aulas) → **502 chunks**; 5 livros
> ficam como acervo (muito grandes). Índice limpo e re-ingerido com o chunking
> corrigido (B1). `data/README.md` documenta inventário, procedência, decisão de
> indexação, chunking e limitações. Recuperação validada (TF-IDF/KNN/chunking/
> regressão retornam o doc correto no topo).
> **Pendência de git**: `.gitignore` ignora `*.db` (ok) mas NÃO os PDFs — decidir
> no `git init` se commita os ~88 MB de livros ou os deixa só no Drive (a
> procedência já está documentada).

### C1 — Dataset ausente em `/data` (bloqueia 3.1 e é item obrigatório próprio)
- **Onde**: `data/` contém só `README.md`, `jarvis.db`, `uploads/` (vazio).
- **Razão**: o enunciado exige ≥10 documentos acadêmicos na pasta `/data`
  (ou link), com origem/tipo/limitações. **Faltar item obrigatório = nota zero.**
  Sem documentos, o RAG (3.1) não pode ser demonstrado nem avaliado (avaliação
  ≥10 perguntas do Trab. 2 também depende disso).
- **Ação proposta**: coletar/redigir ≥10 documentos (.md/.txt/.pdf) de conteúdo
  de IA/ML/estatística; preencher o inventário em `data/README.md`
  (arquivo, tipo, origem, licença, data); rodar ingestão; commitar os fontes.
- **Tipo**: entrega humana (curadoria) + script de ingestão. **Prioridade: máxima.**

### C2 — Ambiente `.venv` quebrado (reprodutibilidade) — ✅ RESOLVIDO (2026-06-12)
- **Onde**: `.venv/Scripts/python.exe` existia mas o trampoline `uv` falhava
  ("entity not found") — o Python base referenciado sumiu.
- **Resolução**: `uv sync --extra dev` reconstruiu o venv (CPython 3.12.13).
  Baseline `pytest -q` → **104 passed, 3 skipped** (smoke LLM opt-in). Verde.

> **Estado verificado do banco `data/jarvis.db` (2026-06-12)**:
> documents=2 (sendo 1 o próprio README.md + 1 artigo TF-IDF), chunks=14,
> events=2, tasks=3, tool_call_logs=29, chat_sessions=1, chat_messages=12.
> Confirma C1: há **~1 documento acadêmico real** → faltam ≥9.

---

## ALTO (qualidade do RAG — afeta a nota de RAG, 20%)

> **A1, A2 e A3 — ✅ IMPLEMENTADOS (2026-06-12).** Aprovados pelo mantenedor
> (`top_k=4`). `ruff` limpo, `pytest` 104 passed / 3 skipped.
> - A1+A2 em `src/tools/tool_rag.py`: envia texto COMPLETO do chunk, numera
>   `[Doc N]` via campo `ref`, e inclui campo `instrucao` de grounding; `top_k`
>   default 5→4. Reforço de citação na regra 7 de `src/tools/registry.py`.
> - A3 em `src/ui/components/chat_view.py`: bloco "Fontes" (helpers
>   `_collect_rag_sources` / `_render_rag_sources`) no streaming e na restauração.

### A1 — Truncamento de chunk a 400 chars no payload da tool RAG
- **Onde**: `src/tools/tool_rag.py:29` → `"text_preview": c.text[:400]`.
- **Razão**: os chunks têm ~800 chars (+overlap), mas a LLM só recebe os
  primeiros 400. **Metade do contexto recuperado é descartada antes da geração**,
  degradando a qualidade e a completude das respostas — exatamente o que o
  critério "RAG (20%)" avalia. O nome `text_preview` denuncia que foi pensado
  como prévia de UI, não como contexto de geração.
- **Ação proposta**: enviar o texto completo do chunk para a LLM (campo `text`),
  mantendo opcionalmente um `text_preview` separado só para exibição. Avaliar
  reduzir `top_k` para compensar tokens, se necessário.
- **Tipo**: alteração de código (1 arquivo). **Prioridade: alta.**

### A2 — Grounding fraco no caminho de geração realmente usado
- **Onde**: a UI usa **só** o agent loop (`src/llm/agent.py` via
  `chat_view._stream_response`). O system prompt do agente
  (`src/tools/registry.py:build_system_prompt`) pede "citar fontes quando
  aplicável" — instrução fraca. O prompt rígido anti-alucinação com citação
  obrigatória `[Doc N]` vive em `src/rag/prompt.py`, **mas esse caminho
  (`pipeline.ask`) não é chamado pela UI** (código órfão).
- **Razão**: risco de alucinação e de respostas sem citação prejudica a nota de
  RAG e a futura avaliação de erros (Trab. 2). Hoje a regra forte de grounding
  existe no projeto mas não está no caminho que roda.
- **Ação proposta** (escolher 1):
  - (a) Reforçar o retorno de `buscar_material_rag` com uma instrução explícita
    ("responda apenas com base nestes trechos; cite [Doc N]; se insuficiente,
    diga que não encontrou") e/ou enriquecer o system prompt do agente para
    perguntas conceituais; **ou**
  - (b) Rotear perguntas conceituais diretamente para `pipeline.ask`
    (grounding rígido já pronto) e usar o agent loop só para agenda/tarefas.
- **Tipo**: alteração de código (1–2 arquivos). **Prioridade: alta.**

### A3 — Citações/fontes não exibidas ao usuário na resposta
- **Onde**: `RagResponse.citations` é montado em `pipeline.py` mas a UI
  (`chat_view`) só mostra chips de tool call; o usuário não vê "Fontes: Doc X".
- **Razão**: transparência do RAG é diferencial e facilita a avaliação ≥10
  perguntas do Trab. 2 ("documentos recuperados" é coluna obrigatória lá).
  Mostrar as fontes recuperadas valoriza a entrega (bônus até 2 pts).
- **Ação proposta**: ao final de uma resposta que usou `buscar_material_rag`,
  renderizar um bloco "Fontes" com títulos/posições dos chunks recuperados.
- **Tipo**: alteração de código (UI). **Prioridade: alta (mas opcional).**

---

## MÉDIO (robustez / engenharia — critério Engenharia 10%)

> **M1 — ✅ IMPLEMENTADO (2026-06-12).** `src/rag/pipeline.py` removido +
> tipos `Citation`/`RagResponse` removidos de `types.py` + `__init__.py`
> atualizado. Registrado em [decisions.md D-027](decisions.md#d-027).
> `ruff` limpo, `pytest` 104 passed / 3 skipped. `prompt.py` mantido (testado).

### M1 — Código órfão `pipeline.ask` / `ask_complete`
- **Onde**: `src/rag/pipeline.py` exportado em `src/rag/__init__.py` mas não usado
  na UI.
- **Razão**: "separação de responsabilidades" e "o aluno deve explicar o código".
  Código morto confunde e contradiz a arquitetura descrita. Resolvido
  naturalmente se A2(b) for aprovado (passa a ser usado); senão, documentar ou
  remover.
- **Ação proposta**: decidir junto com A2 — usar (A2b) ou remover.
- **Tipo**: limpeza. **Prioridade: média.**

> **M2 — ✅ IMPLEMENTADO (2026-06-12).** `concluir_tarefa` agora aceita
> `task_id` OU `titulo` (resolvido por correspondência exata→substring, sem
> acento/caixa, entre tarefas pendentes; erro claro se nenhuma ou >1 casar).
> `tool_tasks.py` + schema atualizados. 5 testes novos em
> `tests/integration/test_tool_tasks.py`. `ruff` limpo.

### M2 — Concluir tarefa depende de `task_id` exato
- **Onde**: `src/tools/tool_tasks.py:_concluir_tarefa` exige `task_id`.
- **Razão**: o usuário fala "marquei a tarefa de estudar como concluída"; o agente
  precisa primeiro `listar_tarefas`, achar o id e então `concluir_tarefa`.
  Funciona, mas é frágil (LLM pode chutar id). Opcional: aceitar conclusão por
  correspondência de título.
- **Ação proposta**: adicionar fallback por título (match único) em
  `concluir_tarefa`, retornando erro claro se ambíguo.
- **Tipo**: alteração de código (1 arquivo). **Prioridade: média (opcional).**

> **M3 — ✅ ESCRITO E PRONTO PARA RODAR (2026-06-12).** Criado
> `scripts/seed_demo.py`: idempotente (marcador `[seed-demo]`, nunca apaga dados
> do usuário), datas relativas a hoje (fuso America/Campo_Grande), reusa
> `ingest_directory` para o dataset. Testado em DB temporário (2 execuções →
> mesmo estado: 4 eventos, 4 tarefas/1 concluída). `ruff` limpo.
> **Rodar quando o dataset estiver em `/data`**:
> `.venv\Scripts\python.exe -m scripts.seed_demo` (ou `--no-ingest`).

### M3 — Dados seed para demonstração (agenda + tarefas + materiais)
- **Onde**: não existe script de seed; o `jarvis.db` atual tem estado arbitrário.
- **Razão**: o vídeo (≤3 min) e a avaliação precisam de dados realistas e
  reproduzíveis. "O que tenho hoje?" só impressiona se houver eventos hoje.
- **Ação proposta**: `scripts/seed_demo.py` que popula eventos da semana, tarefas
  pendentes/concluídas e ingere o dataset de C1 — idempotente.
- **Tipo**: novo script. **Prioridade: média.**

---

## BAIXO (refinamentos)

> **B1 — ✅ IMPLEMENTADO (2026-06-12).** `chunk_text` reescrito: cada chunk é
> agora uma **fatia contígua exata** do texto original (`text[start:end]`), com
> `char_start`/`char_end` corretos e overlap real de até `overlap` chars vindo
> da fonte (antes os offsets eram aproximados e o overlap remontava a part
> anterior com `\n` injetado). Mantém D-006 (recursive splitter 800/150) — só
> torna a implementação fiel à doc do dataset. 2 testes novos travam o contrato
> (fatia exata + overlap). `ruff` limpo. **Atenção**: docs já ingeridos com a
> lógica antiga só serão re-chunkados ao re-ingerir (o dataset real ainda não
> foi carregado, então sem impacto prático).

### B1 — Revisar lógica de overlap no chunking
- **Onde**: `src/rag/chunk.py` (ramo com overlap): `char_start`/`char_end` são
  aproximados e o cálculo de posições é frágil.
- **Razão**: não quebra o RAG (posições não são usadas na recuperação), mas se a
  documentação do dataset afirmar "overlap de 150 chars", convém que o código
  reflita isso fielmente. Baixo impacto.
- **Ação proposta**: revisar/testar o overlap ou ajustar a doc do dataset à
  realidade do código.
- **Tipo**: código + teste. **Prioridade: baixa.**

### B2 — Tool de edição/remoção de evento via chat — ✅ IMPLEMENTADO (2026-06-12)
- **Razão**: hoje só dá para adicionar e consultar evento por chat (editar/remover
  só na UI do calendário). Fora do mínimo de 3.2, mas melhora a experiência.
- **Entregue**: `editar_evento` e `remover_evento` em `src/tools/tool_agenda.py`,
  localizando o evento por `event_id` OU `titulo` (resolução exata→substring,
  sem acento/caixa; erro lista candidatos se ambíguo). 4 testes novos em
  `tests/integration/test_tool_agenda.py`. `ruff` limpo.
- **Total de tools agora: 10** (eram 8). Nota: `README.md` e `STATUS.md` ainda
  citam 8 tools — atualizar a doc quando for fechar a entrega.

---

## Ordem de execução sugerida (após aprovações)

1. **C2** (consertar ambiente) → baseline `pytest` verde.
2. **C1** (dataset ≥10 docs + inventário) → ingestão.
3. **A1** (texto completo do chunk) → **A2** (grounding) → **A3** (fontes na UI).
4. **M3** (seed demo) → grava cenário para o vídeo.
5. **M1/M2/B1/B2** conforme aprovação.

> Cada item aprovado que envolver código novo deverá, conforme o processo SDD,
> ter sua spec/ajuste registrado e (quando transversal) um ADR em `decisions.md`.
