"""Smoke test do GemmaClient com endpoint real — T-001.15.

Marcado `live_llm`: roda APENAS quando JARVIS_RUN_LIVE_LLM=1.
Default: skipped (não queima token em CI/local).
"""

from __future__ import annotations

import pytest

from src.core.config import get_settings
from src.llm import GemmaClient

pytestmark = pytest.mark.live_llm


@pytest.mark.asyncio
async def test_healthcheck_real_endpoint() -> None:
    settings = get_settings()
    client = GemmaClient(settings)
    ok = await client.healthcheck()
    assert ok is True


@pytest.mark.asyncio
async def test_complete_chat_real_endpoint() -> None:
    settings = get_settings()
    client = GemmaClient(settings)
    resp = await client.complete_chat(
        [{"role": "user", "content": "Diga 'olá' em uma palavra."}],
        max_tokens=20,
    )
    assert isinstance(resp, str)
    assert len(resp) > 0


@pytest.mark.asyncio
async def test_stream_chat_real_endpoint() -> None:
    settings = get_settings()
    client = GemmaClient(settings)
    tokens: list[str] = []
    async for tok in client.stream_chat(
        [{"role": "user", "content": "Conte de 1 a 3."}],
        max_tokens=30,
    ):
        tokens.append(tok)
    assert len(tokens) > 0
    joined = "".join(tokens)
    assert len(joined) > 0
