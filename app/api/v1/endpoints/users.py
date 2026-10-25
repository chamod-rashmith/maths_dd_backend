"""
FastAPI Router for v1 User Profile operations.
"""

from typing import Dict, Any
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileResponse, UserProfileSyncRequest

router = APIRouter(prefix="/users", tags=["Users v1"])


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns the authenticated student's profile and telemetry stats.
    Verified strictly using Firebase ID token in Authorization header.
    """
    uid = current_user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    repo = UserRepository(conn)
    user = await repo.get_by_uid(uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not initialized yet. Please call /sync first.",
        )
    return user


@router.post("/sync", response_model=UserProfileResponse)
async def sync_user_profile(
    body: UserProfileSyncRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """
    Idempotent User Profile Sync endpoint.
    Called immediately upon Google Sign-In / App startup with the Firebase ID token.
    Initializes or updates user record securely based on authenticated token identity.
    """
    uid = current_user.get("uid")
    email = current_user.get("email")

    if not uid or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token must include both uid and email.",
        )

    display_name = body.name or current_user.get("name") or email.split("@")[0]
    avatar = body.avatar_url or current_user.get("picture")

    repo = UserRepository(conn)
    try:
        return await repo.sync_or_create(
            uid=uid,
            email=email,
            name=display_name,
            avatar_url=avatar,
            telephone_no=body.telephone_no,
            school_name=body.school_name,
            district=body.district,
            stream=body.stream,
            grade=body.grade,
            attempt=body.attempt,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database synchronization failed: {str(exc)}",
        )
