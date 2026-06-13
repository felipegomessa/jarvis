# Spec 000 — Foundation

> Esta spec consolida os **requisitos transversais** do projeto JARVIS Acadêmico.
> Não trata de funcionalidade de usuário — trata de **base** sobre a qual as outras
> specs (001–006) serão construídas.

## Contexto

Projeto acadêmico em duplas (Trabalho 1 da disciplina IA — UFMS 2026). Avaliado por
critérios funcionais (RAG, tools, aprendizado), de engenharia (organização, testes,
logs) e de qualidade da entrega (vídeo, README, dataset).

Decisões estratégicas (D-001 a D-011) já tomadas e registradas em
[../../decisions.md](../../decisions.md).

## Requisitos funcionais (meta)

### RF-000.1 — Processo SDD operacional

O projeto deve operar sob Spec-Driven Development:
- Toda feature mora em `spec/NNN-nome/{requirements.md, design.md, tasks.md}`.
- Toda spec passa por auditoria de `spec-auditor` antes da aprovação humana.
- Toda decisão arquitetural vira ADR em `decisions.md`.

**Critério de aceitação**:
- ✓ Existe `CLAUDE.md` com §5 Processo SDD descrito.
- ✓ Existe `.claude/agents/spec-auditor.md` configurado.
- ✓ Existe `decisions.md` com D-001 a D-011 registradas.

### RF-000.2 — Reprodutibilidade entre máquinas

Qualquer integrante da dupla deve poder clonar o repositório em outra máquina e
recriar o ambiente sem ambiguidade.

**Critério de aceitação**:
- ✓ `pyproject.toml` fixa Python 3.12 e dependências com versões mínimas.
- ✓ `uv.lock` é commitado (criado após primeiro `uv sync`).
- ✓ `.env.example` documenta TODAS as variáveis de ambiente necessárias.
- ✓ README.md explica passo-a-passo do setup.

### RF-000.3 — Estrutura de diretórios definida

Código segue a hierarquia de pastas listada em CLAUDE.md §4.

**Critério de aceitação**:
- ✓ Diretórios criados: `src/{core,llm,rag,domain/{agenda,tasks},tools,ui/views}`, `spec/`,
      `tests/{unit,integration}`, `data/`, `logs/`.
- ✓ `.claude/{agents,skills}/` criados (`skills/` permanece vazio até demanda surgir).
- ✓ `__init__.py` em cada pacote Python sob `src/` e `tests/`.
- ✓ Regras de dependência entre camadas documentadas (CLAUDE.md §4.1).

### RF-000.4 — Logging configurável

Logging do app (loguru) usa nível controlado por variável de ambiente
(`JARVIS_LOG_LEVEL`).

**Critério de aceitação**:
- ✓ `.env.example` documenta `JARVIS_LOG_LEVEL` (default INFO).
- ✓ `src/core/logging.py` (a ser implementado na Spec 001) lê esta variável.

### RF-000.5 — Secrets protegidos

Token da LLM e qualquer outro segredo nunca é commitado.

**Critério de aceitação**:
- ✓ `.gitignore` contém `.env`, `*.env`, `!.env.example`.
- ✓ `.env.example` tem placeholder explícito (`cole_aqui_o_token_fornecido_pelo_professor`).
- ✓ README orienta o uso.

### RF-000.6 — Auditoria de tool calls será suportada

A base prepara a infraestrutura para que a Spec 005 implemente logs estruturados
em SQLite.

**Critério de aceitação**:
- ✓ `decisions.md` D-010 fixa a política.
- ✓ Spec 001 (próxima) cria a tabela `tool_call_logs`.

## Critérios de qualidade transversais (aplicam-se a TODAS as specs)

- **CT-1**: Toda função pública tem type hints.
- **CT-2**: Toda função pública não trivial tem docstring breve.
- **CT-3**: Toda exceção tratada loga em nível apropriado.
- **CT-4**: Nenhum `print()` em código de produção (usar `logger`).
- **CT-5**: Nenhum `except:` nu — sempre `except <Class>:`.
- **CT-6**: Imports respeitam camadas (CLAUDE.md §4.1).
- **CT-7**: PEP 8 / ruff sem erros.

## Fora de escopo (não-objetivos)

- **NÃO** será implementado deploy em nuvem, CI/CD, containers — projeto roda local.
- **NÃO** haverá autenticação ou multi-usuário (assume-se 1 usuário por instância).
- **NÃO** será implementada internacionalização (i18n) — apenas PT-BR na UI.
- **NÃO** será implementado backup automático do SQLite — usuário faz manualmente.
- **NÃO** haverá migration framework — schema é versionado em SQL único (Spec 001).
- **NÃO** será suportado OCR de PDFs scaneados.
- **NÃO** será suportada importação de Google Calendar / iCal (agenda é manual).
- **NÃO** haverá testes de UI (NiceGUI) automatizados — validação manual no vídeo.

## Trabalho 2 (futuro — fora do escopo desta entrega)

- Funcionalidade 3.4 (Planejamento de estudos integrando agenda + tarefas + materiais).
- ≥2 funcionalidades de aprendizado (1 interativa: o sistema pergunta e avalia).
- Avaliação com ≥10 perguntas (correta / parcial / incorreta).
- Análise de erros (≥3 falhas: tipo, causa, solução).
