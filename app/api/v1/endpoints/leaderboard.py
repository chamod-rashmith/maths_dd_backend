"""
FastAPI Router for Island-Wide & District Student XP Leaderboards (`GET /api/v1/leaderboard`).
මෙම API මොඩියුලය මඟින්:
1. Island-wide Top 50 (`GET /api/v1/leaderboard` — ලංකාවෙන්ම වැඩිම XP ගත්ත ළමයි)
2. District Leaderboard (`GET /api/v1/leaderboard?district_id=CMB` — තමන්ගේ දිස්ත්‍රික්කයේ Top ළමයි)
3. My Current Rank (`my_rank` සහ `GET /api/v1/leaderboard/me` — ලොග් වී සිටින ශිෂ්‍යයා ලංකාවෙන්ම සහ දිස්ත්‍රික්කයෙන් කීවෙනියාද යන්න)
ලබා දෙයි.
"""

from typing import Any
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_leaderboard_service
from app.core.security import get_current_user
from app.schemas.leaderboard import LeaderboardResponse, MyRankSummaryResponse
from app.services.leaderboard_service import LeaderboardService

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard v1"])


@router.get(
    "",
    response_model=LeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Island-Wide or District Top 50 Leaderboard & My Current Rank",
    description=(
        "Returns the Top 50 students ranked by verified XP (`UserStats.xp`), solved count, and active streak.\n\n"
        "- **Island-Wide Top 50:** Call `GET /api/v1/leaderboard` without `district_id`.\n"
        "- **District Leaderboard:** Pass `?district_id=CMB` (or `?district_id=COLOMBO` or `?district_id=1`) to filter by Sri Lankan administrative district.\n"
        "- **My Current Rank:** Always includes `my_rank` showing the logged-in student's live 1-indexed Island-wide rank (`island_rank`) and District rank (`district_rank`)."
    ),
)
async def get_leaderboard(
    district_id: str | None = Query(
        None,
        description="Optional Sri Lankan District filter: accepts 3-letter code ('CMB', 'KDY'), full code ('COLOMBO'), or integer ID ('1'-'25'). Omit for Island-wide Top 50.",
    ),
    exam_year: int | None = Query(
        None,
        ge=2020,
        le=2040,
        description="Optional G.C.E. A/L target examination year filter (e.g. 2026)",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of top students to return (default 10)",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Pagination offset (0-indexed; rank numbers start at offset + 1)",
    ),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: LeaderboardService = Depends(get_leaderboard_service),
) -> LeaderboardResponse:
    """ලංකාවෙන්ම හෝ දිස්ත්‍රික්ක මට්ටමින් Top 50 ශ්‍රේණිගත කිරීම් සහ ශිෂ්‍යයාගේ වත්මන් ස්ථානය ලබා ගැනීම."""
    return await service.get_leaderboard(
        current_user=current_user,
        district_id=district_id,
        exam_year=exam_year,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/me",
    response_model=MyRankSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get My Current Island-Wide & District Rank",
    description=(
        "Returns only the authenticated student's live Island-wide rank (`island_rank`) "
        "and District rank (`district_rank`) along with their XP, streak, and solved count."
    ),
)
async def get_my_current_rank(
    exam_year: int | None = Query(
        None,
        ge=2020,
        le=2040,
        description="Optional G.C.E. A/L target examination year filter",
    ),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: LeaderboardService = Depends(get_leaderboard_service),
) -> MyRankSummaryResponse:
    """ලොග් වී සිටින ශිෂ්‍යයා දැනට ලංකාවෙන්ම සහ දිස්ත්‍රික්කයෙන් කීවෙනියාද යන්න ලබා ගැනීම."""
    return await service.get_my_rank(
        current_user=current_user,
        exam_year=exam_year,
    )
