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
            "Duas formas de adicionar materiais (.pdf, .txt, .md) ao acervo. "
            "O conteúdo é indexado para responder perguntas via RAG."
        ).classes("jarvis-dialog-subtitle")

        # ---------------- Drop zone (upload + indexar pasta) ----------------
        async def on_upload(e: events.UploadEventArguments) -> None:
            # NiceGUI 3.x: o arquivo vem em e.file (FileUpload), com .name e .save().
            name = e.file.name
            target = Path("./data/uploads") / name
            try:
                await e.file.save(target)  # cria a pasta e grava (async)
            except Exception as exc:  # feedback amigável na UI em vez de crash
                logger.exception(f"falha ao salvar upload {name}")
                ui.notify(f"Erro ao salvar '{name}': {exc}", type="negative")
                return
            logger.info(f"upload recebido: {target}")
            ui.notify(
                f"Indexando '{name}'… (pode demorar na 1ª vez)",
                type="info",
                timeout=2000,
            )
            result = await asyncio.to_thread(ingest_document, target)
            if result.status == "ingested":
                ui.notify(f"OK: {name} ({result.chunk_count} chunks)", type="positive")
            elif result.status == "skipped":
                ui.notify(f"Já existia: {name} (hash igual)", type="info")
            else:
                ui.notify(
                    f"Erro: {name} — {result.reason}: {result.error}", type="negative"
                )
            refresh()

        async def on_index_data() -> None:
            ui.notify("Indexando pasta /data (incluindo subpastas)…", type="info")
            # recursive=True: os materiais ficam em data/Artigos, data/Material de Aula,
            # etc. Sem isso a raiz data/ não tem PDFs e a indexação não acha nada.
            results = await asyncio.to_thread(
                ingest_directory, Path("./data"), True
            )
            ing = sum(1 for r in results if r.status == "ingested")
            sk = sum(1 for r in results if r.status == "skipped")
            er = sum(1 for r in results if r.status == "error")
            if not results:
                ui.notify(
                    "Nenhum arquivo .pdf/.txt/.md encontrado em /data.",
                    type="warning",
                )
            else:
                ui.notify(
                    f"{ing} novos · {sk} já existiam · {er} erros",
                    type="positive" if er == 0 else "warning",
                )
            refresh()

        # ===== Opção A: enviar um arquivo do computador (envio automático) =====
        with ui.element("div").classes("jarvis-upload-zone w-full"):
            ui.label("A) Enviar um arquivo do seu computador").style(
                "font-weight:600; color:var(--jarvis-text); font-size:14px"
            )
            ui.label(
                "Clique no botão de upload abaixo, escolha o arquivo e confirme. "
                "O envio e a indexação são automáticos ao selecionar — aguarde a "
                "notificação de confirmação no canto da tela."
            ).style("font-size:12px; color:#9aa; margin:2px 0 8px")
            ui.upload(
                label="Escolher arquivo (.pdf / .txt / .md)",
                on_upload=on_upload,
                multiple=False,
                max_file_size=50_000_000,
                auto_upload=True,
            ).props("accept='.pdf,.txt,.md' color=primary").classes("w-full")

        # ===== Opção B: indexar a pasta data/ do projeto (e subpastas) =====
        with ui.element("div").classes("jarvis-upload-zone w-full").style(
            "margin-top:10px"
        ):
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label("B) Indexar a pasta data/ do projeto").style(
                        "font-weight:600; color:var(--jarvis-text); font-size:14px"
                    )
                    ui.label(
                        "Varre data/ e suas subpastas (Artigos, Material de Aula…) e "
                        "indexa os materiais já presentes no repositório."
                    ).style("font-size:12px; color:#9aa")
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
