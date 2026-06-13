# Auditoria — Spec 000: Foundation

**Auditor**: spec-auditor
**Data**: 2026-05-23
**Spec**: spec/000-foundation/
**Versão dos arquivos**: requirements.md, design.md, tasks.md (auditados juntos)

## Veredito

- 🟡 **APROVADA COM RESSALVAS**

## Resumo executivo

A Spec 000 cumpre seu papel de fundação: define o processo SDD, ancora as 11 ADRs já
registradas, documenta a estrutura de diretórios e fixa critérios de qualidade
transversais (CT-1 a CT-7). Os artefatos prometidos (`CLAUDE.md`, `decisions.md`,
`.claude/agents/spec-auditor.md`, `.claude/settings.json`, `pyproject.toml`,
`.gitignore`, `.env.example`, `README.md`, estrutura de pastas com `__init__.py`)
existem no repositório e são coerentes entre si. Como esperado para uma spec de
fundação, seções B–F são parcialmente "delegadas" para Specs 001–006, e isso foi
contemplado de forma legítima. As ressalvas são pontuais e não bloqueiam a aprovação.

## A. Coerência constitucional

- [✓] **Princípios P1–P7 respeitados** — RF-000.1 implementa P3 (SDD) e P4 (auditoria);
  RF-000.2 implementa P7 (reprodutibilidade); RF-000.5 implementa P2 (decisões
  não-voláteis ao proteger secrets); CT-1 a CT-7 (linha 79–86 de requirements.md)
  ecoam P1 (simplicidade explícita) e §6 (convenções).
- [✓] **Sem contradição com ADRs** — `design.md` linhas 20–32 lista D-001 a D-011 e
  cada item da spec aponta para a ADR correspondente. Nenhuma decisão da spec tenta
  substituir uma ADR existente.
- [✓] **Stack restrita às tecnologias listadas** — `pyproject.toml` (verificado) lista
  exatamente as bibliotecas declaradas em CLAUDE.md §3 (openai, sentence-transformers,
  sqlite-vec, pdfplumber, pydantic, pydantic-settings, loguru, python-dotenv, nicegui,
  python-dateutil) + dev (pytest, pytest-asyncio, ruff, mypy). Nenhuma dependência
  inesperada.
- [⚠] **`.claude/skills/` não está mencionado em CLAUDE.md** — CLAUDE.md §4 cita
  `.claude/skills/` como "vazio inicialmente" (linha 93), e ele existe (verificado).
  Não é um problema, mas tasks.md T-000.8 (linha 50) faz referência a criar
  `.claude/skills/` — convém mencionar essa pasta nos critérios de aceitação de
  RF-000.3 para fechar o loop de rastreabilidade. Não bloqueia.

## B. Requirements.md

> A Spec 000 é uma spec de meta-requisitos transversais. Itens normalmente esperados
> (modelo de dados próprio, contratos de API) não se aplicam — eles são delegados
> explicitamente para Spec 001.

- [✓] **Seção "Fora de escopo" explícita** — linhas 88–97 listam 8 não-objetivos
  claros (deploy, multi-usuário, i18n, backup automático, migration framework, OCR,
  iCal, testes de UI). Excelente.
- [✓] **Critérios de aceitação testáveis** — Cada RF-000.x termina com bullets `✓`
  verificáveis ("Existe arquivo X", "Arquivo Y contém Z", "Estrutura W criada com
  __init__.py"). São binários e auditáveis.
- [✓] **Rastreabilidade ao enunciado do trabalho** — RF-000.1 ↔ Processo SDD (P3);
  RF-000.2 ↔ Reprodutibilidade (P7); RF-000.5 ↔ Segurança de token; RF-000.6 ↔
  Auditoria de tool calls (requisito do trabalho sobre logs). Bem amarrado.
- [✓] **Linguagem clara** — sem termos vagos. Critérios usam verbos checáveis
  ("existe", "contém", "documenta").
- [⚠] **CT-7 menciona "PEP 8 / ruff sem erros"** — Não há, no momento, hook ou task
  que execute `ruff check` automaticamente. CT-7 é um critério aspiracional;
  considerar adicionar à Spec 001 (ou em hook do `.claude/settings.json`) o gate
  de lint. Não bloqueia a Spec 000.

## C. Design.md

> Design da Spec 000 é, intencionalmente, um índice/agregador de decisões já
> existentes. A avaliação ajusta-se a esse propósito.

- [✓] **Modelo de dados (visão geral)** — linhas 72–80 listam as 5 tabelas previstas
  (`documents`, `chunks`, `events`, `tasks`, `tool_call_logs`) com colunas-chave.
  Detalhamento (DDL, índices, constraints) é corretamente delegado para Spec 001.
- [✓] **Contratos de função/API** — não aplicáveis (Spec 000 não introduz API). A
  delegação para Spec 001 é explícita ("a ser implementado em Spec 001" na linha 52).
- [✓] **Fluxo de dados** — linhas 84–96 apresentam os 2 fluxos críticos (RAG e Tool
  Calling) em alto nível, deixando detalhes para Specs 002 e 005.
- [✓] **Regras de dependência entre camadas** — linha 16 referencia explicitamente
  CLAUDE.md §4.1 e dá um sumário correto (`ui → tools/llm → domain/rag → core`).
- [✓] **Tratamento de erros explícito** — linhas 98–106 ("Riscos transversais
  identificados") cobrem endpoint instável, modelo lento ao baixar, sqlite-vec
  ausente, JSON malformado, conflito de schema. Cada risco tem mitigação. Confronto
  com CLAUDE.md §8 é coerente.
- [✓] **Variáveis de ambiente** — tabela de linhas 50–70 com 16 variáveis, defaults
  e origem. Confere com `.env.example` (verificado): todas as 16 estão lá em mesma
  ordem semântica.
- [⚠] **Inconsistência menor em `design.md` linhas 109–118 (Critérios de Pronto)** —
  os itens `[x]` marcam tarefas concluídas, mas T-000.13 (uv.lock gerado) e T-000.14
  (git init) estão como pendentes em `tasks.md` e o `uv.lock` ainda não existe no
  repositório. Isto é coerente com o fluxo (uv sync depende da aprovação humana),
  mas convém deixar nota explícita no design.md de que "[x]" representa "artefato
  prometido nesta entrega" e "[ ]" representa "depende de etapa pós-aprovação".
  Não bloqueia.

## D. Tasks.md

- [✓] **Ordem por dependência** — T-000.1 (CLAUDE.md) precede T-000.2 (decisions.md)
  e T-000.3 (auditor) que dependem dela; T-000.8 (estrutura de pastas) precede
  T-000.13 (uv sync); T-000.11 (auditoria) precede T-000.12 (aprovação humana) e
  T-000.13/.14. Ordem correta.
- [✓] **`[P]` em independentes** — T-000.2, T-000.3, T-000.4, T-000.6, T-000.7,
  T-000.9, T-000.10 estão marcadas `[P]` corretamente; todas operam em arquivos
  distintos sem entrada-saída entre si.
- [✓] **Cobertura dos critérios de RF-000.x**:
  - RF-000.1 → T-000.1 + T-000.2 + T-000.3 ✓
  - RF-000.2 → T-000.5 + T-000.7 + T-000.9 + T-000.13 ✓
  - RF-000.3 → T-000.8 ✓
  - RF-000.4 → T-000.7 (declara `JARVIS_LOG_LEVEL`) — implementação fica para Spec 001 ✓
  - RF-000.5 → T-000.6 + T-000.7 ✓
  - RF-000.6 → delegado a Spec 001 (citado em RF-000.6 critério) ✓
- [⚠] **Tasks de teste ausentes** — Spec 000 não tem código de aplicação, então é
  natural não haver task de teste *de código*. Entretanto, o auditor sugere que
  T-000.13 ("rodar uv sync") seja explicitada como teste de smoke da
  reprodutibilidade (RF-000.2), e que se acrescente uma sub-verificação: "rodar
  `uv run python -c 'import src; print(src.__version__)'` confere import básico".
  Não bloqueia.
- [✓] **Tasks de logging** — não aplicável aqui (logging será implementado em Spec
  001). Mencionado em RF-000.4 e D-010.
- [✓] **Granularidade adequada** — 14 tasks bem dimensionadas: nem todas são triviais
  (T-000.5 criar pyproject.toml exige decisão), nem genéricas demais.

## E. Cobertura de cenários de erro

> A Spec 000 enumera **riscos transversais** que serão tratados nas specs
> subsequentes. Avaliação adapta-se a esse escopo de meta-spec.

- [✓] **Falha de I/O externo (LLM, rede)** — linha 100 do design.md cita "Endpoint
  LIA UFMS instável/indisponível" com mitigação (retry exponencial; UI mostra erro
  amigável). Confere com CLAUDE.md §8.
- [✓] **Entrada malformada vinda da LLM** — linha 104 do design.md trata "LLM retorna
  JSON malformado em tool calls" com mitigação (1 retry com re-prompt). Coerente com
  CLAUDE.md §8.
- [⚠] **Estado inconsistente do DB** — CLAUDE.md §8 cobre "SQLite locked" com retry
  exponencial, mas o design.md da Spec 000 não retoma esse risco. Sugestão: incluir
  uma linha na tabela de "Riscos transversais identificados" mencionando integridade
  de SQLite (lock + corrupção). Não bloqueia — está coberto em CLAUDE.md.
- [✓] **Cenários de domínio** — corretamente delegados às specs de feature
  (002/003/004/005). A Spec 000 não precisa enumerá-los.

## F. Testabilidade

- [✓] **Funções puras testáveis sem mocks pesados** — Spec 000 não introduz funções;
  a regra fica como herança para todas as specs (CT-1, CT-2). CLAUDE.md §7 define
  política de testes (unit para puros, integration para repos/LLM). Bem ancorado.
- [✓] **Componentes que dependem de LLM têm camada de abstração** — design.md
  linha 13 ("layered architecture") + CLAUDE.md §4.1 (regras de dependência)
  garantem que `llm/` é uma camada própria. A abstração concreta vem na Spec 001.
- [⚠] **Pelo menos 1 task de teste para cada componente novo** — Spec 000 não tem
  componente de código, então o critério não se aplica diretamente. Anotação para
  Specs 001+: cada spec subsequente deve ter pelo menos uma task de teste por
  módulo novo.

## Bloqueadores (precisam ser resolvidos antes da aprovação humana)

(nenhum)

A Spec 000 não apresenta bloqueadores. Todos os artefatos prometidos existem, são
coerentes entre si, e nenhum item viola CLAUDE.md ou contradiz alguma ADR.

## Ressalvas (não bloqueiam, mas recomenda-se endereçar)

1. **Rastreabilidade `.claude/skills/`** — Adicionar uma linha em RF-000.3 (ou
   T-000.8) listando explicitamente `.claude/skills/` para fechar a referência feita
   em CLAUDE.md §4 (`.claude/skills/ # Skills sob demanda (vazio inicialmente)`).
   *Onde mudar*: `spec/000-foundation/requirements.md` linha 47 (critério de
   aceitação de RF-000.3).

2. **Esclarecer semântica dos `[x]` no DoD do design.md** — Linhas 109–118
   misturam "artefato existente" e "etapa futura". Sugestão: dividir em duas
   sub-seções, *Artefatos entregues* (todos `[x]`) e *Etapas pós-aprovação*
   (`[ ]` por design, não por falha).
   *Onde mudar*: `spec/000-foundation/design.md` linhas 108–118.

3. **Gate de lint não automatizado** — CT-7 (ruff sem erros) é declarado como
   critério transversal, mas não há automação. Sugestão (para Spec 001 ou ao
   menos como nota): adicionar hook `PostToolUse` em `.claude/settings.json` que
   roda `ruff check` em arquivos `.py` modificados, ou task explícita de CI local.
   Não bloqueia esta spec.

4. **Smoke test de reprodutibilidade** — T-000.13 ("Setup do venv via uv") poderia
   incluir um teste mínimo de import (`uv run python -c "import src;
   print(src.__version__)"`) para garantir que a estrutura de pacotes está
   instalável, não apenas presente em disco.
   *Onde mudar*: `spec/000-foundation/tasks.md` linhas 80–84 (T-000.13).

5. **Risco de integridade do SQLite** — Embora coberto em CLAUDE.md §8, o
   design.md da Spec 000 não menciona explicitamente o cenário "SQLite locked /
   journal corrompido". Sugestão: 1 linha extra na tabela de riscos transversais.
   *Onde mudar*: `spec/000-foundation/design.md` linhas 98–106.

## Observações adicionais

**Pontos positivos**:

- A separação entre "meta-spec" (esta) e "spec de feature" (001+) está clara: a
  Spec 000 reconhece sua função de scaffolding e delega corretamente.
- A tabela de variáveis de ambiente em `design.md` (linhas 50–70) confere
  exatamente com `.env.example` — alto grau de coerência.
- As 11 ADRs (D-001 a D-011) verificadas em `decisions.md` estão completas
  (contexto, decisão, alternativas, consequências) e referenciadas em CLAUDE.md.
- O `.gitignore` é completo e protege explicitamente `*.env` mas preserva
  `.env.example` (`!.env.example`). Boa prática.
- Estrutura de diretórios verificada via Glob: `src/{core,llm,rag,domain/agenda,
  domain/tasks,tools,ui/views}`, `tests/{unit,integration}`, `data/`, `logs/`,
  `.claude/{agents,skills}/` — todos presentes com `__init__.py` nos pacotes
  Python.
- A auto-referência inerente a esta spec (ela define o processo do qual a
  própria auditoria faz parte) foi tratada com transparência: o agente
  `spec-auditor.md` existe, o checklist está fixado, e o `audit.md` está sendo
  gerado conforme o template.

**Sugestões para evolução** (não acionáveis nesta spec):

- Quando Spec 001 for criada, considerar incluir uma task que reaproveite
  `decisions.md` para gerar automaticamente um `STATUS.md` com o estado
  (proposed/accepted) de cada ADR — útil para o vídeo de demonstração.
- À medida que novas specs (001–006) forem geradas, o `spec-auditor` deve
  cruzar referências entre elas (a regra "outras specs" do seu próprio escopo).
  Hoje só existe a Spec 000, então a auditoria cruzada é trivialmente vazia.

**Veredito final**: A spec está sólida e pode ser aprovada com as ressalvas
acima. Recomenda-se que o mantenedor humano endereçe ao menos as ressalvas 1 e 2
(pequenas edições de clareza) antes da aprovação canônica `aprovo a spec 000`;
as demais podem ser absorvidas pelas próximas specs.
