# NOTES — Conceitos não-óbvios, gotchas e aprendizados

> Documento complementar ao `HANDOFF.md`. Aqui registro o **porquê** de
> decisões que podem parecer estranhas em retrospectiva, gotchas que custaram
> tempo, e conceitos que vale a pena revisar antes de mexer em áreas
> sensíveis.

---

## 1. Por que sqlite-vec e não LangChain/ChromaDB?

**Decisão**: D-003 (sqlite-vec).

**Por quê**: O enunciado do trabalho diz "o grupo deve implementar
explicitamente: RAG, integração com LLM, tool calling". Framework grande
(LangChain, LlamaIndex) esconde demais o pipeline e contraria o espírito da
avaliação. ChromaDB introduziria um diretório lateral de banco — preferimos
"tudo em um único arquivo SQLite" para deploy simples.

**Consequência**: pipeline RAG é nosso, manual, ~200 linhas em
`src/rag/{ingest,chunk,embed,retrieve,prompt,pipeline}.py`. Vantagem: dá
para explicar ao professor linha por linha.

**Não recomendado**: tentar trocar para LangChain agora — quebraria 5+
arquivos e a justificativa pedagógica.

---

## 2. Por que prompt-based JSON tool calling em vez de OpenAI tools= nativo?

**Decisão**: D-007.

**Por quê**: O endpoint LIA UFMS (`https://llm.liaufms.org/v1/gemma-3-12b-it`)
é OpenAI-compatible mas **não documenta suporte ao parâmetro `tools=`**.
Testar e descobrir que não funciona no dia da entrega seria desastre.

Prompt-based é determinístico: nós construímos o system prompt com a lista
de tools (formato JSON Schema dentro de ```json blocks), instruímos a LLM a
responder SEMPRE com `{"tool": ..., "args": ...}` ou `{"reply": "..."}`,
parseamos o JSON e executamos.

**Custo**: ~100 linhas a mais (`src/llm/agent.py` + `_parse_json_response`).
**Benefício**: funciona com qualquer endpoint OpenAI-compatible, é
auditavelmente correto, e a LLM Gemma 12B responde bem ao formato.

**Gotcha**: às vezes a LLM envelopa o JSON em ```json ... ``` (markdown).
Por isso `_parse_json_response` tem fallback que strip de code fences +
busca primeiro `{` até último `}`.

---

## 3. Por que VIEW SQL para o calendário em vez de query Python?

**Decisão**: D-025.

**Por quê**: A LLM/UI precisa de uma "lista única ordenada por data de
eventos+tarefas". Opções:

1. ❌ **Tabela polimórfica** (`calendar_items` com colunas opcionais): breaking
   change, quebra D-009 (Pydantic models existentes para Event e Task).
2. ❌ **2 queries + merge em Python**: mais código no agent loop, ordenação
   complica.
3. ✅ **VIEW SQL UNION ALL**: zero impacto nos repos existentes, queries
   simples no service (`SELECT * FROM calendar_items_view WHERE
   starts_at >= ?`).

**Insight**: VIEWs em SQLite são read-only mas nada impede que CRUD continue
pelos repos `agenda/repo.py` e `tasks/repo.py`. A view é só uma "lente"
unificada.

**Gotcha**: a view filtra `WHERE due_at IS NOT NULL` para tarefas. Tarefas
sem prazo NÃO aparecem no calendário (só na "Lista de tarefas" pura). Foi
decisão consciente — uma tarefa sem prazo não tem onde aparecer no grid
mensal sem um "dia mágico" (today, end-of-week, etc.).

---

## 4. Por que session_id é OPCIONAL no AgentLoop?

**Decisão**: D-024.

**Por quê**: Backward-compatibility. Os testes existentes em
`tests/integration/test_agent_loop.py` foram escritos antes de existirem
chat sessions. Tornar `session_id` obrigatório quebraria tudo.

Solução: `AgentLoop.respond(user_message, history=None, session_id=None)`.
Se `session_id is None`, modo "efêmero" — não grava nada no SQLite.
Se fornecido, grava user/assistant/tool em `chat_messages`.

**Onde é usado obrigatoriamente**: `src/ui/components/chat_view.py::_handle_send`
— sempre cria sessão se ainda não há (via `start_session_with_first_message`)
e passa session_id.

**Onde é None**: todos os testes de agent loop com ScriptedLLM
(`tests/integration/test_agent_loop.py`).

---

## 5. Por que `_strip_accents` no tool_agenda?

**Gotcha real**: A LLM Gemma 12B foi instruída no system prompt a responder
com enum `"amanhã"` (com til). Mas em testes empíricos, ela às vezes manda
`"amanha"` sem til (provavelmente cópia de exemplos antigos do treinamento).

Solução: `unicodedata.normalize("NFD", s)` + filter de marcas combinantes.
Aceita ambas as formas mas a estrutura interna usa sempre sem acento para
comparação (`if periodo == "amanha"`).

Aplicado SÓ no `_consultar_agenda`. Outras tools (tool_tasks) recebem
parâmetros já estruturados (priority int, status enum simples) — não têm
esse problema.

---

## 6. Por que NICEGUI 3.x exige @ui.page com tudo dentro?

**Gotcha grande**: A primeira versão da UI tinha `ui.dark_mode().enable()` e
`ui.colors(...)` no escopo do módulo, ANTES de `ui.run()`. NiceGUI 3.x
levanta `RuntimeError: ui.page cannot be used in NiceGUI scripts when UI
is defined in the global scope`.

**Causa**: NiceGUI 3.x escolheu um de dois modos:
- "Script mode": tudo no escopo global, sem `@ui.page` (modo dev rápido).
- "Page mode": tudo dentro de `@ui.page("/")` (modo prod, multi-page).

Misturar os dois explode.

**Fix**: tudo de `apply_theme()` e `ui.colors()` agora está DENTRO da
função decorada com `@ui.page("/")` (`src/ui/app.py::index_page()`).

**Side effect bom**: a configuração roda por client (cada usuário que abre
a página pega o tema). Para o nosso caso single-user é equivalente, mas é
o padrão correto.

---

## 7. Por que `ui.html('<div>...XY</div>')` para avatar?

**Gotcha**: Tentei usar `ui.avatar(...)` e `ui.element('q-avatar')` para
mostrar iniciais "ES" em fundo verde. Nenhum tem prop nativa para "texto
interno" — Quasar `q-avatar` aceita só `icon=`.

Tentativas que falharam:
1. `ui.avatar(icon='person').props('color="green"')` — mostra ícone, não texto.
2. `ui.element('q-avatar')` + child `ui.label(...)` — o slot default não
   recebe filhos corretamente em NiceGUI 3.x sem hack.
3. `ui.avatar(text='ES')` — não existe parâmetro `text`.

Solução: `ui.html(f'<div style="background:...;...">{XY}</div>')` — HTML
puro com CSS inline. Total controle, zero magia.

---

## 8. Por que migration runner usa loop em vez de `executescript`?

**Gotcha CRÍTICO** (bloqueador da auditoria da Spec 001):
`conn.executescript(sql)` em Python `sqlite3` **emite um COMMIT implícito
ANTES de executar o script**. Isso significa:

```python
conn.execute("BEGIN")           # abre transação
conn.executescript(migration_sql)  # COMMIT implícito + executa
# se der erro aqui, ROLLBACK é no-op (transação já fechou)
conn.execute("ROLLBACK")        # inútil
```

Resultado: rollback NÃO desfaz nada. Statements parciais persistem.

**Fix**: `_split_statements(sql)` (split por `;` removendo `-- comentários`)
+ loop `for stmt in statements: conn.execute(stmt)`. Cada statement vai
dentro do `BEGIN/COMMIT/ROLLBACK` manual, e atomicidade fica de verdade.

**Teste que prova**: `tests/integration/test_db_migrations.py::test_atomicity_rollback_on_broken_migration`
— injeta migration com 2º stmt inválido, verifica que o 1º não persiste.

---

## 9. Por que healthcheck timeout = 15s e não 5s?

**Histórico**: Versão inicial usava 5s. Em smoke test real (token válido,
endpoint LIA UFMS), o healthcheck deu timeout. App caiu em OFFLINE
indevidamente.

**Causa provável**: cold start do endpoint Gemma do LIA UFMS — primeira
request pode levar 8-12s.

**Fix**: aumentei para 15s no `app.py::_bootstrap`. App-wide LLM timeout
(`JARVIS_LLM_TIMEOUT_S`) continua 60s para chamadas reais.

**Consequência**: boot da app demora ~15s no pior caso. Aceitável para
demo.

---

## 10. Por que persistir tool calls com metadata?

**Decisão dentro de D-024**: ao persistir mensagens em `chat_messages`, o
role `tool` guarda no `metadata_json`:

```json
{
  "tool": "listar_tarefas",
  "args": {"status": "pending"},
  "status": "ok",
  "duration_ms": 5,
  "error_msg": null
}
```

E o `content` é o `output_json` (resultado da tool).

**Por quê**: a UI precisa reconstruir o card visual exatamente como era.
`ChatView.load_session()` lê e renderiza:
```python
elif m.role == "tool":
    call_evt = {"tool": meta["tool"], "args": meta["args"]}
    result_evt = {"status": meta["status"], "duration_ms": meta["duration_ms"], "output": json.loads(m.content)}
    render_tool_call(call_evt, result_evt)
```

Sem o metadata, perderíamos o nome da tool e os args (precisaríamos
re-parsear o `output_json` para inferir, o que é frágil).

---

## 11. Por que `tasks/repo.py::list_tasks` ordena tão "estranho"?

```sql
ORDER BY
    CASE WHEN status='pending' THEN 0 ELSE 1 END,
    priority DESC,
    CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,
    due_at ASC
```

**Lógica**:
1. Pendentes primeiro (`status='pending'` → 0), concluídas depois.
2. Dentro de pendentes: maior prioridade primeiro (URGENTE > ALTA > NORMAL).
3. Dentro da mesma prioridade: com prazo primeiro (NULL por último).
4. Dentro de "com prazo": prazo mais próximo primeiro.

**Por que CASE em vez de COALESCE**: SQLite ordena NULL antes de qualquer
valor por default. Para forçar NULL no final, transformo em (0|1) com CASE.

Testes em `test_tasks_repo.py::test_list_ordering_priority_then_due` cobrem.

---

## 12. Por que o chat_view tem `await asyncio.sleep(0)` no loop?

```python
async for event in state.agent.respond(...):
    # render event...
    await asyncio.sleep(0)  # ← isto
```

**Motivo**: cede o controle ao event loop do asyncio para que NiceGUI
processe a fila de updates e mande para o browser via WebSocket. Sem isso,
o loop bloqueia o event loop e o browser só vê o resultado final, perdendo
o efeito de streaming/atualização incremental.

**Pegadinha**: `await asyncio.sleep(0)` não dorme 0ms — ele dorme até o
próximo "yield point" do event loop, o que é exatamente o que queremos.

---

## 13. Por que `notify_sessions_changed()` usa `contextlib.suppress(Exception)`?

```python
for cb in list(_state._on_sessions_changed):
    with contextlib.suppress(Exception):
        cb()
```

**Motivo**: o sidebar registra um callback `refresh_recents` quando é
montado. Mas se o usuário fecha o dialog do calendário (que pode chamar
notify) e o sidebar já foi destruído (page refresh), o callback ainda
existe na lista mas referencia widgets mortos.

`contextlib.suppress(Exception)` evita que um callback morto quebre os
outros callbacks vivos. Em produção real eu rastrearia melhor, mas para o
escopo do trabalho é aceitável.

---

## 14. Por que `tool_call_logs` é separado de `chat_messages`?

**Pergunta natural**: "tool events não já estão em `chat_messages` (role=tool)?
Por que ter `tool_call_logs` também?"

**Respostas**:
- **Auditoria independente de sessão**: o `tool_call_logs` é a fonte oficial
  para o requisito do trabalho ("logs estruturados com ferramenta, entrada,
  saída"). Persiste MESMO se a sessão de chat for deletada.
- **Tool calls efêmeros**: `AgentLoop` sem `session_id` (testes, fluxos
  rápidos) ainda grava em `tool_call_logs`. Não grava em `chat_messages`.
- **Tab Auditoria mostra tudo**: independente de sessão, mostra histórico
  global de tool calls.

Dupla escrita parece redundante mas separa concerns: `chat_messages` = UX;
`tool_call_logs` = audit trail.

---

## 15. Onde estão os logs?

- **Console** (stderr colorido): saída do `python -m src.main`.
- **Arquivo**: `logs/jarvis-{YYYY-MM-DD}.log` (rotação diária, retenção 14
  dias, compactação .zip ao rotacionar).
- **Banco de dados** (auditoria): tabela `tool_call_logs`.

Para olhar logs do dia:
```powershell
Get-Content logs\jarvis-2026-05-24.log -Tail 50 -Wait
```

Para olhar tool calls:
- Via UI: menu "+" → "Pesquisar auditoria".
- Via SQL: `sqlite3 data\jarvis.db "SELECT * FROM tool_call_logs ORDER BY id DESC LIMIT 20"`

---

## 16. Como debug uma chamada de tool que falhou?

1. Abrir UI → "+" → "Pesquisar auditoria".
2. Achar a linha com `status='error'`. Ver `error_msg` e `input_json`.
3. Se for stacktrace, ir em `logs/jarvis-*.log` no mesmo timestamp — o
   `logger.exception(...)` no `AgentLoop` grava tudo.
4. Reproduzir manualmente:
   ```powershell
   .venv\Scripts\python.exe -c "
   import asyncio, json
   from src.tools.registry import get_registry
   reg = get_registry()
   tool = reg.get('listar_tarefas')
   r = asyncio.run(tool.handler({'status': 'pending'}))
   print(json.dumps(r, ensure_ascii=False, indent=2))
   "
   ```

---

## 17. Como adicionar uma nova tool?

1. Criar `src/tools/tool_NOME.py` (copiar de `tool_tasks.py` como template).
2. Implementar `async def _handler(args: dict) -> dict:` com `asyncio.to_thread`
   para operações sync (DB, IO).
3. No final do arquivo, definir `_register()` que chama
   `get_registry().register(ToolDefinition(...))` e invocar `_register()`.
4. Importar o módulo em `src/tools/registry.py::get_registry()` (linha do
   bloco `from src.tools import (...)`).
5. Pronto — a LLM já enxerga no system prompt automaticamente.

---

## 18. Como mudar o limite de iterações do agent loop?

```python
agent = AgentLoop(gemma=client, max_iterations=10)  # default 6
```

Em `src/ui/app.py::_bootstrap` já está fixado em 6. Para mudar
permanentemente, edite lá. Para experimentos, é só passar outro valor.

Cuidado: cada iteração = 1 chamada LLM. Aumentar consome mais token.

---

## 19. Como mudar o threshold de relevância do RAG?

Variável de ambiente `JARVIS_RAG_DISTANCE_THRESHOLD` no `.env` (default 0.6).
Valores menores = mais restritivo (menos resultados, menos hallucination).
Valores maiores = mais permissivo (mais resultados, mais ruído).

0.6 = cosseno (sqlite-vec retorna 1-cos_similarity).
- 0.0 = idênticos
- 0.3 = muito similar
- 0.6 = razoavelmente relevante (escolha equilibrada)
- 1.0 = ortogonal (sem relação)

---

## 20. Por que o título do chat é o primeiro prompt truncado?

`title_from_prompt(prompt, max_chars=60)` em
`src/domain/chat/service.py`.

**Razão**: simplifica drasticamente o UX. ChatGPT também faz isso (com
heurísticas mais sofisticadas, mas o efeito é o mesmo). Alternativa seria
fazer 1 chamada extra à LLM ("gere um título para esta conversa") mas
consome token e demora.

**Melhoria futura**: usar primeiras 2-3 trocas (user + assistant) e gerar
título mais rico via LLM. Marcar como TODO para Trabalho 2.

---

## 21. Por que o calendário não tem visualização Semana/Dia?

**Por enquanto**: só visão Mês. Suficiente para o MVP.

**Adicionar Semana** seria mais um botão no header + render de uma única
"linha" do grid (7 cells) com mais altura. ~40 linhas a mais em
`CalendarMonthView`. Não fiz para manter escopo do plano.

**Adicionar Dia** seria similar — 1 cell vertical com timeline horária.

**Lista** já existe via tab "Lista de tarefas" + "Agenda" (filtros do
calendar_dialog).

---

## 22. Por que removi os tabs antigos?

**Decisão**: D-026. Substituídos por menu "+" e dialogs modais. Razões:

- **ChatGPT-like**: chat é o foco principal, dialogs entram quando precisa.
- **Menos navegação**: usuário não troca de "página" para criar evento.
- **Reuso visual**: o calendário tem 90% mais espaço como dialog
  fullscreen.

Se quiser de volta os tabs (por preferência), o código antigo está no git
history — `src/ui/views/{chat,agenda,tasks,materials,audit}.py`.

---

## 23. Convenções de código (não óbvias)

- **Imports**: ordenados por ruff/isort. Stdlib → third-party → local.
- **Type hints**: obrigatórios em funções públicas. Privadas (`_func`)
  opcionais.
- **Docstrings**: PT-BR, breves (1-3 linhas) em públicas.
- **Logging**: PT-BR nas mensagens visíveis. EN nos identificadores
  técnicos (logger names, error codes).
- **Strings de UI/LLM**: SEMPRE com acentos corretos.
- **Constantes de cor**: `COLOR_*` em UPPER_SNAKE em `src/ui/theme.py`.
- **Nomes de tools**: snake_case PT-BR (`consultar_agenda`,
  `adicionar_evento`) — o que o LLM verá no prompt.
- **Comentários**: explicar PORQUÊ, não O QUÊ. Código óbvio fica sem
  comentário.

---

## 24. Performance / limites conhecidos

- **Modelo embed**: ~120MB carregado em RAM permanente após primeira
  query. Sem warmup explícito (lazy).
- **chunk_vecs**: testado até ~1000 chunks. Cosseno via vec0 é rápido (<10ms).
- **Agent loop**: cada chamada LLM ~1-3s. Com 6 iterações max, pior caso
  ~20s.
- **NiceGUI**: WebSocket update funciona com ~100msg/s sem problema.
- **SQLite**: WAL mode permite leituras concorrentes; writes serializados
  (mas nosso caso single-user, OK).
- **NÃO suporta múltiplos usuários simultâneos** — chat_view e state são
  globais. Para multi-user real, precisaria refatorar.

---

## 25. Filosofia geral do projeto

1. **Não importar magia**: cada peça do RAG / tool calling / chat é nossa.
   Dá para explicar ao professor.
2. **Migrations versionadas**: schema evolutivo, sem framework pesado.
3. **Decisões registradas**: 26 ADRs cobrem 99% do "por quê". Spec SDD
   garante que cada feature foi pensada antes de codada.
4. **Backward-compat onde dá**: features novas (session_id, calendar
   view) não quebram features antigas.
5. **Tests primeiro nas partes críticas**: chunking, parsing JSON, repo
   CRUD, migrations atômicas. UI e LLM real (smoke) opt-in.
6. **Acentuação importa**: trabalho é em PT-BR, UI deve respeitar.
7. **Dark mode premium**: o trabalho fala em "diferencial". Visual conta.
