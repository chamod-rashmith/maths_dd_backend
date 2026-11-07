"""
Pydantic DTO schemas for Island-Wide & District Student XP Leaderboards (`GET /api/v1/leaderboard`).
මෙම Schema මොඩියුලය මඟින් ලංකාවෙන්ම (Island-wide Top 50), දිස්ත්‍රික්ක මට්ටමින් (District Leaderboard),
සහ ලොග් වී සිටින ශිෂ්‍යයාගේ වත්මන් ස්ථානය (My Current Rank) සඳහා වන දත්ත ආකෘති නිර්වචනය කරයි.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import LeaderboardScope
from app.schemas.district import DistrictResponse


class LeaderboardEntryResponse(BaseModel):
    """
    Single ranked student row in the Island-wide or District Leaderboard.
    Data Minimization & Privacy:
    - Never exposes sensitive contact fields (email, telephone_no) or private user identifiers (user_id / Firebase UID).
    - Exposes student display name, school, district English name, A/L year, and telemetry metrics.
    """

    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., ge=1, description="1-indexed rank in the requested leaderboard scope")
    name: str = Field(..., description="Student's display name")
    avatar_url: str | None = Field(None, description="Student's profile picture URL")
    school_name: str | None = Field(None, description="School attended by the student")
    district_name_en: str | None = Field(None, description="District English name (e.g. 'Colombo', 'Kandy')")
    exam_year: int | None = Field(None, description="Target G.C.E. A/L examination year")
    xp: int = Field(0, ge=0, description="Total verified XP score from UserStats")
    current_streak_days: int = Field(0, ge=0, description="Current continuous daily practice streak")
    total_solved_count: int = Field(0, ge=0, description="Total distinct questions solved")
    is_current_user: bool = Field(False, description="True if this leaderboard entry belongs to the logged-in student")


class MyRankSummaryResponse(BaseModel):
    """
    Authenticated student's personal live ranking across both the Island and their District.
    Displayed in the sticky 'My Current Rank' card on the Leaderboard screen.
    Omits redundant profile/user identifiers (`user_id`, `name`, `avatar_url`, `district`, etc.)
    already loaded from `/users/me`.
    """

    model_config = ConfigDict(from_attributes=True)

    xp: int = Field(0, ge=0, description="Student's total XP")
    current_streak_days: int = Field(0, ge=0, description="Student's current streak days")
    total_solved_count: int = Field(0, ge=0, description="Student's total solved questions")
    island_rank: int = Field(..., ge=1, description="Student's 1-indexed rank across all of Sri Lanka")
    total_island_students: int = Field(..., ge=1, description="Total ranked students island-wide")
    district_rank: int | None = Field(
        None,
        ge=1,
        description="Student's 1-indexed rank within their district (None if no district is set on their profile)",
    )
    total_district_students: int | None = Field(
        None,
        ge=0,
        description="Total ranked students within the student's district",
    )


class LeaderboardResponse(BaseModel):
    """
    Complete response envelope for `GET /api/v1/leaderboard`.
    Includes the Top N leaderboard entries (Island-wide or District-filtered)
    plus the authenticated user's personal Island & District rank (`my_rank`).
    """

    model_config = ConfigDict(from_attributes=True)

    scope: LeaderboardScope = Field(
        LeaderboardScope.ISLAND,
        description="Active leaderboard scope: 'ISLAND' or 'DISTRICT'",
    )
    district: DistrictResponse | None = Field(
        None,
        description="Resolved District metadata when filtered by ?district_id=... (None for Island-wide)",
    )
    exam_year: int | None = Field(
        None,
        description="Optional A/L exam year filter applied to the leaderboard",
    )
    total_students: int = Field(0, ge=0, description="Total students in the current leaderboard scope")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of top entries returned")
    items: list[LeaderboardEntryResponse] = Field(
        default_factory=list,
        description="Ranked list of top students ordered by XP descending",
    )
    my_rank: MyRankSummaryResponse = Field(
        ...,
        description="Logged-in student's current Island-wide and District rank summary",
    )
