"""
PostgreSQL UserRepository implementation using modern SQLAlchemy 2.0.

===============================================================================
පරිශීලක සහ ශාස්ත්‍රීය පැතිකඩ Repository ක්‍රියාත්මක කිරීම (Postgres User Repository):
-------------------------------------------------------------------------------
1. User identity සහ authentication data (`users` table) කළමනාකරණය.
2. Normalized `StudentProfile` (`student_profiles` table) සමඟ 1-to-1 sync කිරීම:
   - `exam_year`: Target A/L Year (e.g. 2025, 2026, 2027)
   - `attempt_number`: Sitting attempt (1 = 1st shy, 2 = 2nd shy, 3 = 3rd shy)
   - `exam_district_id`: Z-Score ගණනය කරන නිල විභාග දිස්ත්‍රික්කය
   - `medium`: විභාග මාධ්‍යය (SINHALA, ENGLISH, TAMIL)
3. 100% Backward Compatibility:
   - Legacy frontend request එකකින් `district` හෝ `attempt` පමණක් එවුවද,
     එය ස්වයංක්‍රීයව `StudentProfile` වෙත map වී normalize වේ.
===============================================================================
"""

from typing import Any, Dict, Optional, Union
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.domain.exceptions import DatabaseOperationError, PermissionDeniedError
from app.domain.repositories.user_repository import UserRepository
from app.core.field_encryption import decrypt_field, encrypt_field
from app.models.district import District
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.models.user_stats import UserStats


def _serialize_user(user: User) -> Dict[str, Any]:
    """Helper to cleanly serialize User and normalized StudentProfile ORM models."""
    stats = user.stats
    xp = stats.xp if stats else 0
    current_streak_days = stats.current_streak_days if stats else 0
    accuracy_rate = stats.accuracy_rate if stats else 0.0
    total_solved_count = stats.total_solved_count if stats else 0

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
        }

    # Extract normalized student_profile data
    profile = user.student_profile
    exam_year = profile.exam_year if profile else None
    attempt_number = profile.attempt_number if profile else None
    medium = profile.medium if profile else "SINHALA"

    # Derive attempt_number fallback from legacy attempt string if needed
    attempt_str = user.attempt
    if attempt_number is None and attempt_str is not None:
        upper_att = attempt_str.upper()
        if "FIRST" in upper_att or "1" in upper_att:
            attempt_number = 1
        elif "SECOND" in upper_att or "2" in upper_att:
            attempt_number = 2
        elif "THIRD" in upper_att or "3" in upper_att:
            attempt_number = 3

    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.name,
        "telephone_no": decrypt_field(user.telephone_no),
        "role": user.role,
        "avatar_url": user.avatar_url,
        "school_name": profile.school_name if (profile and profile.school_name) else user.school_name,
        "district": user.district,
        "exam_year": exam_year,
        "attempt_number": attempt_number,
        "medium": medium,
        "stream": profile.stream if (profile and profile.stream) else user.stream,
        "grade": user.grade,
        "xp": xp,
        "current_streak_days": current_streak_days,
        "accuracy_rate": accuracy_rate,
        "total_solved_count": total_solved_count,
        "is_premium": user.is_premium,
        "active_subscription": active_sub_payload,
    }


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of `UserRepository` using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _resolve_district(self, raw_val: Optional[Union[int, str]]) -> Optional[int]:
        """Helper to resolve integer ID or slug string (e.g. 'COLOMBO') into district integer ID (1-25)."""
        if raw_val is None:
            return None
        if isinstance(raw_val, int):
            return raw_val
        s = str(raw_val).strip()
        if s.isdigit():
            return int(s)
        d_stmt = select(District.id).where(func.upper(District.code) == s.upper())
        d_res = await self._session.execute(d_stmt)
        return d_res.scalar_one_or_none()

    async def get_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """Fetches user record by Firebase UID including StudentProfile, stats, and subscriptions."""
        try:
            result = await self._session.execute(
                select(User)
                .options(
                    selectinload(User.stats),
                    selectinload(User.subscriptions),
                    joinedload(User.district),
                    joinedload(User.student_profile),
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
        district_id: Optional[Union[int, str]] = None,
        district: Optional[Union[int, str]] = None,
        stream: Optional[str] = None,
        grade: Optional[str] = None,
        attempt: Optional[str] = None,
        exam_year: Optional[int] = None,
        attempt_number: Optional[int] = None,
        exam_district_id: Optional[Union[int, str]] = None,
        medium: Optional[str] = "SINHALA",
    ) -> Dict[str, Any]:
        """
        Idempotently synchronizes user identity, academic profile, and stats.
        """
        try:
            # 1. Resolve district IDs (accepts district_id, district, or exam_district_id and keeps them unified)
            raw_district = (
                district_id
                if district_id is not None
                else (district if district is not None else exam_district_id)
            )
            resolved_district_id = await self._resolve_district(raw_district)
            resolved_exam_district_id = (
                await self._resolve_district(exam_district_id) or resolved_district_id
            )

            # 2. Derive attempt_number <-> attempt
            resolved_attempt_number = attempt_number
            resolved_attempt_str = attempt
            if resolved_attempt_number is None and resolved_attempt_str is not None:
                upper_a = resolved_attempt_str.upper()
                if "FIRST" in upper_a or "1" in upper_a:
                    resolved_attempt_number = 1
                elif "SECOND" in upper_a or "2" in upper_a:
                    resolved_attempt_number = 2
                elif "THIRD" in upper_a or "3" in upper_a:
                    resolved_attempt_number = 3
            elif resolved_attempt_number is not None and resolved_attempt_str is None:
                if resolved_attempt_number == 1:
                    resolved_attempt_str = "FIRST"
                elif resolved_attempt_number == 2:
                    resolved_attempt_str = "SECOND"
                elif resolved_attempt_number == 3:
                    resolved_attempt_str = "THIRD"

            # 3. Query existing user by uid
            result = await self._session.execute(
                select(User)
                .options(
                    selectinload(User.stats),
                    selectinload(User.subscriptions),
                    joinedload(User.district),
                    joinedload(User.student_profile),
                )
                .where(User.uid == uid)
            )
            user = result.scalar_one_or_none()

            # 4. Never rebind an existing account to a different Firebase UID.
            # Email matching alone does not prove ownership of the existing account.
            if not user:
                result_email = await self._session.execute(
                    select(User)
                    .options(
                        selectinload(User.stats),
                        selectinload(User.subscriptions),
                        joinedload(User.district),
                        joinedload(User.student_profile),
                    )
                    .where(func.lower(User.email) == email.lower())
                )
                user = result_email.scalar_one_or_none()
                if user:
                    raise PermissionDeniedError(
                        "A user profile already exists for this email with a different "
                        "authentication identity. Use the account-linking or recovery flow."
                    )

            # 5. Update or insert User record
            if user:
                if name and name.strip():
                    user.name = name
                if avatar_url is not None:
                    user.avatar_url = avatar_url
                if telephone_no is not None:
                    user.telephone_no = encrypt_field(telephone_no)
                if school_name is not None:
                    user.school_name = school_name
                if raw_district is not None:
                    user.district_id = resolved_district_id
                if stream is not None:
                    user.stream = str(stream)
                if grade is not None:
                    user.grade = str(grade)
                if resolved_attempt_str is not None:
                    user.attempt = str(resolved_attempt_str)
            else:
                user = User(
                    uid=uid,
                    email=email,
                    name=name,
                    avatar_url=avatar_url,
                    telephone_no=encrypt_field(telephone_no),
                    school_name=school_name,
                    district_id=resolved_district_id,
                    stream=str(stream) if stream else None,
                    grade=str(grade) if grade else None,
                    attempt=str(resolved_attempt_str) if resolved_attempt_str else None,
                )
                self._session.add(user)
                # Initialize default stats record
                initial_stats = UserStats(user_id=uid)
                self._session.add(initial_stats)

            # 6. Synchronize normalized 1-to-1 StudentProfile
            profile = user.student_profile
            if profile:
                if exam_year is not None:
                    profile.exam_year = exam_year
                if resolved_attempt_number is not None:
                    profile.attempt_number = resolved_attempt_number
                if resolved_exam_district_id is not None:
                    profile.exam_district_id = resolved_exam_district_id
                if school_name is not None:
                    profile.school_name = school_name
                if stream is not None:
                    profile.stream = str(stream)
                if medium is not None:
                    profile.medium = str(medium)
            else:
                new_profile = StudentProfile(
                    user_id=uid,
                    exam_year=exam_year,
                    attempt_number=resolved_attempt_number,
                    exam_district_id=resolved_exam_district_id,
                    school_name=school_name or user.school_name,
                    stream=str(stream) if stream else user.stream,
                    medium=str(medium) if medium else "SINHALA",
                )
                self._session.add(new_profile)
                user.student_profile = new_profile

            await self._session.flush()
            await self._session.refresh(user)

            # Ensure stats are loaded
            if not user.stats:
                stmt_s = select(UserStats).where(UserStats.user_id == user.uid)
                res_s = await self._session.execute(stmt_s)
                user.stats = res_s.scalar_one_or_none()

            return _serialize_user(user)
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc
