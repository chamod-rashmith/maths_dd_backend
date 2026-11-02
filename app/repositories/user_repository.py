"""
PostgreSQL UserRepository implementation using modern SQLAlchemy 2.0.
"""

from typing import Any, Dict, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.domain.exceptions import DatabaseOperationError
from app.domain.repositories.user_repository import UserRepository
from app.models.user import User
from app.models.user_stats import UserStats


def _serialize_user(user: User) -> Dict[str, Any]:
    """Helper to cleanly serialize User ORM model to dictionary without legacy to_dict()."""
    stats = user.stats
    xp = stats.xp if stats else 0
    streak_count = stats.current_streak_days if stats else 0
    accuracy_rate = stats.accuracy_rate if stats else 0.0
    questions_solved = stats.total_solved_count if stats else 0

    active_sub = user.active_subscription
    active_sub_payload = None
    if active_sub:
        active_sub_payload = {
            "id": active_sub.id,
            "plan_id": active_sub.plan_id,
            "status": active_sub.status,
            "provider": active_sub.provider,
            "starts_at": active_sub.starts_at,
            "expires_at": active_sub.expires_at,
            "amount_lkr": active_sub.amount_lkr,
            "slip_image_url": active_sub.slip_image_url,
            "reference_note": active_sub.reference_note,
            "admin_notes": active_sub.admin_notes,
            "approved_at": active_sub.approved_at,
        }

    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.name,
        "telephone_no": user.telephone_no,
        "role": user.role,
        "avatar_url": user.avatar_url,
        "school_name": user.school_name,
        "district_id": user.district_id,
        "district": user.district,
        "stream": user.stream,
        "grade": user.grade,
        "attempt": user.attempt,
        "xp": xp,
        "streak_count": streak_count,
        "accuracy_rate": accuracy_rate,
        "questions_solved": questions_solved,
        "is_premium": user.is_premium,
        "active_subscription": active_sub_payload,
    }


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of `UserRepository` using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        try:
            result = await self._session.execute(
                select(User)
                .options(
                    selectinload(User.stats),
                    selectinload(User.subscriptions),
                    joinedload(User.district),
                )
                .where(User.uid == uid)
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
        district_id: Optional[str] = None,
        district: Optional[str] = None,
        stream: Optional[str] = None,
        grade: Optional[str] = None,
        attempt: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            effective_district_id = district_id if district_id is not None else district
            if effective_district_id:
                effective_district_id = effective_district_id.strip().upper()

            # 1. Search for existing user by uid
            result = await self._session.execute(
                select(User)
                .options(
                    selectinload(User.stats),
                    selectinload(User.subscriptions),
                    joinedload(User.district),
                )
                .where(User.uid == uid)
            )
            user = result.scalar_one_or_none()

            # 2. If not found by uid, check if existing record has matching email
            if not user:
                result_email = await self._session.execute(
                    select(User)
                    .options(
                        selectinload(User.stats),
                        selectinload(User.subscriptions),
                        joinedload(User.district),
                    )
                    .where(func.lower(User.email) == email.lower())
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
                if effective_district_id is not None:
                    user.district_id = effective_district_id
                if stream is not None:
                    user.stream = str(stream)
                if grade is not None:
                    user.grade = str(grade)
                if attempt is not None:
                    user.attempt = str(attempt)
            else:
                user = User(
                    uid=uid,
                    email=email,
                    name=name,
                    avatar_url=avatar_url,
                    telephone_no=telephone_no,
                    school_name=school_name,
                    district_id=effective_district_id,
                    stream=str(stream) if stream else None,
                    grade=str(grade) if grade else None,
                    attempt=str(attempt) if attempt else None,
                )
                self._session.add(user)
                # Initialize clean user_stats record
                initial_stats = UserStats(user_id=uid)
                self._session.add(initial_stats)

            await self._session.flush()
            await self._session.refresh(user)

            # Ensure stats & subscriptions are loaded
            if not user.stats:
                stmt_s = select(UserStats).where(UserStats.user_id == user.uid)
                res_s = await self._session.execute(stmt_s)
                user.stats = res_s.scalar_one_or_none()

            return _serialize_user(user)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc
