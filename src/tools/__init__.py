"""Tool registry + 5+ tools que a LLM pode chamar — Spec 005."""

from src.tools.registry import (
    ToolDefinition,
    ToolHandler,
    ToolRegistry,
    build_system_prompt,
    get_registry,
    reset_registry_for_tests,
)

__all__ = [
    "ToolDefinition",
    "ToolHandler",
    "ToolRegistry",
    "build_system_prompt",
    "get_registry",
    "reset_registry_for_tests",
]
