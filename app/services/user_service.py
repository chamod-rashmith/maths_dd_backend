"""
Application Service for User Profile business logic.

===============================================================================
User Application Service:
-------------------------------------------------------------------------------
Auth token එකෙන් uid සහ email තහවුරු කර, User Profile සහ Domain 1 ශාස්ත්‍රීය දත්ත
(Target A/L year, Attempt, Z-score district) repository වෙත යොමු කරයි.
===============================================================================
"""

from typing import Any, Dict

from app.domain.exceptions import (
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationDomainError,
)
from app.domain.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileSyncRequest


class UserService:
    """Orchestrates user profile retrieval and idempotent authentication synchronization."""

    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def get_my_profile(self, current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Fetches profile of the currently authenticated user."""
        uid = current_user.get("uid")
        if not uid:
            raise ValidationDomainError("Authenticated token payload is missing 'uid'.")

        user = await self._repo.get_by_uid(uid)
        if not user:
            raise EntityNotFoundError(
                "User profile not initialized yet. Please call /sync first."
            )
        return user

    async def sync_profile(
        self, current_user: Dict[str, Any], payload: UserProfileSyncRequest
    ) -> Dict[str, Any]:
        """Synchronizes user profile and normalized StudentProfile from request payload."""
        uid = current_user.get("uid")
        email = current_user.get("email")

        if not uid or not email:
            raise ValidationDomainError("Token must include both 'uid' and 'email'.")

        if not current_user.get("email_verified", False):
            raise PermissionDeniedError(
                "A verified email address is required to synchronize a user profile."
            )

        display_name = (
            payload.name or current_user.get("name") or email.split("@")[0]
        )
        avatar_url = payload.avatar_url or current_user.get("picture")

        return await self._repo.sync_or_create(
            uid=uid,
            email=email,
            name=display_name,
            avatar_url=avatar_url,
            telephone_no=payload.telephone_no,
            school_name=payload.school_name,
            district_id=payload.district_id,
            district=payload.district_code or payload.district,
            stream=payload.stream.value if payload.stream else None,
            grade=payload.grade.value if payload.grade else None,
            attempt=payload.attempt.value if payload.attempt else None,
            exam_year=payload.exam_year,
            attempt_number=payload.attempt_number,
            exam_district_id=payload.exam_district_id,
            medium=payload.medium or "SINHALA",
        )
