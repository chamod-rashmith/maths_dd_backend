"""
Application Service for User Profile business logic.
"""

from typing import Any, Dict

from app.domain.exceptions import EntityNotFoundError, ValidationDomainError
from app.domain.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileSyncRequest


class UserService:
    """Orchestrates user profile retrieval and idempotent authentication synchronization."""

    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def get_my_profile(self, current_user: Dict[str, Any]) -> Dict[str, Any]:
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
        uid = current_user.get("uid")
        email = current_user.get("email")

        if not uid or not email:
            raise ValidationDomainError("Token must include both 'uid' and 'email'.")

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
        )
