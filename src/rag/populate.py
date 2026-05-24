"""CLI auxiliar para popular o RAG a partir de /data — RF-002.10.

Uso:
    python -m src.rag.populate
    python -m src.rag.populate ./outra_pasta
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from src.core.config import get_settings
from src.core.db import apply_migrations, get_connection, smoke_check_vec
from src.core.logging import configure_logging
from src.rag.ingest import ingest_directory


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    dir_path = Path(args[0]) if args else Path("./data")

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_dir)

    logger.info(f"populate: ingerindo arquivos de {dir_path}")

    with get_connection() as conn:
        smoke_check_vec(conn)
        apply_migrations(conn)

    results = ingest_directory(dir_path)
    if not results:
        logger.warning("nenhum arquivo processado")
        return 1

    ingested = [r for r in results if r.status == "ingested"]
    skipped = [r for r in results if r.status == "skipped"]
    errors = [r for r in results if r.status == "error"]

    logger.info(
        f"RESUMO: {len(ingested)} ingested, {len(skipped)} skipped, "
        f"{len(errors)} errors"
    )
    if errors:
        for r in errors:
            logger.warning(f"  ERR  {r.source_path}: {r.reason} ({r.error})")

    # MVP: não falhar exit code só por erros parciais (ingest_directory é best-effort)
    return 0


if __name__ == "__main__":
    sys.exit(main())
