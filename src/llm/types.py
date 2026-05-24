"""Tipos compartilhados pelo módulo LLM — RF-001.9."""

from typing import Literal, TypedDict

Role = Literal["system", "user", "assistant", "tool"]


class Message(TypedDict):
    """Mensagem no formato OpenAI Chat Completions."""

    role: Role
    content: str
