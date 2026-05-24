"""Testes de src/core/logging.py — T-001.13."""

from __future__ import annotations

from pathlib import Path

import pytest
from loguru import logger

from src.core.logging import configure_logging, reset_logging_for_tests


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    reset_logging_for_tests()
    yield
    reset_logging_for_tests()


def test_configure_logging_creates_log_dir(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    configure_logging(log_level="INFO", log_dir=log_dir)
    assert log_dir.exists()
    assert log_dir.is_dir()


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    configure_logging(log_level="INFO", log_dir=log_dir)
    n1 = len(logger._core.handlers)  # type: ignore[attr-defined]
    configure_logging(log_level="INFO", log_dir=log_dir)
    n2 = len(logger._core.handlers)  # type: ignore[attr-defined]
    assert n1 == n2, f"chamar 2 vezes dobrou handlers ({n1} -> {n2})"


def test_configure_logging_emits_to_file(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    configure_logging(log_level="DEBUG", log_dir=log_dir)
    logger.info("teste-marcador-001-logging")
    # Força flush (loguru não tem flush() público; basta um sleep curto OU
    # checar que algum .log existe no diretório)
    log_files = list(log_dir.glob("jarvis-*.log"))
    assert len(log_files) >= 1
    # Lê o conteúdo do log mais recente
    content = log_files[0].read_text(encoding="utf-8")
    assert "teste-marcador-001-logging" in content
