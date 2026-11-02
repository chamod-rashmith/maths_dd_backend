"""
Pydantic DTO schemas for Sri Lankan Administrative Districts.
Used for client-side dropdown selection, localization, and regional leaderboards.
"""

from pydantic import BaseModel, ConfigDict


class DistrictResponse(BaseModel):
    """District response object for client-side display and localized selection."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name_en: str
    name_si: str
    name_ta: str
    province: str
    display_order: int
