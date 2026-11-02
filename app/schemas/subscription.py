"""
Pydantic DTO schemas for Subscriptions and Billing Operations.
Enforces strict client payload hygiene without leaking internal database audit fields.
Supports both RevenueCat automated store webhooks and Sri Lankan direct bank slip workflows.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SubscriptionPlan(str, Enum):
    """Available educational subscription plans."""

    COMBINED_PRO_MONTHLY = "COMBINED_PRO_MONTHLY"
    COMBINED_PRO_ANNUAL = "COMBINED_PRO_ANNUAL"
    PURE_MATHS_TERM = "PURE_MATHS_TERM"
    APPLIED_MATHS_TERM = "APPLIED_MATHS_TERM"
    LIFETIME = "LIFETIME"


class SubscriptionStatus(str, Enum):
    """Lifecycle statuses for user subscriptions."""

    ACTIVE = "ACTIVE"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    TRIAL = "TRIAL"
    GRACE_PERIOD = "GRACE_PERIOD"


class SubscriptionProvider(str, Enum):
    """Payment channels and providers."""

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


class SignedUploadUrlResponse(BaseModel):
    """Pre-signed GCS upload URL response for direct client-to-cloud storage uploads."""

    upload_url: str = Field(..., description="Short-lived pre-signed PUT URL to upload binary slip image to GCS directly")
    storage_path: str = Field(..., description="Storage object path in GCS (e.g. 'slips/{user_id}/{filename}.jpg')")
    public_url: str = Field(..., description="Permanent storage path / URL for database persistence")


class RevenueCatEventPayload(BaseModel):
    """Normalized RevenueCat webhook event payload."""

    id: str = Field(..., description="Unique event identifier from RevenueCat used for idempotency")
    type: str = Field(..., description="Event type: INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION, etc.")
    app_user_id: str = Field(..., description="Application user ID matching our Firebase UID")
    product_id: Optional[str] = None
    period_type: Optional[str] = None
    purchased_at_ms: Optional[int] = None
    expiration_at_ms: Optional[int] = None
    store: Optional[str] = "PLAY_STORE"
    environment: Optional[str] = "PRODUCTION"
    entitlement_ids: Optional[List[str]] = None
    transaction_id: Optional[str] = None
    original_transaction_id: Optional[str] = None


class RevenueCatWebhookPayload(BaseModel):
    """Outer wrapper for RevenueCat webhook posts."""

    api_version: Optional[str] = "1.0"
    event: RevenueCatEventPayload


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


class CurrentSubscriptionStatusResponse(BaseModel):
    """Detailed access status returned to the mobile app for paywall gating and expiry countdown."""

    is_premium: bool
    plan_id: Optional[str] = None
    status: Optional[str] = None
    provider: Optional[str] = None
    expires_at: Optional[datetime] = None
    days_remaining: Optional[int] = None
    active_subscription: Optional[UserSubscriptionResponse] = None
