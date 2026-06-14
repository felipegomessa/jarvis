"""Exceções do módulo de aprendizado — Spec 007."""

from __future__ import annotations


class LearningError(Exception):
    """Falha tratável na geração/correção de provas (ex.: JSON inválido do LLM)."""
