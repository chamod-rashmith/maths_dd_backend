"""
Pydantic DTO schemas for Subscriptions and Billing Operations.
Enforces strict client payload hygiene without leaking internal database audit fields.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SubscriptionPlan(str, Enum):
    COMBINED_PRO_MONTHLY = "COMBINED_PRO_MONTHLY"
    COMBINED_PRO_ANNUAL = "COMBINED_PRO_ANNUAL"
    PURE_MATHS_TERM = "PURE_MATHS_TERM"
    APPLIED_MATHS_TERM = "APPLIED_MATHS_TERM"
    LIFETIME = "LIFETIME"


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    TRIAL = "TRIAL"
    GRACE_PERIOD = "GRACE_PERIOD"


class SubscriptionProvider(str, Enum):
    REVENUECAT = "REVENUECAT"
    PLAY_STORE = "PLAY_STORE"
    APP_STORE = "APP_STORE"
    BANK_TRANSFER = "BANK_TRANSFER"
    MANUAL_ADMIN = "MANUAL_ADMIN"


class BankSlipUploadRequest(BaseModel):
    """Payload submitted by a student after bank deposit / CDM transfer."""

    plan_id: str = Field(..., description="Target plan ID e.g. COMBINED_PRO_MONTHLY")
    slip_image_url: str = Field(..., description="Public/signed URL to the uploaded slip image in Cloud Storage")
    amount_lkr: float = Field(..., gt=0, description="Amount deposited in LKR")
    reference_note: Optional[str] = Field(
        None, max_length=500, description="Depositor name, bank branch, or CDM transaction reference"
    )


class AdminApprovalRequest(BaseModel):
    """Payload submitted by an Admin to approve a pending bank slip subscription."""

    duration_days: int = Field(30, ge=1, le=730, description="Duration in days to grant access for this payment")
    admin_notes: Optional[str] = Field(None, max_length=500, description="Optional verification note by admin")


class AdminRejectionRequest(BaseModel):
    """Payload submitted by an Admin to reject an invalid or fraudulent bank slip."""

    rejection_reason: str = Field(..., min_length=3, max_length=500, description="Reason displayed to the student")


class UserSubscriptionResponse(BaseModel):
    """Lightweight client representation of a subscription record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    status: str
    provider: str
    starts_at: datetime
    expires_at: Optional[datetime] = None
    amount_lkr: Optional[float] = None
    slip_image_url: Optional[str] = None
    reference_note: Optional[str] = None
    admin_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
