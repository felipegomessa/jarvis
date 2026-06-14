"""Registry de tools que a LLM pode chamar.

Cada tool tem: nome, descrição em PT-BR, schema dos parâmetros (dict tipo JSON Schema),
e um handler async. O registry expõe `build_system_prompt()` que gera o trecho
do system message com a lista de tools no formato esperado pela LLM (D-007).
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters_schema: dict[str, Any]  # JSON-schema-like
    handler: ToolHandler
    examples: list[dict[str, Any]] | None = None


class ToolRegistry:
    """Registry singleton-friendly de tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool já registrada: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def build_tools_section(self) -> str:
        """Gera o trecho de descrição das tools para o system prompt."""
        lines: list[str] = []
        for t in self._tools.values():
            lines.append(f"### Tool: `{t.name}`")
            lines.append(t.description)
            lines.append("Parâmetros (JSON):")
            lines.append("```json")
            lines.append(json.dumps(t.parameters_schema, ensure_ascii=False, indent=2))
            lines.append("```")
            if t.examples:
                lines.append("Exemplos:")
                for ex in t.examples:
                    lines.append("```json")
                    lines.append(json.dumps(ex, ensure_ascii=False))
                    lines.append("```")
            lines.append("")
        return "\n".join(lines)


def build_system_prompt(registry: ToolRegistry) -> str:
    """System prompt completo para o agent loop.

    Instruções:
    - LLM SEMPRE responde com JSON único (sem texto antes/depois).
    - Forma 1: {"tool": "nome", "args": {...}} para invocar tool.
    - Forma 2: {"reply": "texto da resposta"} quando já tiver info suficiente.
    """
    tools_section = registry.build_tools_section()
    tool_names = ", ".join(f"`{n}`" for n in registry.names())
    return (
        "Você é JARVIS, um assistente acadêmico para estudantes. Você pode usar "
        "ferramentas (tools) para consultar a agenda, lista de tarefas e materiais "
        "de estudo do usuário.\n\n"
        f"Tools disponíveis: {tool_names}.\n\n"
        "REGRAS DE RESPOSTA (obrigatórias):\n"
        "1. Você deve sempre responder com UM único objeto JSON válido, sem texto "
        "antes ou depois. Sem markdown, sem prefixo, sem sufixo.\n"
        "2. Para chamar uma tool, use:\n"
        '   {"tool": "nome_da_tool", "args": {...argumentos JSON...}}\n'
        "3. Quando você já tem informação suficiente para responder ao usuário, "
        "responda com:\n"
        '   {"reply": "sua resposta final em português, citando fontes quando aplicável"}\n'
        "4. Você pode chamar várias tools em sequência (uma por vez). O resultado de "
        "cada tool vira como observação na próxima rodada.\n"
        "5. NUNCA invente dados. Se a tool retornar vazio, diga ao usuário que não "
        "encontrou.\n"
        "6. Responda em português do Brasil.\n"
        "7. Para perguntas conceituais sobre materiais de estudo (ex: 'explique X', "
        "'resuma Y'), use `buscar_material_rag` e responda APENAS com base nos "
        "trechos retornados, citando a fonte como [Doc N: título]. Se o resultado "
        "indicar `no_relevant_context` ou vier vazio, diga que não encontrou "
        "material relevante — não use conhecimento externo.\n\n"
        "DICA importante (Agenda vs Tarefas): use `adicionar_evento` quando o usuário "
        "descrever algo que ACONTECE em horário fixo (aula, prova, reunião, palestra). "
        "Use `adicionar_tarefa` quando ele descrever algo que ELE PRECISA FAZER até um "
        "prazo (estudar, escrever, entregar trabalho, ler capítulo). Em caso de dúvida, "
        "pergunte ao usuário antes de decidir.\n\n"
        "Lista de tools com seus schemas:\n\n"
        f"{tools_section}\n"
        "Lembrete: sua próxima mensagem deve ser APENAS um JSON válido."
    )


# Registry global (singleton por processo)
_global_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Retorna registry global (criando lazy + populando com tools default)."""
    global _global_registry
    if _global_registry is not None:
        return _global_registry
    _global_registry = ToolRegistry()
    # Importa módulos que registram as tools (registro automático ao importar).
    from src.tools import (  # noqa: F401 — imports têm efeito colateral de registro
        tool_agenda,
        tool_calendar,
        tool_learning,
        tool_materials,
        tool_rag,
        tool_tasks,
    )

    return _global_registry


def reset_registry_for_tests() -> None:
    """Limpa o registry global (apenas testes)."""
    global _global_registry
    _global_registry = None
