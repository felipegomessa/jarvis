"""Hierarquia de exceções do cliente LLM — RF-001.9.

Permite tratamento granular na UI (D-017 degraded mode) e no agent loop (Spec 005).
"""


class LLMError(Exception):
    """Base de todas as exceções do cliente LLM."""


class LLMAuthError(LLMError):
    """401/403 — token inválido ou ausente. NÃO re-tenta."""


class LLMRequestError(LLMError):
    """4xx (exceto 401/403/429) — pedido malformado. NÃO re-tenta."""


class LLMTimeoutError(LLMError):
    """Timeout ou erro de conexão de rede. Re-tenta via tenacity."""


class LLMServerError(LLMError):
    """5xx — erro do servidor. Re-tenta via tenacity."""
