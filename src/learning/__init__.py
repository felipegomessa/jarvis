"""Camada de orquestração de aprendizado (LLM + RAG + domínio) — Spec 007 / D-030.

Pode importar `core`, `domain`, `rag`, `llm`. Importada por `ui/` e `tools/`.
"""

from src.learning.coach import build_difficulty_report, select_weak, topic_scores
from src.learning.errors import LearningError
from src.learning.generator import generate_quiz, parse_quiz_questions
from src.learning.grader import aggregate_score, grade_mc, grade_open
from src.learning.service import (
    difficulty_report,
    generate,
    grade_attempt,
    start_attempt,
)

__all__ = [
    "LearningError",
    "aggregate_score",
    "build_difficulty_report",
    "difficulty_report",
    "generate",
    "generate_quiz",
    "grade_attempt",
    "grade_mc",
    "grade_open",
    "parse_quiz_questions",
    "select_weak",
    "start_attempt",
    "topic_scores",
]
