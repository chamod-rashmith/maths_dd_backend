"""
FastAPI Router for v1 User Profile operations.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from app.api.deps import get_user_service
from app.core.security import get_current_user
from app.domain.entities import UserEntity
from app.schemas.user import UserProfileResponse, UserProfileSyncRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users v1"])


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserEntity:
    """
    Returns the authenticated student's profile and telemetry stats.
    Verified strictly using Firebase ID token in Authorization header.
    """
    return await service.get_my_profile(current_user)


@router.post("/sync", response_model=UserProfileResponse)
async def sync_user_profile(
    body: UserProfileSyncRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserEntity:
    """
    Idempotent User Profile Sync endpoint.
    Called immediately upon Google Sign-In / App startup with the Firebase ID token.
    Initializes or updates user record securely based on authenticated token identity.
    """
    return await service.sync_profile(current_user, body)
