"""
FastAPI Router for v1 User Profile operations.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth import get_current_user
import database

router = APIRouter(prefix="/api/v1/users", tags=["Users v1"])


class UserProfileSyncRequest(BaseModel):
    name: Optional[str] = Field(None, description="Display name from Google Sign-In or User Profile")
    avatar_url: Optional[str] = Field(None, description="Profile picture URL from Google Auth")
    telephone_no: Optional[str] = Field(None, description="Contact phone number")
    school_name: Optional[str] = Field(None, description="School attended by the student")
    district: Optional[str] = Field("Colombo", description="District for provincial exam rankings")
    stream: Optional[str] = Field("PHYSICAL_SCIENCE", description="PHYSICAL_SCIENCE or BIO_SCIENCE")
    grade: Optional[str] = Field("GRADE_12", description="GRADE_12, GRADE_13, or REVISION")
    attempt: Optional[str] = Field("FIRST", description="FIRST, SECOND, or THIRD attempt")


class UserProfileResponse(BaseModel):
    uid: str
    email: str
    name: str
    telephone_no: Optional[str] = None
    role: str = "USER"
    avatar_url: Optional[str] = None
    school_name: Optional[str] = None
    district: str = "Colombo"
    stream: str = "PHYSICAL_SCIENCE"
    grade: str = "GRADE_12"
    attempt: str = "FIRST"
    is_premium: bool = False
    current_streak_days: int = 0
    longest_streak_days: int = 0
    total_solved_count: int = 0
    total_study_time_seconds: int = 0


@router.get("/me", response_model=Dict[str, Any])
async def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns the authenticated student's profile and telemetry stats.
    Verified strictly using Firebase ID token in Authorization header.
    """
    uid = current_user.get("uid")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = await database.get_user_by_uid(uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not initialized yet. Please call /sync first.",
        )
    return user


@router.post("/sync", response_model=Dict[str, Any])
async def sync_user_profile(
    body: UserProfileSyncRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
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

    # Fallback to name from Google token if not supplied in body
    display_name = body.name or current_user.get("name") or email.split("@")[0]
    avatar = body.avatar_url or current_user.get("picture")

    try:
        user_record = await database.sync_or_create_user_profile(
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
        return user_record
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database synchronization failed: {str(e)}",
        )
