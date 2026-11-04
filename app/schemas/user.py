"""
Pydantic DTO schemas for User Profile operations.
Enforces type-safe UserRole, StudyStream, StudentGrade, and ExamAttempt enums.

===============================================================================
පරිශීලක සහ ශාස්ත්‍රීය පැතිකඩ DTO Schemas (User & Student Profile DTOs):
-------------------------------------------------------------------------------
1. `UserProfileSyncRequest`:
   - Google Auth හෝ Setup Profile පියවරේදී ලැබෙන දත්ත ලබාගැනීම.
   - `exam_year` (2025/2026/2027), `attempt_number` (1/2/3 shy), සහ
     `exam_district_id` (Z-Score දිස්ත්‍රික්කය) සුරක්ෂිතව type-check කරයි.
   - Legacy `attempt` සහ `district` fields සමඟ 100% backward compatible වේ.
2. `UserProfileResponse`:
   - Client වෙත සම්පූර්ණ Profile, Stats, Subscription, සහ Normalized Student Profile
     දත්ත ලබාදෙන ප්‍රතිචාර schema එක.
===============================================================================
"""

from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ExamAttempt, StudentGrade, StudyStream, UserRole
from app.schemas.district import DistrictResponse
from app.schemas.subscription import UserSubscriptionResponse


class UserProfileSyncRequest(BaseModel):
    """
    Request payload for synchronizing a user profile after authentication or profile edit.
    """

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

    # -------------------------------------------------------------------------
    # Normalized Domain 1 Fields (A/L විභාග ශාස්ත්‍රීය දත්ත)
    # -------------------------------------------------------------------------
    exam_year: Optional[int] = Field(
        None,
        ge=2020,
        le=2040,
        description="Target G.C.E. A/L examination year (e.g. 2025, 2026, 2027)",
    )
    attempt_number: Optional[int] = Field(
        None,
        ge=1,
        le=3,
        description="Sitting attempt number: 1 (1st shy), 2 (2nd shy), 3 (3rd shy)",
    )
    exam_district_id: Optional[int] = Field(
        None,
        description="Official Sri Lankan District integer ID (1-25) for Z-Score calculation",
    )
    medium: Optional[str] = Field(
        "SINHALA",
        description="Examination medium (SINHALA, ENGLISH, TAMIL)",
    )

    # -------------------------------------------------------------------------
    # Regional Residential District Fields
    # -------------------------------------------------------------------------
    district_id: Optional[int] = Field(
        None, description="Sri Lankan District integer ID (1-25)"
    )
    district_code: Optional[str] = Field(
        None, description="Sri Lankan District slug code (e.g. 'COLOMBO', 'KANDY')"
    )
    district: Optional[Union[int, str]] = Field(
        None, description="Legacy fallback field for district (accepts ID or code)"
    )

    # -------------------------------------------------------------------------
    # Academic Study Stream & Grade
    # -------------------------------------------------------------------------
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
    def resolve_normalized_and_legacy_fields(self) -> "UserProfileSyncRequest":
        """
        Harmonizes legacy fields with normalized Domain 1 fields:
        - Resolves district string/integer to district_id and propagates to exam_district_id if missing.
        - Synchronizes attempt enum with attempt_number (1, 2, 3).
        """
        # 1. District resolution
        if self.district_id is None and self.district is not None:
            if isinstance(self.district, int):
                self.district_id = self.district
            elif isinstance(self.district, str):
                if self.district.strip().isdigit():
                    self.district_id = int(self.district.strip())
                else:
                    self.district_code = self.district.strip().upper()

        if self.exam_district_id is None and self.district_id is not None:
            self.exam_district_id = self.district_id

        # 2. Attempt number <-> Attempt enum resolution
        if self.attempt_number is not None and self.attempt is None:
            if self.attempt_number == 1:
                self.attempt = ExamAttempt.FIRST
            elif self.attempt_number == 2:
                self.attempt = ExamAttempt.SECOND
            elif self.attempt_number == 3:
                self.attempt = ExamAttempt.THIRD
        elif self.attempt is not None and self.attempt_number is None:
            att_str = str(self.attempt.value if hasattr(self.attempt, "value") else self.attempt).upper()
            if "FIRST" in att_str or "1" in att_str:
                self.attempt_number = 1
            elif "SECOND" in att_str or "2" in att_str:
                self.attempt_number = 2
            elif "THIRD" in att_str or "3" in att_str:
                self.attempt_number = 3

        return self


class UserProfileResponse(BaseModel):
    """Clean lightweight response model representing a student's profile, academic status, and telemetry stats."""

    model_config = ConfigDict(from_attributes=True)

    uid: str
    email: str
    name: str
    telephone_no: Optional[str] = None
    role: UserRole = UserRole.USER
    avatar_url: Optional[str] = None
    school_name: Optional[str] = None

    # Regional & Z-Score data
    district_id: Optional[int] = None
    district: Optional[DistrictResponse] = None
    exam_district_id: Optional[int] = None
    exam_district: Optional[DistrictResponse] = None

    # Academic Syllabus & Target Exam
    exam_year: Optional[int] = None
    attempt_number: Optional[int] = None
    medium: Optional[str] = "SINHALA"
    stream: Optional[str] = None
    grade: Optional[str] = None
    attempt: Optional[str] = None

    # Gamification & Telemetry stats
    xp: Optional[int] = 0
    streak_count: Optional[int] = 0
    accuracy_rate: Optional[float] = 0.0
    questions_solved: Optional[int] = 0

    # Subscription state
    is_premium: bool = False
    active_subscription: Optional[UserSubscriptionResponse] = None
