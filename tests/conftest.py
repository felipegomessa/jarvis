"""Fixtures globais e hooks de pytest — RF-001.8 / ADR D-019."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

from src.core.db import apply_migrations, get_connection
from src.llm.types import Message

# ============================================================
# Hook: skip de testes marcados `live_llm` quando flag desligada
# ============================================================

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("JARVIS_RUN_LIVE_LLM") == "1":
        return
    skip_marker = pytest.mark.skip(
        reason="live_llm: defina JARVIS_RUN_LIVE_LLM=1 para rodar"
    )
    for item in items:
        if "live_llm" in item.keywords:
            item.add_marker(skip_marker)


# ============================================================
# Fixtures de DB
# ============================================================

@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Caminho para um SQLite temporário (criado vazio)."""
    return tmp_path / "jarvis-test.db"


@pytest.fixture
def tmp_db(tmp_db_path: Path) -> Iterator[sqlite3.Connection]:
    """Conexão a um SQLite temporário com migrations aplicadas."""
    with get_connection(tmp_db_path) as conn:
        apply_migrations(conn)
        yield conn


# ============================================================
# Fixtures de LLM
# ============================================================

@pytest.fixture
def sample_messages() -> list[Message]:
    return [
        {"role": "system", "content": "Você é um assistente acadêmico."},
        {"role": "user", "content": "Olá, explique embeddings em uma frase."},
    ]


class FakeLLM:
    """Stub de GemmaClient para testes — não bate em endpoint algum.

    Programe a sequência de respostas e o stub as retorna em ordem.
    """

    def __init__(
        self,
        scripted_completions: list[str] | None = None,
        scripted_streams: list[list[str]] | None = None,
        healthy: bool = True,
    ) -> None:
        self.scripted_completions = list(scripted_completions or [])
        self.scripted_streams = list(scripted_streams or [])
        self.healthy = healthy
        self.calls: list[tuple[str, list[Message]]] = []

    async def complete_chat(
        self, messages: list[Message], max_tokens: int | None = None
    ) -> str:
        self.calls.append(("complete", list(messages)))
        if not self.scripted_completions:
            return ""
        return self.scripted_completions.pop(0)

    async def stream_chat(
        self, messages: list[Message], max_tokens: int | None = None
    ) -> AsyncIterator[str]:
        self.calls.append(("stream", list(messages)))
        if not self.scripted_streams:
            return
        tokens = self.scripted_streams.pop(0)
        for tok in tokens:
            yield tok

    async def healthcheck(self, timeout_s: float = 5.0) -> bool:
        return self.healthy


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()
