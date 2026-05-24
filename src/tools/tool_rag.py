"""Tool de busca em materiais (RAG)."""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.rag.retrieve import search_async
from src.tools.registry import ToolDefinition, get_registry


async def _buscar_material_rag(args: dict[str, Any]) -> dict[str, Any]:
    pergunta = args.get("pergunta") or args.get("query")
    if not pergunta:
        raise ValueError("argumento 'pergunta' obrigatório")

    top_k = int(args.get("top_k", 5))
    retrieval = await search_async(pergunta, top_k=top_k)

    chunks_payload = [
        {
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "document_title": c.document_title,
            "position": c.position,
            "distance": round(c.distance, 4),
            "text_preview": c.text[:400],
        }
        for c in retrieval.chunks
    ]
    logger.info(
        f"buscar_material_rag: '{pergunta[:60]}...' -> {len(chunks_payload)} chunks "
        f"(no_relevant={retrieval.no_relevant_context})"
    )

    return {
        "pergunta": pergunta,
        "no_relevant_context": retrieval.no_relevant_context,
        "threshold_used": retrieval.threshold_used,
        "count": len(chunks_payload),
        "chunks": chunks_payload,
    }


def _register() -> None:
    reg = get_registry()
    reg.register(
        ToolDefinition(
            name="buscar_material_rag",
            description=(
                "Busca trechos relevantes nos materiais de estudo (PDFs/textos) "
                "carregados pelo usuário, via RAG semântico. Use SEMPRE que a "
                "pergunta for conceitual (ex: 'explique X', 'o que é Y?', 'resuma Z')."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "pergunta": {
                        "type": "string",
                        "description": "Pergunta ou termo de busca em português.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Número de trechos a retornar (default 5).",
                    },
                },
                "required": ["pergunta"],
            },
            handler=_buscar_material_rag,
            examples=[
                {
                    "tool": "buscar_material_rag",
                    "args": {"pergunta": "explique regressão logística"},
                },
            ],
        )
    )


_register()
