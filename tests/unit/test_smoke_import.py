"""Smoke test de import — T-001.16 (resolve etapa pós-aprovação da Spec 000)."""

from __future__ import annotations


def test_import_top_level() -> None:
    import src

    assert src.__version__ == "0.1.0"


def test_import_core_modules() -> None:
    import src.core
    import src.core.config
    import src.core.db
    import src.core.health
    import src.core.logging  # noqa: F401


def test_import_llm_modules() -> None:
    import src.llm  # noqa: F401
    from src.llm import (
        GemmaClient,  # noqa: F401
        LLMAuthError,  # noqa: F401
        LLMError,  # noqa: F401
        LLMRequestError,  # noqa: F401
        LLMServerError,  # noqa: F401
        LLMTimeoutError,  # noqa: F401
        Message,  # noqa: F401
        Role,  # noqa: F401
    )
