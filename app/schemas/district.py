"""
Pydantic DTO schemas for Sri Lankan Administrative Districts.
Used for client-side dropdown selection, localization, and regional leaderboards.
"""

from pydantic import BaseModel, ConfigDict

from app.domain.enums import Province


class DistrictResponse(BaseModel):
    """District response object with integer ID, unique string code, and type-safe Province enum."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name_en: str
    name_si: str
    name_ta: str
    province: Province | str


class UserDistrictSummary(BaseModel):
    """
    Lightweight District representation for Student Profile responses (`/api/v1/users/me`).
    Omits heavy/unused localized names (name_ta, name_si) and regional groupings (province)
    to keep personal profile payloads minimal.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name_en: str


