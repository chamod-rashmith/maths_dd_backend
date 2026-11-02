"""
Concrete PostgreSQL Implementation of UserRepository using SQLAlchemy 2.0.
"""

from typing import Any, Dict, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.user_repository import UserRepository
from app.models.user import User


def _serialize_user(user: User) -> Dict[str, Any]:
    """Pure DTO serialization omitting internal database timestamps."""
    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.name,
        "telephone_no": user.telephone_no,
        "role": user.role,
        "avatar_url": user.avatar_url,
        "school_name": user.school_name,
        "district": user.district,
        "stream": user.stream,
        "grade": user.grade,
        "attempt": user.attempt,
        "xp": user.xp,
        "streak_count": user.current_streak_days if user.current_streak_days > 0 else user.streak_count,
        "accuracy_rate": user.accuracy_rate,
        "questions_solved": user.total_solved_count if user.total_solved_count > 0 else user.questions_solved,
        "is_premium": user.is_premium,
        "premium_expiry": user.premium_expiry,
    }


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of `UserRepository` using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        try:
            result = await self._session.execute(
                select(User).where(User.uid == uid)
            )
            user = result.scalar_one_or_none()
            return _serialize_user(user) if user else None
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def sync_or_create(
        self,
        uid: str,
        email: str,
        name: str,
        avatar_url: Optional[str] = None,
        telephone_no: Optional[str] = None,
        school_name: Optional[str] = None,
        district: Optional[str] = None,
        stream: Optional[str] = None,
        grade: Optional[str] = None,
        attempt: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            # 1. Search for existing user by uid
            result = await self._session.execute(
                select(User).where(User.uid == uid)
            )
            user = result.scalar_one_or_none()

            # 2. If not found by uid, check if existing record has matching email
            if not user:
                result_email = await self._session.execute(
                    select(User).where(func.lower(User.email) == email.lower())
                )
                user = result_email.scalar_one_or_none()
                if user:
                    user.uid = uid

            if user:
                if name and name.strip():
                    user.name = name
                if avatar_url is not None:
                    user.avatar_url = avatar_url
                if telephone_no is not None:
                    user.telephone_no = telephone_no
                if school_name is not None:
                    user.school_name = school_name
                if district is not None:
                    user.district = district
                if stream is not None:
                    user.stream = stream
                if grade is not None:
                    user.grade = grade
                if attempt is not None:
                    user.attempt = attempt
            else:
                user = User(
                    uid=uid,
                    email=email,
                    name=name,
                    avatar_url=avatar_url,
                    telephone_no=telephone_no,
                    school_name=school_name,
                    district=district,
                    stream=stream,
                    grade=grade,
                    attempt=attempt,
                )
                self._session.add(user)

            await self._session.flush()
            await self._session.refresh(user)
            return _serialize_user(user)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc
