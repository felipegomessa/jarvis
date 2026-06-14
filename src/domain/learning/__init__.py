"""Domínio de aprendizado: provas, tentativas, respostas (Spec 007)."""

from src.domain.learning.models import (
    Answer,
    Attempt,
    DifficultyReport,
    Question,
    QuestionType,
    Quiz,
    StudyPlan,
    StudyPlanItem,
    TopicScore,
)
from src.domain.learning.repo import (
    add_questions,
    create_attempt,
    create_quiz,
    finalize_attempt,
    get_attempt,
    get_quiz,
    latest_graded_attempt_id,
    list_quizzes,
    save_answer,
    topic_breakdown,
)

__all__ = [
    "Answer",
    "Attempt",
    "DifficultyReport",
    "Question",
    "QuestionType",
    "Quiz",
    "StudyPlan",
    "StudyPlanItem",
    "TopicScore",
    "add_questions",
    "create_attempt",
    "create_quiz",
    "finalize_attempt",
    "get_attempt",
    "get_quiz",
    "latest_graded_attempt_id",
    "list_quizzes",
    "save_answer",
    "topic_breakdown",
]
