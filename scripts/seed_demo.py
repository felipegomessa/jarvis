"""Popula o banco com dados de demonstração realistas — M3 (plano de melhorias).

Objetivo: deixar a agenda, a lista de tarefas e o acervo RAG com conteúdo
coerente para o **vídeo demo** e para a avaliação, de forma **reproduzível**.

Características:
- **Idempotente**: cada execução remove os dados anteriores marcados com
  `[seed-demo]` antes de reinserir. Rodar N vezes => mesmo estado final.
  NÃO toca em eventos/tarefas criados pelo usuário (sem o marcador).
- **Datas relativas a hoje** (fuso America/Campo_Grande), para que
  "O que tenho hoje?", "Tenho prova amanhã?" e "Aulas esta semana?"
  funcionem em qualquer dia em que o script for executado.
- **Ingestão opcional de `/data`**: reusa `ingest_directory` (idempotente via
  SHA-256), para indexar o dataset acadêmico colocado pelo grupo.

Uso:
    python -m scripts.seed_demo                # semeia agenda+tarefas e ingere ./data
    python -m scripts.seed_demo --no-ingest    # só agenda+tarefas
    python -m scripts.seed_demo --data ./outra # ingere de outra pasta

Melhor demo: rode num dia de semana (seg a sex) para a janela "esta semana"
ficar cheia.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

from src.core.config import get_settings
from src.core.db import apply_migrations, get_connection, smoke_check_vec
from src.core.logging import configure_logging
from src.domain.agenda import EventCreate, create_event
from src.domain.agenda.service import DEFAULT_TZ
from src.domain.tasks import TaskCreate, complete_task, create_task
from src.rag.ingest import ingest_directory

# Sufixo gravado na `description` de tudo que este script cria. É o que torna a
# operação idempotente e segura (nunca apaga dados do usuário).
SEED_MARKER = "[seed-demo]"


def _now_local_naive() -> datetime:
    """Agora no fuso local, SEM tzinfo — consistente com os eventos criados
    pela UI/tools (que armazenam datetimes locais ingênuos)."""
    return datetime.now(DEFAULT_TZ).replace(tzinfo=None, microsecond=0)


def _desc(text: str) -> str:
    return f"{text} {SEED_MARKER}"


def clear_seed(conn: sqlite3.Connection) -> tuple[int, int]:
    """Remove eventos e tarefas previamente semeados. Retorna (n_eventos, n_tarefas)."""
    like = f"%{SEED_MARKER}%"
    ev = conn.execute(
        "DELETE FROM events WHERE description LIKE ?", (like,)
    ).rowcount
    tk = conn.execute(
        "DELETE FROM tasks WHERE description LIKE ?", (like,)
    ).rowcount
    return ev or 0, tk or 0


def seed_events(conn: sqlite3.Connection) -> int:
    """Cria eventos de agenda relativos a hoje. Retorna a quantidade criada."""
    now = _now_local_naive()
    midnight = now.replace(hour=0, minute=0, second=0)
    tomorrow = midnight + timedelta(days=1)
    # Início da semana (segunda 00:00) para preencher "esta semana".
    week_start = midnight - timedelta(days=midnight.weekday())

    specs: list[EventCreate] = [
        EventCreate(
            title="Aula de Inteligência Artificial",
            description=_desc("Tópico: RAG e tool calling com LLMs."),
            starts_at=midnight.replace(hour=14),
            ends_at=midnight.replace(hour=16),
            kind="aula",
            location="Bloco 7 — Sala 12",
        ),
        EventCreate(
            title="Aula de Estatística",
            description=_desc("Revisão de probabilidade para Naive Bayes."),
            starts_at=week_start.replace(hour=8) + timedelta(days=1),
            ends_at=week_start.replace(hour=10) + timedelta(days=1),
            kind="aula",
            location="Bloco 3 — Sala 5",
        ),
        EventCreate(
            title="Prova de Aprendizado de Máquina",
            description=_desc("Conteúdo: regressão logística, embeddings, métricas."),
            starts_at=tomorrow.replace(hour=10),
            ends_at=tomorrow.replace(hour=12),
            kind="prova",
            location="Bloco 7 — Auditório",
        ),
        EventCreate(
            title="Entrega do Trabalho de IA (JARVIS)",
            description=_desc("Código + dataset + vídeo no repositório."),
            starts_at=week_start.replace(hour=23, minute=59) + timedelta(days=4),
            kind="trabalho",
            location="Online (Moodle)",
        ),
    ]

    for ec in specs:
        create_event(conn, ec)
    logger.info(f"seed: {len(specs)} eventos criados")
    return len(specs)


def seed_tasks(conn: sqlite3.Connection) -> int:
    """Cria tarefas (pendentes + uma concluída). Retorna a quantidade criada."""
    now = _now_local_naive()
    midnight = now.replace(hour=0, minute=0, second=0)

    pending: list[TaskCreate] = [
        TaskCreate(
            title="Estudar regressão logística para a prova",
            description=_desc("Foco na função sigmoide e fronteira de decisão."),
            due_at=midnight.replace(hour=22),
            priority=2,
        ),
        TaskCreate(
            title="Resolver lista de exercícios sobre embeddings",
            description=_desc("Questões 1 a 8 da lista 4."),
            due_at=midnight.replace(hour=23, minute=59) + timedelta(days=2),
            priority=1,
        ),
        TaskCreate(
            title="Ler capítulo sobre redes neurais",
            description=_desc("Capítulo 6 do material da disciplina."),
            due_at=midnight.replace(hour=23, minute=59) + timedelta(days=4),
            priority=0,
        ),
    ]
    for tc in pending:
        create_task(conn, tc)

    # Uma tarefa já concluída (mostra o fluxo de 'concluir_tarefa' no histórico).
    done = create_task(
        conn,
        TaskCreate(
            title="Revisar TF-IDF",
            description=_desc("Anotações da aula passada."),
            due_at=midnight - timedelta(days=1) + timedelta(hours=20),
            priority=0,
        ),
    )
    complete_task(conn, done.id)

    total = len(pending) + 1
    logger.info(f"seed: {total} tarefas criadas (1 concluída)")
    return total


def ingest_data_dir(dir_path: Path) -> None:
    """Ingere o dataset acadêmico de `dir_path` (best-effort, idempotente)."""
    if not dir_path.exists():
        logger.warning(f"pasta de dados não existe: {dir_path} — pulei a ingestão")
        return
    results = ingest_directory(dir_path)
    ingested = sum(1 for r in results if r.status == "ingested")
    skipped = sum(1 for r in results if r.status == "skipped")
    errors = sum(1 for r in results if r.status == "error")
    logger.info(
        f"ingestão de {dir_path}: {ingested} novos, {skipped} já indexados, "
        f"{errors} erros"
    )
    if not results:
        logger.warning(
            f"nenhum documento (.pdf/.txt/.md) encontrado em {dir_path}. "
            "Coloque o dataset (≥10 docs) lá antes de gravar o vídeo."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Semeia dados de demonstração.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("./data"),
        help="Pasta do dataset a ingerir (default: ./data).",
    )
    parser.add_argument(
        "--no-ingest",
        action="store_true",
        help="Não ingerir documentos; só semear agenda e tarefas.",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_dir)

    with get_connection() as conn:
        smoke_check_vec(conn)
        apply_migrations(conn)

        conn.execute("BEGIN")
        try:
            n_ev_old, n_tk_old = clear_seed(conn)
            if n_ev_old or n_tk_old:
                logger.info(
                    f"seed anterior removido: {n_ev_old} eventos, {n_tk_old} tarefas"
                )
            n_ev = seed_events(conn)
            n_tk = seed_tasks(conn)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            logger.exception("falha ao semear — rollback aplicado")
            return 1

    logger.info(f"OK: agenda ({n_ev} eventos) e tarefas ({n_tk}) semeadas.")

    if not args.no_ingest:
        ingest_data_dir(args.data)

    logger.info("seed_demo concluído.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
