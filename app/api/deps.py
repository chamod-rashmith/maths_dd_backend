"""
Centralized FastAPI Dependency Injection (DI) Container.
Provides abstract domain repository contracts backed by concrete PostgreSQL implementations.
"""

import asyncpg
from fastapi import Depends

from app.core.database import get_db
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.question_repository import QuestionRepository
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.domain.repositories.user_repository import UserRepository
from app.repositories.curriculum_repository import PostgresCurriculumRepository
from app.repositories.question_repository import PostgresQuestionRepository
from app.repositories.study_note_repository import PostgresStudyNoteRepository
from app.repositories.user_repository import PostgresUserRepository


def get_user_repository(
    conn: asyncpg.Connection = Depends(get_db),
) -> UserRepository:
    """Provides a `UserRepository` instance bound to the active DB connection."""
    return PostgresUserRepository(conn)


def get_curriculum_repository(
    conn: asyncpg.Connection = Depends(get_db),
) -> CurriculumRepository:
    """Provides a `CurriculumRepository` instance bound to the active DB connection."""
    return PostgresCurriculumRepository(conn)


def get_question_repository(
    conn: asyncpg.Connection = Depends(get_db),
) -> QuestionRepository:
    """Provides a `QuestionRepository` instance bound to the active DB connection."""
    return PostgresQuestionRepository(conn)


def get_study_note_repository(
    conn: asyncpg.Connection = Depends(get_db),
) -> StudyNoteRepository:
    """Provides a `StudyNoteRepository` instance bound to the active DB connection."""
    return PostgresStudyNoteRepository(conn)
