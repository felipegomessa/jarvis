"""Correção de provas: MC determinística + dissertativa via LLM-juiz — RF-007.6."""

from __future__ import annotations

from loguru import logger

from src.domain.learning import Question
from src.llm.json_utils import parse_json_response
from src.llm.types import Message


def grade_mc(question: Question, response: str) -> tuple[float, bool]:
    """Corrige múltipla escolha. `response` é o índice escolhido (ex.: '2'); branco = 0."""
    resp = (response or "").strip()
    if not resp:
        return 0.0, False
    try:
        chosen = int(resp)
    except ValueError:
        return 0.0, False
    correct = chosen == question.correct_index
    return (question.max_points if correct else 0.0), correct


def build_open_grading_messages(
    question: Question, response: str, source_text: str | None
) -> list[Message]:
    """Mensagens para o LLM-juiz corrigir uma dissertativa — função pura (testável)."""
    contexto = f"\n\nTrecho-fonte do material:\n{source_text}" if source_text else ""
    system = (
        "Você é um corretor acadêmico justo. Avalie a resposta do aluno comparando-a "
        "com a rubrica (pontos esperados) e com o trecho-fonte. Dê uma nota de 0.0 a "
        "1.0 (fração do acerto) e um feedback breve em português. Responda APENAS um "
        'JSON: {"score": 0.0, "feedback": "...", "pontos_faltantes": ["..."]}'
    )
    user = (
        f"Enunciado: {question.prompt}\n\n"
        f"Rubrica (pontos esperados): {question.answer_key}{contexto}\n\n"
        f"Resposta do aluno: {response}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_open_grade(raw: str, max_points: float) -> tuple[float, str]:
    """Parseia o JSON do LLM-juiz. Score é limitado a [0,1] e escalado por max_points."""
    parsed = parse_json_response(raw)  # pode levantar ValueError
    score = float(parsed.get("score", 0.0))
    score = max(0.0, min(1.0, score))
    feedback = str(parsed.get("feedback", "")).strip()
    faltantes = parsed.get("pontos_faltantes")
    if isinstance(faltantes, list) and faltantes:
        feedback += " (faltou: " + "; ".join(str(x) for x in faltantes) + ")"
    return score * max_points, feedback or "sem feedback"


async def grade_open(
    gemma,  # GemmaClient | FakeLLM (complete_chat)
    question: Question,
    response: str,
    source_text: str | None = None,
) -> tuple[float, str]:
    """Corrige dissertativa via LLM-juiz. Branco = 0; erro do juiz não derruba a prova."""
    if not (response or "").strip():
        return 0.0, "não respondida"
    try:
        messages = build_open_grading_messages(question, response, source_text)
        raw = await gemma.complete_chat(messages)
        return parse_open_grade(raw, question.max_points)
    except Exception as e:
        logger.warning(f"LLM-juiz falhou na questão {question.id}: {e}")
        return 0.0, "não avaliada — erro do corretor"


def aggregate_score(awarded: list[float], max_points: list[float]) -> float:
    """Nota final 0-10 = soma(obtidos)/soma(possiveis) * 10, arredondada a 1 casa."""
    total = sum(max_points)
    if total <= 0:
        return 0.0
    return round(sum(awarded) / total * 10, 1)
