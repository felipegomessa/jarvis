"""Entry point do JARVIS Academico — inicia a UI NiceGUI."""

from __future__ import annotations

import sys

from loguru import logger


def main() -> int:
    try:
        from src.ui.app import run

        run()
    except Exception:
        logger.exception("falha ao iniciar a UI")
        return 1
    return 0


if __name__ in {"__main__", "__mp_main__"}:
    sys.exit(main())
