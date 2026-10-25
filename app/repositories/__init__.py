"""Concrete PostgreSQL Repository Implementations (Adapters)."""

from app.repositories.curriculum_repository import PostgresCurriculumRepository
from app.repositories.question_repository import PostgresQuestionRepository
from app.repositories.study_note_repository import PostgresStudyNoteRepository
from app.repositories.user_repository import PostgresUserRepository

__all__ = [
    "PostgresCurriculumRepository",
    "PostgresQuestionRepository",
    "PostgresStudyNoteRepository",
    "PostgresUserRepository",
]
