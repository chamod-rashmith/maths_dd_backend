"""
Centralized FastAPI Dependency Injection (DI) Container.
Provides abstract domain repository contracts, application services, and RBAC security guards.
"""

from typing import Any, Dict
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.domain.exceptions import PermissionDeniedError
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.progress_repository import ProgressRepository
from app.domain.repositories.question_repository import QuestionRepository
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.domain.repositories.user_repository import UserRepository
from app.repositories.curriculum_repository import PostgresCurriculumRepository
from app.repositories.progress_repository import PostgresProgressRepository
from app.repositories.question_repository import PostgresQuestionRepository
from app.repositories.study_note_repository import PostgresStudyNoteRepository
from app.repositories.user_repository import PostgresUserRepository
from app.services.curriculum_service import CurriculumService
from app.services.progress_service import ProgressService
from app.services.question_service import QuestionService
from app.services.study_note_service import StudyNoteService
from app.services.user_service import UserService

_CONTENT_PRIVILEGED_ROLES = {"ADMIN", "EDITOR"}
_FINANCE_AUDIT_ROLES = {"ADMIN", "ACCOUNT_AUDIT"}


# -----------------------------------------------------------------------------
# 1. Abstract Repository Providers
# -----------------------------------------------------------------------------

def get_user_repository(
    session: AsyncSession = Depends(get_db),
) -> UserRepository:
    """Provides a `UserRepository` instance bound to the active SQLAlchemy session."""
    return PostgresUserRepository(session)


def get_curriculum_repository(
    session: AsyncSession = Depends(get_db),
) -> CurriculumRepository:
    """Provides a `CurriculumRepository` instance bound to the active SQLAlchemy session."""
    return PostgresCurriculumRepository(session)


def get_question_repository(
    session: AsyncSession = Depends(get_db),
) -> QuestionRepository:
    """Provides a `QuestionRepository` instance bound to the active SQLAlchemy session."""
    return PostgresQuestionRepository(session)


def get_study_note_repository(
    session: AsyncSession = Depends(get_db),
) -> StudyNoteRepository:
    """Provides a `StudyNoteRepository` instance bound to the active SQLAlchemy session."""
    return PostgresStudyNoteRepository(session)


def get_progress_repository(
    session: AsyncSession = Depends(get_db),
) -> ProgressRepository:
    """Provides a `ProgressRepository` instance bound to the active SQLAlchemy session."""
    return PostgresProgressRepository(session)


# -----------------------------------------------------------------------------
# 2. Application Service Providers
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


def get_progress_service(
    repo: ProgressRepository = Depends(get_progress_repository),
) -> ProgressService:
    """Provides a `ProgressService` orchestrated with `ProgressRepository`."""
    return ProgressService(repo)


# -----------------------------------------------------------------------------
# 3. Role-Based Access Control (RBAC) Dependencies
# -----------------------------------------------------------------------------

async def require_admin_or_editor(
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
) -> Dict[str, Any]:
    """
    Verifies that the authenticated user holds an 'ADMIN' or 'EDITOR' role
    for curriculum, questions, and study notes management (Create / Update / Delete).
    """
    token_role = str(current_user.get("role", "")).upper()
    if token_role in _CONTENT_PRIVILEGED_ROLES:
        return current_user

    uid = current_user.get("uid")
    if uid:
        db_user = await user_repo.get_by_uid(uid)
        if db_user and str(db_user.get("role", "")).upper() in _CONTENT_PRIVILEGED_ROLES:
            return current_user

    raise PermissionDeniedError(
        "Insufficient privileges. ADMIN or EDITOR role is required."
    )


async def require_admin_or_account_audit(
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
) -> Dict[str, Any]:
    """
    Verifies that the authenticated user holds an 'ADMIN' or 'ACCOUNT_AUDIT' role
    for financial bank slip verification, subscription approvals, rejections, and billing maintenance.
    """
    token_role = str(current_user.get("role", "")).upper()
    if token_role in _FINANCE_AUDIT_ROLES:
        return current_user

    uid = current_user.get("uid")
    if uid:
        db_user = await user_repo.get_by_uid(uid)
        if db_user and str(db_user.get("role", "")).upper() in _FINANCE_AUDIT_ROLES:
            return current_user

    raise PermissionDeniedError(
        "Insufficient privileges. ADMIN or ACCOUNT_AUDIT role is required."
    )
