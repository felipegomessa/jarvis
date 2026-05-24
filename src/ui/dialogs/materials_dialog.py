"""Dialog modal: enviar material + listar documentos indexados — Fase 6."""

from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger
from nicegui import events, ui

from src.core.db import get_connection
from src.rag.ingest import ingest_directory, ingest_document


def open_materials_dialog() -> None:
    with ui.dialog().props("persistent") as dialog, ui.card().classes(
        "jarvis-dialog-card w-full max-w-4xl"
    ):
        # ---------------- Header ----------------
        with ui.element("div").classes("jarvis-dialog-header"):
            with ui.element("div").classes("jarvis-dialog-header__title"):
                ui.icon("upload_file").style("color: var(--jarvis-blue)")
                ui.label("Materiais de estudo")
            ui.button(icon="close", on_click=dialog.close).props(
                "flat round size=sm color=white"
            )

        ui.label(
            "Carregue PDFs, .txt ou .md. O conteúdo será indexado para responder "
            "perguntas via RAG."
        ).classes("jarvis-dialog-subtitle")

        # ---------------- Drop zone (upload + indexar pasta) ----------------
        async def on_upload(e: events.UploadEventArguments) -> None:
            upload_dir = Path("./data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            target = upload_dir / e.name
            with open(target, "wb") as f:
                f.write(e.content.read())
            logger.info(f"upload recebido: {target}")
            ui.notify(
                f"Indexando '{e.name}'… (pode demorar na 1ª vez)",
                type="info",
                timeout=2000,
            )
            result = await asyncio.to_thread(ingest_document, target)
            if result.status == "ingested":
                ui.notify(
                    f"OK: {e.name} ({result.chunk_count} chunks)",
                    type="positive",
                )
            elif result.status == "skipped":
                ui.notify(f"Já existia: {e.name} (hash igual)", type="info")
            else:
                ui.notify(
                    f"Erro: {e.name} — {result.reason}: {result.error}",
                    type="negative",
                )
            refresh()

        async def on_index_data() -> None:
            ui.notify("Indexando pasta /data…", type="info")
            results = await asyncio.to_thread(ingest_directory, Path("./data"))
            ing = sum(1 for r in results if r.status == "ingested")
            sk = sum(1 for r in results if r.status == "skipped")
            er = sum(1 for r in results if r.status == "error")
            ui.notify(
                f"{ing} novos · {sk} já existiam · {er} erros",
                type="positive" if er == 0 else "warning",
            )
            refresh()

        with ui.element("div").classes("jarvis-upload-zone w-full"):
            with ui.row().classes("w-full gap-3 items-center no-wrap"):
                ui.upload(
                    label="Selecionar arquivo (.pdf / .txt / .md)",
                    on_upload=on_upload,
                    multiple=False,
                    max_file_size=50_000_000,
                ).props("accept='.pdf,.txt,.md' color=primary").classes("flex-1")
                ui.button(
                    "Indexar pasta /data",
                    icon="folder_open",
                    on_click=on_index_data,
                ).props("color=primary unelevated")

        # ---------------- Lista de documentos indexados ----------------
        with ui.row().classes("items-center justify-between w-full").style(
            "margin-top:18px; margin-bottom:8px"
        ):
            count_label = ui.label("Documentos indexados").style(
                "font-weight:600; color:var(--jarvis-text); font-size:14px"
            )
            ui.button(icon="refresh", on_click=lambda: refresh()).props(
                "flat round size=sm color=grey-6"
            )

        list_container = ui.column().classes("w-full gap-2").style(
            "max-height:42vh; overflow-y:auto; padding-right:4px"
        )

        def refresh() -> None:
            list_container.clear()
            with get_connection() as conn:
                rows = conn.execute(
                    """SELECT id, title, source_path, type, char_count,
                              chunk_count, ingested_at
                         FROM documents
                        ORDER BY ingested_at DESC"""
                ).fetchall()
            count_label.set_text(f"Documentos indexados ({len(rows)})")
            with list_container:
                if not rows:
                    ui.label("(nenhum documento ainda)").style(
                        "color:#666; font-style:italic; font-size:13px; padding:8px"
                    )
                    return
                for r in rows:
                    with ui.element("div").classes("jarvis-doc-row w-full"):
                        ui.icon("description").style(
                            "color:var(--jarvis-blue); font-size:22px"
                        )
                        with ui.column().classes("flex-1 gap-0 min-w-0"):
                            ui.label(r["title"]).classes(
                                "jarvis-doc-row__title"
                            ).style(
                                "white-space:nowrap; overflow:hidden; "
                                "text-overflow:ellipsis"
                            )
                            ui.label(
                                f"{r['type']} · {r['chunk_count']} chunks · "
                                f"{r['char_count']} chars · "
                                f"ingerido em {r['ingested_at']}"
                            ).classes("jarvis-doc-row__meta")
                            ui.label(r["source_path"]).classes(
                                "jarvis-doc-row__path"
                            ).style(
                                "white-space:nowrap; overflow:hidden; "
                                "text-overflow:ellipsis"
                            )

        refresh()

    dialog.open()
