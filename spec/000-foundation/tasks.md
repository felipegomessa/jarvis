# Spec 000 — Foundation — Tasks

> Ordem por dependência. `[P]` = pode rodar em paralelo com a anterior.

## T-000.1 — Criar constituição (CLAUDE.md)

- Criar `CLAUDE.md` com §1 Visão, §2 Princípios, §3 Stack, §4 Estrutura,
  §5 Processo SDD, §6 Convenções, §7 Testes, §8 Erros, §9 IAs, §10 Checklist, §11 Continuidade.
- **Status**: ✅ Concluída.

## T-000.2 — Criar registro de decisões (decisions.md) [P]

- Documentar D-001 a D-011 com contexto, decisão, alternativas, consequências.
- **Status**: ✅ Concluída.

## T-000.3 — Criar subagente auditor (.claude/agents/spec-auditor.md) [P]

- Definir checklist de auditoria, formato do relatório, princípios.
- **Status**: ✅ Concluída.

## T-000.4 — Criar configurações Claude (.claude/settings.json) [P]

- Permissões básicas para uv, python, pytest, ruff, git.
- **Status**: ✅ Concluída.

## T-000.5 — Criar pyproject.toml (uv)

- Definir Python 3.12, dependências (openai, sentence-transformers, sqlite-vec,
  pdfplumber, pydantic, pydantic-settings, loguru, python-dotenv, nicegui,
  python-dateutil) e dev deps (pytest, ruff, mypy).
- Configurar ruff, pytest, mypy.
- **Status**: ✅ Concluída.

## T-000.6 — Criar .gitignore [P]

- Cobrir: __pycache__, .venv, .env (mas não .env.example), *.db, *.log, modelos
  cache, IDE.
- **Status**: ✅ Concluída.

## T-000.7 — Criar .env.example [P]

- Documentar TODAS as variáveis `JARVIS_*` com defaults sensatos e placeholder
  para o token.
- **Status**: ✅ Concluída.

## T-000.8 — Criar estrutura de diretórios e __init__.py

- `src/{core, llm, rag, domain/agenda, domain/tasks, tools, ui/views}`.
- `tests/{unit, integration}`.
- `data/`, `logs/`, `.claude/skills/`, `spec/000-foundation/`.
- `src/__init__.py` com `__version__`. `src/main.py` placeholder.
- **Status**: ✅ Concluída.

## T-000.9 — Criar README.md [P]

- Visão geral, funcionalidades, stack resumida, setup (uv sync), estrutura de pastas,
  IAs utilizadas, equipe, licença.
- **Status**: ✅ Concluída.

## T-000.10 — Criar data/README.md [P]

- Inventário do dataset (vazio inicialmente), estratégia de chunking (referência a
  D-006), limitações, procedência.
- **Status**: ✅ Concluída.

## T-000.11 — Auditoria pela `spec-auditor`

- Invocar subagente `spec-auditor` com a pasta `spec/000-foundation/`.
- Salvar output em `spec/000-foundation/audit.md`.
- Resolver bloqueadores se houver.
- **Status**: ⏳ Pendente.

## T-000.12 — Aprovação humana

- Mantenedor lê audit.md e a spec. Aprova explicitamente com
  `aprovo a spec 000`.
- **Status**: ⏳ Pendente.

## T-000.13 — Setup do venv via uv (validação + smoke test)

- Rodar `uv sync` para criar `.venv` e gerar `uv.lock`.
- Validar que todas as deps instalam sem erro.
- **Smoke test de reprodutibilidade**: rodar
  `uv run python -c "import src; print(src.__version__)"` — deve imprimir `0.1.0`.
- Commitar `uv.lock`.
- **Status**: ⏳ Pendente (depende de aprovação humana).

## T-000.14 — Inicializar git e fazer commit inicial

- `git init` (caso ainda não seja repo).
- `git add` + `git commit` com mensagem "spec(000): foundation scaffolding".
- Configurar remote para GitHub (futuro).
- **Status**: ⏳ Pendente (aguardando decisão do usuário sobre quando inicializar git).
