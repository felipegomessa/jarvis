"""Tool de listagem de materiais (documentos ingeridos no RAG)."""

from __future__ import annotations

import asyncio
from typing import Any

from src.core.db import get_connection
from src.tools.registry import ToolDefinition, get_registry


async def _listar_materiais(args: dict[str, Any]) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, source_path, type, char_count, chunk_count,
                       ingested_at
                  FROM documents
                 ORDER BY ingested_at DESC
                """
            ).fetchall()
        docs = [
            {
                "id": int(r["id"]),
                "title": r["title"],
                "source_path": r["source_path"],
                "type": r["type"],
                "char_count": int(r["char_count"]),
                "chunk_count": int(r["chunk_count"]),
                "ingested_at": r["ingested_at"],
            }
            for r in rows
        ]
        return {"count": len(docs), "documents": docs}

    return await asyncio.to_thread(_run)


def _register() -> None:
    reg = get_registry()
    reg.register(
        ToolDefinition(
            name="listar_materiais",
            description=(
                "Lista os documentos acadêmicos carregados pelo usuário no acervo "
                "RAG. Útil para mostrar quais materiais estão disponíveis."
            ),
            parameters_schema={"type": "object", "properties": {}},
            handler=_listar_materiais,
            examples=[{"tool": "listar_materiais", "args": {}}],
        )
    )


_register()
