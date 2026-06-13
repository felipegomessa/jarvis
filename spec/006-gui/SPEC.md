# Spec 006 — GUI NiceGUI (MVP)

> **Modo MVP**: spec consolidada e enxuta. Foco em demonstrar todas as features
> em uma interface coesa para o video do trabalho.

## Layout

```
+--------------------------------------------------------+
| JARVIS Academico         [LLM ONLINE/OFFLINE banner]   |
+--------------------------------------------------------+
| Tabs: [Chat] [Agenda] [Tarefas] [Materiais] [Auditoria]|
+--------------------------------------------------------+
|                                                        |
| (conteudo da tab selecionada)                          |
|                                                        |
+--------------------------------------------------------+
```

## Tabs

### Chat
- ScrollArea com mensagens (user + assistant + tool events).
- Input + botao Enviar.
- Cada interacao usa `AgentLoop.respond(user_msg)`.
- Tool calls aparecem como cards expandidos: "[tool] consultar_agenda(...) -> X events".
- Citacoes de RAG aparecem como chips clicaveis no final da resposta.

### Agenda
- Lista de eventos hoje / esta semana.
- Form simples para adicionar evento (titulo, data/hora, tipo, local).
- Botao excluir.

### Tarefas
- Lista pendentes + concluidas.
- Checkbox para marcar concluida.
- Form para adicionar (titulo, prazo, prioridade).
- Indicador de atrasadas em vermelho.

### Materiais
- Upload de arquivos (.pdf/.txt/.md).
- Lista de documentos ingeridos.
- Botao "Indexar pasta /data" (chama populate).

### Auditoria (diferencial)
- Tabela com todas as linhas de tool_call_logs.
- Filtros por tool, status, data.

## Erros / Degraded mode

- Banner persistente no topo se `LLMHealth.status == 'OFFLINE'`.
- Tabs Chat e Materiais (RAG) mostram bloqueio quando offline.
- Agenda e Tarefas continuam funcionando offline (D-017).

## Arquivos

```
src/ui/
├── app.py                  # entry point, monta NiceGUI app
├── state.py                # estado global (gemma client, agent, etc.)
├── views/
│   ├── chat.py
│   ├── agenda.py
│   ├── tasks.py
│   ├── materials.py
│   └── audit.py
```

## DoD

- [ ] `uv run python -m src.main` inicia o servidor NiceGUI.
- [ ] Todas as 5 tabs renderizam.
- [ ] Chat envia para AgentLoop e exibe respostas.
- [ ] Tabs Agenda/Tarefas/Materiais fazem CRUD basico.
