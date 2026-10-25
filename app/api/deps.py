"""
Centralized FastAPI Dependency Injection (DI) Container.
Provides abstract domain repository contracts, application services, and RBAC security guards.
"""

from typing import Any, Dict
import asyncpg
from fastapi import Depends

from app.core.database import get_db
from app.core.security import get_current_user
from app.domain.exceptions import PermissionDeniedError
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.question_repository import QuestionRepository
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.domain.repositories.user_repository import UserRepository
from app.repositories.curriculum_repository import PostgresCurriculumRepository
from app.repositories.question_repository import PostgresQuestionRepository
from app.repositories.study_note_repository import PostgresStudyNoteRepository
from app.repositories.user_repository import PostgresUserRepository
from app.services.curriculum_service import CurriculumService
from app.services.question_service import QuestionService
from app.services.study_note_service import StudyNoteService
from app.services.user_service import UserService

_PRIVILEGED_ROLES = {"ADMIN", "EDITOR"}


# -----------------------------------------------------------------------------
# 1. Abstract Repository Providers
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# 2. Application Service / Use Case Providers
# -----------------------------------------------------------------------------

def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    """Provides a `UserService` orchestrated with `UserRepository`."""
    return UserService(repo)


def get_curriculum_service(
    repo: CurriculumRepository = Depends(get_curriculum_repository),
) -> CurriculumService:
    """Provides a `CurriculumService` orchestrated with `CurriculumRepository`."""
    return CurriculumService(repo)


def get_question_service(
    repo: QuestionRepository = Depends(get_question_repository),
) -> QuestionService:
    """Provides a `QuestionService` orchestrated with `QuestionRepository`."""
    return QuestionService(repo)


def get_study_note_service(
    repo: StudyNoteRepository = Depends(get_study_note_repository),
) -> StudyNoteService:
    """Provides a `StudyNoteService` orchestrated with `StudyNoteRepository`."""
    return StudyNoteService(repo)


# -----------------------------------------------------------------------------
# 3. Role-Based Access Control (RBAC) Dependencies
# -----------------------------------------------------------------------------

async def require_admin_or_editor(
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
) -> Dict[str, Any]:
    """
    Verifies that the authenticated user holds an 'ADMIN' or 'EDITOR' role
    (via Firebase custom claims or the PostgreSQL `users` record).
    """
    token_role = str(current_user.get("role", "")).upper()
    if token_role in _PRIVILEGED_ROLES:
        return current_user

    uid = current_user.get("uid")
    if uid:
        db_user = await user_repo.get_by_uid(uid)
        if db_user and db_user.role.upper() in _PRIVILEGED_ROLES:
            return current_user

    raise PermissionDeniedError(
        "Insufficient privileges. ADMIN or EDITOR role is required."
    )
