"""Testes de src/core/config.py — T-001.13."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.config import Settings, get_settings


def test_settings_loads_from_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_LLM_API_KEY", "test-token-abc")
    monkeypatch.setenv("JARVIS_LLM_TIMEOUT_S", "30")
    monkeypatch.setenv("JARVIS_CHUNK_SIZE", "500")
    monkeypatch.setenv("JARVIS_UI_DARK", "false")

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.llm_api_key == "test-token-abc"
    assert s.llm_timeout_s == 30.0
    assert s.chunk_size == 500
    assert s.ui_dark is False


def test_settings_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JARVIS_LLM_API_KEY", raising=False)
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None)  # type: ignore[call-arg]
    # mensagem deve apontar para llm_api_key
    assert "llm_api_key" in str(excinfo.value).lower()


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_LLM_API_KEY", "x")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.llm_model == "google/gemma-3-12b-it"
    assert s.embed_model == "intfloat/multilingual-e5-small"
    assert s.chunk_size == 800
    assert s.chunk_overlap == 150
    assert s.rag_top_k == 5
    assert s.log_level == "INFO"
    assert s.ui_port == 8080
    assert s.ui_host == "127.0.0.1"
    assert s.ui_dark is True


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_LLM_API_KEY", "x")
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b  # mesmo objeto (cache)


def test_settings_chunk_overlap_can_be_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_LLM_API_KEY", "x")
    monkeypatch.setenv("JARVIS_CHUNK_OVERLAP", "0")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.chunk_overlap == 0


def test_settings_temperature_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_LLM_API_KEY", "x")
    monkeypatch.setenv("JARVIS_LLM_TEMPERATURE", "3.0")  # fora do range [0, 2]
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
