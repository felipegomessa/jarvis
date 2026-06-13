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

    top_k = int(args.get("top_k", 4))
    retrieval = await search_async(pergunta, top_k=top_k)

    # Numeramos os trechos como [Doc N] para a LLM citar a fonte na resposta.
    # Enviamos o TEXTO COMPLETO do chunk (não uma prévia), pois é o contexto que
    # fundamenta a geração — truncar aqui degradaria a qualidade do RAG (A1).
    chunks_payload = [
        {
            "ref": f"Doc {i}",
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "document_title": c.document_title,
            "position": c.position,
            "distance": round(c.distance, 4),
            "text": c.text,
        }
        for i, c in enumerate(retrieval.chunks, start=1)
    ]
    logger.info(
        f"buscar_material_rag: '{pergunta[:60]}...' -> {len(chunks_payload)} chunks "
        f"(no_relevant={retrieval.no_relevant_context})"
    )

    # Instrução de grounding lida pela LLM antes de compor a resposta (A2):
    # responder só com base nos trechos, citar [Doc N] e não alucinar.
    if retrieval.no_relevant_context or not chunks_payload:
        instrucao = (
            "Nenhum trecho relevante foi encontrado nos materiais. NÃO invente: "
            "responda ao usuário que não encontrou material relevante sobre o tema "
            "e sugira que ele carregue documentos pertinentes."
        )
    else:
        instrucao = (
            "Responda à pergunta do usuário APENAS com base nos trechos acima "
            "(campo 'text'). Cite a fonte como [Doc N: título] sempre que afirmar "
            "algo (use o campo 'ref'). Se os trechos forem insuficientes para "
            "responder, diga claramente que não encontrou material suficiente. "
            "Não use conhecimento externo nem invente informações."
        )

    return {
        "pergunta": pergunta,
        "no_relevant_context": retrieval.no_relevant_context,
        "threshold_used": retrieval.threshold_used,
        "count": len(chunks_payload),
        "instrucao": instrucao,
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
                        "description": "Número de trechos a retornar (default 4).",
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
