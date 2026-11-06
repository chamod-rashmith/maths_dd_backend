"""
API Endpoint for Sri Lankan Administrative Districts.
Publicly accessible and cached persistently with Redis.
"""

from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.district_repository import DistrictRepository
from app.schemas.district import DistrictResponse

router = APIRouter(prefix="/districts", tags=["Districts"])


@router.get(
    "",
    response_model=List[DistrictResponse],
    summary="Get all Sri Lankan Administrative Districts",
    description="Returns all 25 Sri Lankan districts with Sinhala, Tamil, and English localization and provincial mapping. Requires authentication and is backed by persistent Redis caching.",
)
async def get_districts(
    _current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[DistrictResponse]:
    """Retrieve all 25 administrative districts (requires authenticated user)."""
    repo = DistrictRepository(session)
    districts = await repo.get_all()
    return [DistrictResponse.model_validate(d) for d in districts]
