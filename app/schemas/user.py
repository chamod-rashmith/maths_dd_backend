"""
Pydantic DTO schemas for User Profile operations.
Enforces type-safe UserRole, StudyStream, StudentGrade, ExamMedium, and ExamAttempt enums.

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

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import (
    ExamAttempt,
    ExamMedium,
    StudentGrade,
    StudyStream,
    UserRole,
)
from app.schemas.district import DistrictResponse
from app.schemas.subscription import UserSubscriptionResponse


class UserProfileSyncRequest(BaseModel):
    """
    Request payload for synchronizing a user profile after authentication or profile edit.
    """

    name: str | None = Field(
        None, description="Display name from Google Sign-In or User Profile"
    )
    avatar_url: str | None = Field(
        None, description="Profile picture URL from Google Auth"
    )
    telephone_no: str | None = Field(None, description="Contact phone number")
    school_name: str | None = Field(
        None, description="School attended by the student"
    )

    # -------------------------------------------------------------------------
    # Normalized Domain 1 Fields (A/L විභාග ශාස්ත්‍රීය දත්ත)
    # -------------------------------------------------------------------------
    exam_year: int | None = Field(
        None,
        ge=2020,
        le=2040,
        description="Target G.C.E. A/L examination year (e.g. 2025, 2026, 2027)",
    )
    attempt_number: int | None = Field(
        None,
        ge=1,
        le=3,
        description="Sitting attempt number: 1 (1st shy), 2 (2nd shy), 3 (3rd shy)",
    )
    exam_district_id: int | None = Field(
        None,
        description="Official Sri Lankan District integer ID (1-25) for Z-Score calculation",
    )
    medium: ExamMedium | str | None = Field(
        ExamMedium.SINHALA,
        description="Examination medium (SINHALA, ENGLISH, TAMIL)",
    )

    # -------------------------------------------------------------------------
    # Regional Residential District Fields
    # -------------------------------------------------------------------------
    district_id: int | None = Field(
        None, description="Sri Lankan District integer ID (1-25)"
    )
    district_code: str | None = Field(
        None, description="Sri Lankan District slug code (e.g. 'COLOMBO', 'KANDY')"
    )
    district: int | str | None = Field(
        None, description="Legacy fallback field for district (accepts ID or code)"
    )

    # -------------------------------------------------------------------------
    # Academic Study Stream & Grade
    # -------------------------------------------------------------------------
    stream: StudyStream | None = Field(
        None, description="PHYSICAL_SCIENCE, BIO_SCIENCE, etc."
    )
    grade: StudentGrade | None = Field(
        None, description="GRADE_12, GRADE_13, or REVISION"
    )
    attempt: ExamAttempt | None = Field(
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
    telephone_no: str | None = None
    role: UserRole = UserRole.USER
    avatar_url: str | None = None
    school_name: str | None = None

    # Regional & Z-Score data
    district_id: int | None = None
    district: DistrictResponse | None = None
    exam_district_id: int | None = None
    exam_district: DistrictResponse | None = None

    # Academic Syllabus & Target Exam
    exam_year: int | None = None
    attempt_number: int | None = None
    medium: ExamMedium | str | None = ExamMedium.SINHALA
    stream: StudyStream | str | None = None
    grade: StudentGrade | str | None = None
    attempt: ExamAttempt | str | None = None

    # Gamification & Telemetry stats
    xp: int = 0
    streak_count: int = 0
    accuracy_rate: float = 0.0
    questions_solved: int = 0

    # Subscription state
    is_premium: bool = False
    active_subscription: UserSubscriptionResponse | None = None
