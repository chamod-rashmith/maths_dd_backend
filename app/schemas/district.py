"""
Pydantic DTO schemas for Sri Lankan Administrative Districts.
Used for client-side dropdown selection, localization, and regional leaderboards.
"""

from pydantic import BaseModel, ConfigDict


class DistrictResponse(BaseModel):
    """District response object with integer ID and unique string code."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name_en: str
    name_si: str
    name_ta: str
    province: str
    display_order: int
