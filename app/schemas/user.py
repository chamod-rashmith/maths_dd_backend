"""
Pydantic DTO schemas for User Profile operations.
Enforces type-safe UserRole, StudyStream, StudentGrade, and ExamAttempt enums.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ExamAttempt, StudentGrade, StudyStream, UserRole
from app.schemas.district import DistrictResponse
from app.schemas.subscription import UserSubscriptionResponse


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
    district_id: Optional[str] = Field(
        None, description="Sri Lankan District identifier (e.g. 'COLOMBO', 'KANDY')"
    )
    district: Optional[str] = Field(
        None, description="Legacy fallback field for district identifier"
    )
    stream: Optional[StudyStream] = Field(
        None, description="PHYSICAL_SCIENCE, BIO_SCIENCE, etc."
    )
    grade: Optional[StudentGrade] = Field(
        None, description="GRADE_12, GRADE_13, or REVISION"
    )
    attempt: Optional[ExamAttempt] = Field(
        None, description="FIRST, SECOND, or THIRD attempt"
    )

    @model_validator(mode="after")
    def resolve_district_id(self) -> "UserProfileSyncRequest":
        """Resolve legacy district field into district_id if needed."""
        if not self.district_id and self.district:
            self.district_id = self.district.strip().upper()
        return self


class UserProfileResponse(BaseModel):
    """Clean lightweight response model representing a student's profile and telemetry stats."""

    model_config = ConfigDict(from_attributes=True)

    uid: str
    email: str
    name: str
    telephone_no: Optional[str] = None
    role: UserRole = UserRole.USER
    avatar_url: Optional[str] = None
    school_name: Optional[str] = None
    district_id: Optional[str] = None
    district: Optional[DistrictResponse] = None
    stream: Optional[str] = None
    grade: Optional[str] = None
    attempt: Optional[str] = None
    xp: Optional[int] = 0
    streak_count: Optional[int] = 0
    accuracy_rate: Optional[float] = 0.0
    questions_solved: Optional[int] = 0
    is_premium: bool = False
    active_subscription: Optional[UserSubscriptionResponse] = None
