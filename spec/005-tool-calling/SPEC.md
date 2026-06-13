# Spec 005 — Tool Calling (Agent Loop) — REQUISITO OBRIGATORIO DO TRABALHO

> **Modo MVP**: spec consolidada. Esta spec entrega o **requisito obrigatorio
> de tool calling**: 5+ tools, decisao tomada pela LLM (nao por logica fixa),
> e logs estruturados (tool, input, output) — exigidos no enunciado §4.

## Tools obrigatorias (5+)

1. **consultar_agenda(periodo, kind?)** — periodo in {hoje, amanha, semana, agora}.
2. **listar_tarefas(status?, somente_atrasadas?)** — filtra por pending/done.
3. **adicionar_tarefa(title, description?, due_at?, priority?)**.
4. **concluir_tarefa(task_id)**.
5. **buscar_material_rag(pergunta)** — RAG da Spec 002.

Extras (diferencial):
6. **adicionar_evento(title, starts_at, ends_at?, kind?, location?, description?)**.
7. **listar_materiais()** — lista documentos ingeridos.

## Arquitetura

```
src/tools/
├── __init__.py
├── registry.py     # ToolDefinition, ToolRegistry, build_system_prompt
├── tool_agenda.py
├── tool_tasks.py
├── tool_rag.py
└── tool_materials.py

src/llm/
└── agent.py        # AgentLoop com decisao prompt-based JSON
```

## Fluxo (D-007 prompt-based JSON + D-015 audit)

```
1. user_message recebido
2. monta system_prompt = "Voce e JARVIS. Tools disponiveis: ..."
                       + lista de tools com schema JSON
                       + instrucao: responda com JSON {"tool": ..., "args": ...}
                         OU {"reply": "<resposta direta>"}
3. messages = [system, history..., user]
4. LOOP (max 5 iteracoes):
   a. llm_response = gemma.complete_chat(messages)
   b. parse JSON
   c. SE {"reply": "..."} -> yield resposta, BREAK
   d. SE {"tool": name, "args": {...}}:
      - log inicio (timestamp)
      - try execute_tool(name, args)
      - log fim (log_tool_call em SQLite: tool, input_json, output_json,
                 status, error, duration_ms)
      - append messages: assistant({"tool":...}) + user(observation: result_json)
      - continue
   e. SE JSON malformado: 1 retry com mensagem corretiva, depois fallback
5. SE max_iterations atingido sem reply: retorna ultimo observation como texto.
```

## Cenarios de erro

- JSON malformado da LLM → re-prompt com erro de parsing; se 2 falhas, retorna
  fallback "Nao consegui processar sua pergunta. Tente reformular."
- Tool nao existe → observacao "ERRO: tool 'X' nao existe; tools disponiveis: [...]".
- Tool levanta excecao → log status='error'; observacao "ERRO ao executar X: <msg>".
- Max iterations atingido → resposta de fallback.

## Testes

- `test_registry.py` (unit) — registro + lookup de tools.
- `test_tools_smoke.py` (integration) — cada tool individualmente.
- `test_agent_loop.py` (integration com FakeLLM) — simula sequencia de respostas
  e verifica que tool calls sao executadas + loggadas + injetadas.

## DoD

- [ ] `src/tools/*.py` (5+ tools + registry).
- [ ] `src/llm/agent.py` (AgentLoop).
- [ ] Tabela `tool_call_logs` recebe inserts a cada chamada.
- [ ] Testes verdes.
