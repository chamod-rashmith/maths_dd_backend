"""
PostgreSQL & SQLAlchemy 2.0 ORM implementation of `LeaderboardRepository`.
මෙම Repository මඟින් `UserStats`, `StudentProfile`, `User`, සහ `District` වගු 100% Parameterized
SQLAlchemy 2.0 ORM expressions මඟින් සම්බන්ධ කර Island-Wide Top 50, District Leaderboard,
සහ ශිෂ්‍යයාගේ වත්මන් ස්ථානය (My Current Rank) ගණනය කරයි.
"""

from typing import Any
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import LeaderboardScope
from app.domain.exceptions import DatabaseOperationError, ValidationDomainError
from app.domain.repositories.leaderboard_repository import LeaderboardRepository
from app.models.district import District
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.models.user_stats import UserStats
from app.repositories.district_repository import DistrictRepository


def _ahead_of_user_condition(
    effective_xp: Any,
    effective_solved: Any,
    effective_streak: Any,
    my_xp: int,
    my_solved: int,
    my_streak: int,
    my_uid: str,
) -> Any:
    """
    Pure SQLAlchemy 2.0 boolean expression evaluating whether a row ranks strictly ahead
    of `(my_xp, my_solved, my_streak, my_uid)` under deterministic leaderboard ordering:
    `xp DESC, total_solved_count DESC, current_streak_days DESC, uid ASC`.
    """
    return or_(
        effective_xp > my_xp,
        and_(effective_xp == my_xp, effective_solved > my_solved),
        and_(
            effective_xp == my_xp,
            effective_solved == my_solved,
            effective_streak > my_streak,
        ),
        and_(
            effective_xp == my_xp,
            effective_solved == my_solved,
            effective_streak == my_streak,
            User.uid < my_uid,
        ),
    )


class PostgresLeaderboardRepository(LeaderboardRepository):
    """SQLAlchemy 2.0 AsyncSession implementation for Island-wide & District XP Leaderboards."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._district_repo = DistrictRepository(session)

    async def get_user_rank_summary(
        self,
        current_user: dict[str, Any],
        exam_year: int | None = None,
    ) -> dict[str, Any]:
        """
        Computes the authenticated student's live Island-wide rank and District rank
        using parameterized SQLAlchemy 2.0 ORM aggregate queries.
        """
        try:
            my_uid = str(current_user.get("uid", ""))
            effective_xp = func.coalesce(UserStats.xp, 0)
            effective_solved = func.coalesce(UserStats.total_solved_count, 0)
            effective_streak = func.coalesce(UserStats.current_streak_days, 0)
            effective_district_id = func.coalesce(
                StudentProfile.exam_district_id, User.district_id
            )

            # 1. Fetch the current user's own stats & district row
            me_stmt = (
                select(
                    User.uid,
                    effective_district_id.label("district_id"),
                    effective_xp.label("xp"),
                    effective_streak.label("current_streak_days"),
                    effective_solved.label("total_solved_count"),
                    District.code.label("district_code"),
                    District.name_si.label("district_name_si"),
                )
                .outerjoin(UserStats, UserStats.user_id == User.uid)
                .outerjoin(StudentProfile, StudentProfile.user_id == User.uid)
                .outerjoin(District, District.id == effective_district_id)
                .where(User.uid == my_uid)
            )
            me_row = (await self._session.execute(me_stmt)).first()

            if me_row is not None:
                my_district_id = me_row.district_id
                my_xp = int(me_row.xp or 0)
                my_streak = int(me_row.current_streak_days or 0)
                my_solved = int(me_row.total_solved_count or 0)
                my_district_code = me_row.district_code
                my_district_name_si = me_row.district_name_si
                user_in_db = True
            else:
                my_district_id = current_user.get("district_id")
                my_xp = 0
                my_streak = 0
                my_solved = 0
                my_district_code = None
                my_district_name_si = None
                user_in_db = False

                if my_district_id is not None:
                    d_info = await self._district_repo.resolve_district(my_district_id)
                    if d_info:
                        my_district_id = int(d_info["id"])
                        my_district_code = d_info.get("code")
                        my_district_name_si = d_info.get("name_si")

            ahead_cond = _ahead_of_user_condition(
                effective_xp=effective_xp,
                effective_solved=effective_solved,
                effective_streak=effective_streak,
                my_xp=my_xp,
                my_solved=my_solved,
                my_streak=my_streak,
                my_uid=my_uid,
            )

            # 2. Island-wide total students & current user's 1-indexed Island rank
            island_base_filters = [User.role == "USER"]
            if exam_year is not None:
                island_base_filters.append(StudentProfile.exam_year == exam_year)

            total_island_stmt = (
                select(func.count(User.uid))
                .outerjoin(UserStats, UserStats.user_id == User.uid)
                .outerjoin(StudentProfile, StudentProfile.user_id == User.uid)
                .where(*island_base_filters)
            )

            total_island_count = int(
                (await self._session.execute(total_island_stmt)).scalar_one() or 0
            )
            if not user_in_db:
                total_island_count += 1

            island_ahead_stmt = (
                select(func.count(User.uid))
                .outerjoin(UserStats, UserStats.user_id == User.uid)
                .outerjoin(StudentProfile, StudentProfile.user_id == User.uid)
                .where(ahead_cond, *island_base_filters)
            )
            island_ahead_count = int(
                (await self._session.execute(island_ahead_stmt)).scalar_one() or 0
            )
            island_rank = island_ahead_count + 1
            total_island_students = max(total_island_count, island_rank)

            # 3. District-level rank & total students (if the student has a district)
            district_rank: int | None = None
            total_district_students: int | None = None

            if my_district_id is not None:
                district_filters = [
                    User.role == "USER",
                    effective_district_id == my_district_id,
                ]
                if exam_year is not None:
                    district_filters.append(StudentProfile.exam_year == exam_year)

                total_dist_stmt = (
                    select(func.count(User.uid))
                    .outerjoin(UserStats, UserStats.user_id == User.uid)
                    .outerjoin(StudentProfile, StudentProfile.user_id == User.uid)
                    .where(*district_filters)
                )
                dist_total = int(
                    (await self._session.execute(total_dist_stmt)).scalar_one() or 0
                )
                if not user_in_db:
                    dist_total += 1

                dist_ahead_stmt = (
                    select(func.count(User.uid))
                    .outerjoin(UserStats, UserStats.user_id == User.uid)
                    .outerjoin(StudentProfile, StudentProfile.user_id == User.uid)
                    .where(ahead_cond, *district_filters)
                )
                dist_ahead = int(
                    (await self._session.execute(dist_ahead_stmt)).scalar_one() or 0
                )
                district_rank = dist_ahead + 1
                total_district_students = max(dist_total, district_rank)

            return {
                "user_id": my_uid,
                "district_code": my_district_code,
                "district_name_si": my_district_name_si,
                "xp": my_xp,
                "current_streak_days": my_streak,
                "total_solved_count": my_solved,
                "island_rank": island_rank,
                "total_island_students": total_island_students,
                "district_rank": district_rank,
                "total_district_students": total_district_students,
            }
        except (ValidationDomainError, DatabaseOperationError):
            raise
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc

    async def get_leaderboard(
        self,
        current_user: dict[str, Any],
        district_identifier: int | str | None = None,
        exam_year: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Fetches the Top N students (Island-wide or filtered by District) ordered by:
        1. `xp DESC`
        2. `total_solved_count DESC`
        3. `current_streak_days DESC`
        4. `uid ASC`
        Along with the authenticated student's `my_rank` summary.
        """
        try:
            my_uid = str(current_user.get("uid", ""))
            resolved_district: dict[str, Any] | None = None
            scope = LeaderboardScope.ISLAND

            if district_identifier is not None and str(district_identifier).strip() != "":
                resolved_district = await self._district_repo.resolve_district(
                    district_identifier
                )
                if not resolved_district:
                    raise ValidationDomainError(
                        f"Invalid district identifier '{district_identifier}'. "
                        "Provide a valid Sri Lankan district ID (1-25), code (e.g. 'COLOMBO'), or abbreviation (e.g. 'CMB')."
                    )
                scope = LeaderboardScope.DISTRICT

            effective_xp = func.coalesce(UserStats.xp, 0)
            effective_solved = func.coalesce(UserStats.total_solved_count, 0)
            effective_streak = func.coalesce(UserStats.current_streak_days, 0)
            effective_district_id = func.coalesce(
                StudentProfile.exam_district_id, User.district_id
            )
            effective_school = func.coalesce(
                StudentProfile.school_name, User.school_name
            )

            filters = [User.role == "USER"]
            if resolved_district is not None:
                filters.append(effective_district_id == int(resolved_district["id"]))
            if exam_year is not None:
                filters.append(StudentProfile.exam_year == exam_year)

            # 1. Count total students in the requested leaderboard scope
            count_stmt = (
                select(func.count(User.uid))
                .outerjoin(UserStats, UserStats.user_id == User.uid)
                .outerjoin(StudentProfile, StudentProfile.user_id == User.uid)
                .where(*filters)
            )
            total_students = int(
                (await self._session.execute(count_stmt)).scalar_one() or 0
            )

            # 2. Fetch Top N leaderboard entries
            top_stmt = (
                select(
                    User.uid,
                    User.name,
                    User.avatar_url,
                    effective_school.label("school_name"),
                    StudentProfile.exam_year.label("exam_year"),
                    effective_xp.label("xp"),
                    effective_streak.label("current_streak_days"),
                    effective_solved.label("total_solved_count"),
                    District.code.label("district_code"),
                    District.name_si.label("district_name_si"),
                )
                .outerjoin(UserStats, UserStats.user_id == User.uid)
                .outerjoin(StudentProfile, StudentProfile.user_id == User.uid)
                .outerjoin(District, District.id == effective_district_id)
                .where(*filters)
                .order_by(
                    effective_xp.desc(),
                    effective_solved.desc(),
                    effective_streak.desc(),
                    User.uid.asc(),
                )
                .limit(limit)
                .offset(offset)
            )

            rows = (await self._session.execute(top_stmt)).all()

            items: list[dict[str, Any]] = []
            for idx, row in enumerate(rows, start=offset + 1):
                items.append(
                    {
                        "rank": idx,
                        "user_id": row.uid,
                        "name": row.name,
                        "avatar_url": row.avatar_url,
                        "school_name": row.school_name,
                        "district_code": row.district_code,
                        "district_name_si": row.district_name_si,
                        "exam_year": row.exam_year,
                        "xp": int(row.xp or 0),
                        "current_streak_days": int(row.current_streak_days or 0),
                        "total_solved_count": int(row.total_solved_count or 0),
                        "is_current_user": (row.uid == my_uid),
                    }
                )

            # 3. Compute the authenticated user's personal Island & District rank
            my_rank = await self.get_user_rank_summary(
                current_user=current_user,
                exam_year=exam_year,
            )

            return {
                "scope": scope,
                "district": resolved_district,
                "exam_year": exam_year,
                "total_students": total_students,
                "limit": limit,
                "items": items,
                "my_rank": my_rank,
            }
        except (ValidationDomainError, DatabaseOperationError):
            raise
        except Exception as exc:
            raise DatabaseOperationError(str(exc)) from exc
