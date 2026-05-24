"""Configuração do logging via loguru — RF-001.5 / ADR D-010.

Dois sinks: stderr colorido (interativo) e arquivo rotativo diário em
`<log_dir>/jarvis-{date}.log`. Idempotente: chamar duas vezes não dobra handlers.
"""

import sys
from pathlib import Path

from loguru import logger

_CONFIGURED = False


def configure_logging(log_level: str = "INFO", log_dir: Path = Path("./logs")) -> None:
    """Configura loguru. Chamadas subsequentes na mesma sessão são no-op.

    Args:
        log_level: Nível mínimo (DEBUG/INFO/WARNING/ERROR/CRITICAL).
        log_dir: Diretório para arquivos rotativos diários.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    logger.remove()  # remove handlers default

    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{line}</cyan> | "
            "{message}"
        ),
    )

    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "jarvis-{time:YYYY-MM-DD}.log",
        level=log_level,
        rotation="00:00",  # rotaciona à meia-noite
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{line} | {message}",
    )

    _CONFIGURED = True


def reset_logging_for_tests() -> None:
    """Reabre a flag para testes possam reconfigurar (NÃO usar em produção)."""
    global _CONFIGURED
    _CONFIGURED = False
    logger.remove()
