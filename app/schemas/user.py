"""
Pydantic DTO schemas for User Profile operations.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserProfileSyncRequest(BaseModel):
    """Request payload for synchronizing a user profile after authentication."""

    name: Optional[str] = Field(
        None, description="Display name from Google Sign-In or User Profile"
    )
    avatar_url: Optional[str] = Field(
        None, description="Profile picture URL from Google Auth"
    )
    telephone_no: Optional[str] = Field(None, description="Contact phone number")
    school_name: Optional[str] = Field(
        None, description="School attended by the student"
    )
    district: Optional[str] = Field(
        None, description="District for provincial exam rankings"
    )
    stream: Optional[str] = Field(
        None, description="PHYSICAL_SCIENCE or BIO_SCIENCE"
    )
    grade: Optional[str] = Field(
        None, description="GRADE_12, GRADE_13, or REVISION"
    )
    attempt: Optional[str] = Field(
        None, description="FIRST, SECOND, or THIRD attempt"
    )


class UserProfileResponse(BaseModel):
    """Response model representing a student's user profile and telemetry stats."""

    uid: str
    email: str
    name: str
    telephone_no: Optional[str] = None
    role: str = "USER"
    avatar_url: Optional[str] = None
    school_name: Optional[str] = None
    district: Optional[str] = None
    stream: Optional[str] = None
    grade: Optional[str] = None
    attempt: Optional[str] = None
    is_premium: bool = False
    current_streak_days: int = 0
    longest_streak_days: int = 0
    total_solved_count: int = 0
    total_study_time_seconds: int = 0
    last_active_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
