"""Construção do prompt RAG (PT-BR + citações obrigatórias) — D-023 / RF-002.7."""

from __future__ import annotations

from src.llm.types import Message
from src.rag.types import RetrievalResult

SYSTEM_PROMPT = (
    "Você é um assistente acadêmico que ajuda estudantes a entender materiais "
    "de estudo. Responda APENAS com base no contexto fornecido abaixo. Cite a "
    "fonte como [Doc N] sempre que afirmar algo. Se o contexto for insuficiente, "
    "diga claramente que não encontrou material relevante e sugira que o usuário "
    "carregue mais documentos. Não invente informações."
)


def _format_context(retrieval: RetrievalResult) -> str:
    if retrieval.no_relevant_context or not retrieval.chunks:
        return "(nenhum trecho relevante encontrado nos materiais carregados)"
    parts: list[str] = []
    for i, ch in enumerate(retrieval.chunks, start=1):
        parts.append(f"[Doc {i}: {ch.document_title}]\n{ch.text}")
    return "\n\n".join(parts)


def build_rag_messages(question: str, retrieval: RetrievalResult) -> list[Message]:
    """Constrói system + user messages para o GemmaClient."""
    context = _format_context(retrieval)
    system_content = f"{SYSTEM_PROMPT}\n\nContexto:\n{context}"
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question},
    ]
