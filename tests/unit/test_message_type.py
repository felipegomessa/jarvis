"""Testes dos tipos compartilhados em src/llm/types.py."""

from __future__ import annotations

from src.llm.types import Message, Role


def test_message_typed_dict_shape() -> None:
    m: Message = {"role": "user", "content": "olá"}
    assert m["role"] == "user"
    assert m["content"] == "olá"


def test_roles_are_literal() -> None:
    # Apenas garantir que as constantes existem e podem ser usadas
    valid: list[Role] = ["system", "user", "assistant", "tool"]
    assert len(valid) == 4
