"""Modelos Pydantic do módulo de aprendizado (provas) — Spec 007 / D-030."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

QuestionType = Literal["mc", "open"]


class Question(BaseModel):
    """Uma questão de prova. MC exige `options`+`correct_index`; open exige `answer_key`."""

    id: int | None = None
    type: QuestionType
    prompt: str
    topic: str = ""
    options: list[str] | None = None      # MC
    correct_index: int | None = None      # MC
    answer_key: str | None = None         # open
    source_document_id: int | None = None
    source_chunk_id: int | None = None
    max_points: float = 1.0

    @model_validator(mode="after")
    def _check_by_type(self) -> Question:
        if self.type == "mc":
            # 4 alternativas é o alvo, mas aceitamos 2 a 6 para não descartar questões
            # boas quando a LLM varia o número de opções (robustez com LLM real).
            if not self.options or not (2 <= len(self.options) <= 6):
                raise ValueError("questão MC exige entre 2 e 6 alternativas")
            if self.correct_index is None or not (
                0 <= self.correct_index < len(self.options)
            ):
                raise ValueError("questão MC exige correct_index dentro das alternativas")
        else:  # open
            if not (self.answer_key and self.answer_key.strip()):
                raise ValueError("questão dissertativa exige answer_key (rubrica)")
        return self


class Quiz(BaseModel):
    id: int | None = None
    title: str
    documents: list[int]                  # ≥1 document_id fonte
    questions: list[Question] = []
    status: str = "ready"

    @model_validator(mode="after")
    def _check_docs(self) -> Quiz:
        if not self.documents:
            raise ValueError("a prova precisa de ao menos 1 documento-fonte")
        return self


class Answer(BaseModel):
    question_id: int
    response: str = ""
    awarded_points: float | None = None
    is_correct: bool | None = None
    feedback: str | None = None


class Attempt(BaseModel):
    id: int | None = None
    quiz_id: int
    score: float | None = None            # 0..10
    status: str = "in_progress"           # in_progress | graded
    answers: list[Answer] = []


class TopicScore(BaseModel):
    topic: str
    earned: float
    possible: float

    @property
    def ratio(self) -> float:
        return self.earned / self.possible if self.possible > 0 else 0.0


class StudyPlanItem(BaseModel):
    topic: str
    action: str
    material: str | None = None           # documento/seção citada
    minutes: int = 30
    day: str | None = None                # data sugerida (YYYY-MM-DD), encaixada na agenda
    time: str | None = None               # horário sugerido (HH:MM)


class StudyPlan(BaseModel):
    items: list[StudyPlanItem] = []


class DifficultyReport(BaseModel):
    weak_topics: list[TopicScore] = []
    recommendations: list[str] = []
    plan: StudyPlan = StudyPlan()
    positive: bool = False                # True quando não houve tópico fraco
