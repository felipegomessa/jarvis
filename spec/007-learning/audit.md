# Auditoria — Spec 007: Melhorias de Aprendizado

**Auditor**: spec-auditor · **Data**: 2026-06-13 · **Spec**: spec/007-learning/

## Veredito original

🟡 **APROVADA COM RESSALVAS — 2 bloqueadores de design** (sanados na revisão; ver §"Resolução" ao final).

O conteúdo é forte, rastreável e coerente com a constituição na maior parte. Lacuna
central: como uma tool obtém o `GemmaClient`.

## A. Coerência constitucional
- ✓ P1 (simplicidade), P3 (SDD: 3 arquivos + entrevista + tasks + auditoria), P5/§6 (logs/erros).
- ⚠ Stack §3: geração do `.docx` (RF-007.10) exige lib não listada (ex.: `python-docx`).
- ⚠ §4: cria `src/learning/` (novo top-level) — exige atualizar §4/§4.1 + ADR D-030.

## B. Requirements.md
- ✓ "Fora de escopo" explícito; critérios testáveis; rastreabilidade ao enunciado; sem ambiguidade relevante.

## C. Design.md
- ✓ Migration 005 no formato dos migrations 001–004; runner em `db.py:135-139` remove e aplica `PRAGMA user_version` (a linha no .sql é consistente).
- ✓ Contratos, fluxos e tratamento de erros (§11) bem definidos.
- ✓ **Verificado correto**: `src/llm/gemma_client.py` importa só `core`+`llm.{exceptions,types}` (29-37), nunca `tools/` → a justificativa de não-ciclo procede.
- ✗ **Bloqueador 1**: injeção do `GemmaClient` nas tools não especificada. Contrato real é `await tool_def.handler(args)` (`agent.py:216`) — handlers só recebem `args`; `AppState.gemma` está em `src/ui/state.py` e `tools/` não pode importar `ui/` (§4.1).

## D. Tasks.md
- ✓ Ordenação por dependência, `[P]` corretos, cobertura RF→task completa, tasks de teste (T-007.11/12), logging via `tool_call_logs`.

## E. Cobertura de erros
- ✓ LLM/rede (§8/D-014), JSON malformado (1 reparo), doc sem chunks (D-029), branco, prova sem tópico fraco.
- ⚠ **Ressalva 2**: `identificar_dificuldades/montar_plano_estudos(attempt_id?)` não define o caso "nenhuma tentativa graded".

## F. Testabilidade
- ✓ Funções puras + `gemma` por parâmetro (fake_llm/D-019). `RetrievedChunk` tem `text/position/document_title`.
- ⚠ **Ressalva 3**: `RetrievedChunk.distance` é required (`types.py:35`) — `get_document_chunks` deve preencher `0.0`.

## Bloqueadores
1. **Injeção do `GemmaClient` nas tools** (design.md:34/243) — inviável como descrita; especificar mecanismo (estender contrato com contexto **ou** client default em camada permitida).
2. **D-030 referenciado como consolidado mas inexistente** em `decisions.md` (vai até D-029). Como a regra de camada nova e a resolução do item 1 são transversais, fixar o rascunho do ADR na própria spec antes da aprovação humana.

## Ressalvas
1. Dependência `.docx` (`python-docx`) fora da stack §3 — registrar.
2. Caso "última tentativa inexistente" — definir retorno amigável.
3. `get_document_chunks` deve preencher `distance=0.0` (campo required).
4. `json_utils.py`: manter `agent.py` importando do novo módulo sem quebrar testes.

## Resolução (revisão 2026-06-13, pós-auditoria)
- **Bloqueador 1 → resolvido**: definido o mecanismo de *client default* em
  `src/llm/client.py` (`set_default_client`/`get_default_client`, setado no boot em
  `main.py`). `learning/*` aceita `gemma` por parâmetro (UI injeta `state.gemma`;
  testes injetam fake) e cai no client default quando omitido. `tools/tool_learning`
  importa **apenas `learning/`** (não `llm/` nem `ui/`) → §4.1 preservado
  literalmente; sem ciclo. Ver design.md §13 (revisado) e §14 (rascunho D-030).
- **Bloqueador 2 → resolvido**: rascunho do ADR **D-030** embutido em design.md §14
  (módulo `learning/` + regra de camada + client default + `python-docx`).
- **Ressalvas 1–4 → endereçadas** em design.md §10/§11/§13 e tasks T-007.4/.5/.13.
- Arquivo temporário órfão removido.

## Re-auditoria (2ª rodada, 2026-06-13) — 🟢 APROVADA

- **Bloqueador 1 → RESOLVIDO**: mecanismo de client default verificado — (a) `tools/`
  não importa `llm/`/`ui/` literalmente; (b) sem ciclo (`gemma_client` 29-37 e
  `llm/client.py` trivial); (c) **correção factual aplicada**: o `GemmaClient` é
  criado em `src/ui/app.py:36` (não em `main.py`) — wiring de `set_default_client`
  corrigido em design.md (2 trechos + §14) e em T-007.5.
- **Bloqueador 2 → RESOLVIDO**: rascunho D-030 completo na design.md §14.
- **Ressalvas 1–4 → OK.** Nenhuma regressão, ciclo ou violação de camada introduzida.
- **Veredito final: 🟢 APROVADA** (pendência factual de baixa severidade já sanada).
  Pronta para aprovação humana.
