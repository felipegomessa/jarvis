"""Estado de saúde do LLM (degraded mode) — RF-001.7 / ADR D-017.

Singleton em memória, thread-safe via threading.Lock. UI consulta este estado
para mostrar banner OFFLINE quando o endpoint LIA UFMS está indisponível.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Literal

LLMHealthStatus = Literal["ONLINE", "OFFLINE", "UNKNOWN"]


@dataclass
class LLMHealth:
    status: LLMHealthStatus = "UNKNOWN"
    last_check: datetime | None = None
    last_error: str | None = None


_state = LLMHealth()
_lock = Lock()


def get_health() -> LLMHealth:
    """Retorna cópia do estado atual (thread-safe)."""
    with _lock:
        return LLMHealth(_state.status, _state.last_check, _state.last_error)


def set_health(status: LLMHealthStatus, error: str | None = None) -> None:
    """Atualiza o estado (thread-safe)."""
    with _lock:
        _state.status = status
        _state.last_check = datetime.now(UTC)
        _state.last_error = error


def reset_health_for_tests() -> None:
    """Reseta para o estado inicial (apenas testes)."""
    with _lock:
        _state.status = "UNKNOWN"
        _state.last_check = None
        _state.last_error = None
