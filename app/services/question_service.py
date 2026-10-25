"""
Application Service for Questions and Marking Schemes.
"""

from typing import List

from app.domain.entities import QuestionSummaryEntity, QuestionWithSolutionEntity
from app.domain.repositories.question_repository import QuestionRepository
from app.schemas.question import QuestionCreate


class QuestionService:
    """Orchestrates question creation and catalog retrieval."""

    def __init__(self, repo: QuestionRepository) -> None:
        self._repo = repo

    async def list_recent_questions(
        self, limit: int = 15
    ) -> List[QuestionSummaryEntity]:
        return await self._repo.get_recent(limit=limit)

    async def create_question(
        self, payload: QuestionCreate
    ) -> QuestionWithSolutionEntity:
        return await self._repo.create_question_with_solution(
            title=payload.title,
            subject_id=payload.subject_id,
            lesson_id=payload.lesson_id,
            content_text=payload.content_text,
            solution_text=payload.solution_text,
            solution_title=payload.solution_title,
            question_type=payload.question_type,
            difficulty=payload.difficulty,
            schedule=payload.schedule,
            source=payload.source,
            source_details=payload.source_details or "",
            allocated_marks=payload.allocated_marks,
            is_premium=payload.is_premium,
            is_published=payload.is_published,
            scheduled_date=payload.scheduled_date,
            custom_id=payload.custom_id,
        )
