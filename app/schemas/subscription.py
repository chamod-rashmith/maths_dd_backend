"""
Pydantic DTO schemas for Subscriptions, Plans, Billing, and Bank Slip Operations.
මෙම මොඩියුලය මඟින් සාමාජිකත්ව (Subscriptions), මිල ගණන් (Plans & Pricing), සහ බැංකු රිසිට්පත්
සම්බන්ධ සියලුම Data Transfer Objects (DTO) නිරවද්‍යව නිර්වචනය කරයි.

Client Security & Privacy Standards:
1. Strip Internal Timestamps:
   - Does NOT leak internal database audit timestamps (`created_at`, `updated_at`, `deleted_at`) to the client.
2. Minor-Unit Monetary Precision:
   - Financial transactions store `amount_minor` (cents / ශත as BIGINT) to eliminate IEEE-754 float rounding issues.
   - Provides helper `amount_lkr` for clean mobile UI rendering.
3. Strict Access Gating:
   - Submissions in `PENDING_APPROVAL` status ensure `is_premium` remains `False` until human verification.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class SubscriptionPlanCode(str, Enum):
    """Available educational subscription plans."""

    COMBINED_PRO_MONTHLY = "COMBINED_PRO_MONTHLY"
    COMBINED_PRO_ANNUAL = "COMBINED_PRO_ANNUAL"
    PURE_MATHS_TERM = "PURE_MATHS_TERM"
    APPLIED_MATHS_TERM = "APPLIED_MATHS_TERM"
    LIFETIME = "LIFETIME"
    ADMIN_OVERRIDE = "ADMIN_OVERRIDE"


# Legacy alias for backward compatibility
SubscriptionPlan = SubscriptionPlanCode


class SubscriptionStatus(str, Enum):
    """Lifecycle statuses for user subscriptions."""

    NONE = "NONE"
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


class PlanInterval(str, Enum):
    """Billing cycle interval for plans."""

    MONTH = "MONTH"
    YEAR = "YEAR"
    TERM = "TERM"
    LIFETIME = "LIFETIME"


class PaymentStatus(str, Enum):
    """Transaction status of a payment record."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class SlipReviewStatus(str, Enum):
    """Human admin review status for a bank deposit slip."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# =============================================================================
# 1. Plans & Pricing DTOs (Client Catalog)
# =============================================================================

class PlanPriceResponse(BaseModel):
    """
    පැකේජයක මිල විස්තරය (Plan Price for Paywall Display).
    ශත (cents) සහ රුපියල් (LKR) යන දෙකෙන්ම අගය සපයයි.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="මිල වාර්තාවේ ID")
    currency: str = Field(default="LKR", description="මුදල් ඒකකය (LKR)")
    amount_minor: int = Field(..., description="මිල ශත වලින් (Minor Units / Cents, e.g. 250000 = Rs. 2,500.00)")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def amount_lkr(self) -> float:
        """රුපියල් වලින් මිල (Amount in Rupees for Mobile Display)."""
        return self.amount_minor / 100.0


class SubscriptionPlanResponse(BaseModel):
    """
    ශිෂ්‍යයන්ට පෙන්වන සාමාජිකත්ව පැකේජ විස්තරය (Public Subscription Plan DTO).
    Mobile Paywall එකෙහි පෙන්වීම සඳහා අවශ්‍ය දත්ත පමණක් අඩංගු වන අතර, අභ්‍යන්තර audit timestamps ඉවත් කර ඇත.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="පැකේජයේ හැඳුනුම් අංකය (UUID)")
    code: SubscriptionPlanCode | str = Field(..., description="පැකේජ කේතය (e.g. COMBINED_PRO_MONTHLY, COMBINED_PRO_ANNUAL)")
    name_si: str = Field(..., description="සිංහල නම (e.g. 'සංයුක්ත ගණිතය මාසික සාමාජිකත්වය')")
    name_en: str | None = Field(None, description="ඉංග්‍රීසි නම (Optional English Title)")
    description_si: str | None = Field(None, description="සිංහල විස්තරය (Sinhala Description)")
    interval: PlanInterval | str = Field(default=PlanInterval.MONTH, description="ගෙවීම් වාර ගණන (MONTH, YEAR, LIFETIME)")
    duration_days: int | None = Field(None, description="වලංගු දින ගණන (30, 365, හෝ Lifetime සඳහා None)")
    display_order: int = Field(default=0, description="තිරයේ පෙන්වන අනුපිළිවෙල")
    features_si: str | None = Field(None, description="පැකේජයේ අඩංගු පහසුකම් (Features / Perks)")
    prices: list[PlanPriceResponse] = Field(default_factory=list, description="පැකේජයේ සක්‍රිය මිල ගණන්")


# =============================================================================
# 2. Bank Slip & Payment DTOs
# =============================================================================

class BankSlipUploadRequest(BaseModel):
    """
    ශිෂ්‍යයා විසින් බැංකු තැන්පතු රිසිට්පතක් ඉදිරිපත් කිරීමේදී එවන Payload එක.
    Supports both legacy `amount_lkr` and modern `amount_minor` (cents).
    """

    plan_id: str = Field(..., description="ඉල්ලුම් කරන පැකේජ කේතය හෝ ID (e.g. COMBINED_PRO_MONTHLY)")
    slip_image_url: str = Field(..., description="Cloud Storage හි ගබඩා කළ රිසිට්පත් ඡායාරූපයේ URL එක")
    amount_lkr: float | None = Field(None, gt=0, description="තැන්පත් කළ මුදල රුපියල් වලින් (e.g. 2500.0)")
    amount_minor: int | None = Field(None, gt=0, description="තැන්පත් කළ මුදල ශත වලින් (e.g. 250000 = Rs. 2,500.00)")
    bank_name: str | None = Field(None, max_length=100, description="තැන්පත් කළ බැංකුව (e.g. 'BOC', 'Commercial Bank')")
    deposit_reference: str | None = Field(None, max_length=100, description="රිසිට්පත් අංකය හෝ CDM reference අංකය")
    reference_note: str | None = Field(
        None, max_length=500, description="තැන්පත්කරුගේ නම, දුරකථන අංකය හෝ අමතර සටහන"
    )

    @model_validator(mode="after")
    def validate_and_normalize_amount(self) -> "BankSlipUploadRequest":
        """Validate and harmonize amount_minor and amount_lkr."""
        if self.amount_minor is None and self.amount_lkr is None:
            raise ValueError("Either amount_minor (cents) or amount_lkr (rupees) must be provided.")

        if self.amount_minor is None and self.amount_lkr is not None:
            # Convert rupees to integer minor units (cents)
            self.amount_minor = int(round(self.amount_lkr * 100))
        elif self.amount_lkr is None and self.amount_minor is not None:
            # Derive rupees from minor units
            self.amount_lkr = self.amount_minor / 100.0

        return self


class BankSlipDetailsResponse(BaseModel):
    """බැංකු රිසිට්පත් පරීක්ෂණ විස්තරය (Bank Slip Audit Details)."""

    model_config = ConfigDict(from_attributes=True)

    payment_id: str = Field(..., description="අදාළ ගෙවීමේ ID")
    slip_image_url: str = Field(..., description="රිසිට්පත් ඡායාරූපයේ URL")
    bank_name: str | None = Field(None, description="තැන්පත් කළ බැංකුව")
    deposit_reference: str | None = Field(None, description="රිසිට්පත් අංකය")
    depositor_note: str | None = Field(None, description="ශිෂ්‍යයාගේ සටහන")
    review_status: SlipReviewStatus | str = Field(..., description="පරීක්ෂා කිරීමේ තත්වය: PENDING, APPROVED, REJECTED")
    admin_feedback: str | None = Field(None, description="පරිපාලකගේ සටහන හෝ ප්‍රතික්ෂේප කළ හේතුව")
    reviewed_at: datetime | None = Field(None, description="පරිපාලක අනුමත කළ දිනය")


class PaymentResponse(BaseModel):
    """ගෙවීම් ගනුදෙනු විස්තරය (Payment Transaction DTO)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="ගෙවීමේ හැඳුනුම් අංකය")
    subscription_id: str = Field(..., description="අදාළ සාමාජිකත්වයේ ID")
    method: SubscriptionProvider | str = Field(..., description="ගෙවීම් ක්‍රමය (BANK_TRANSFER, PLAY_STORE, etc.)")
    status: PaymentStatus | str = Field(..., description="ගෙවීමේ තත්වය (PENDING, COMPLETED, FAILED)")
    currency: str = Field(default="LKR", description="මුදල් ඒකකය")
    amount_minor: int = Field(..., description="ගෙවූ මුදල ශත වලින්")
    paid_at: datetime | None = Field(None, description="ගෙවූ දිනය")
    bank_slip: BankSlipDetailsResponse | None = Field(None, description="බැංකු රිසිට්පත් විස්තර")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def amount_lkr(self) -> float:
        """රුපියල් වලින් මුදල."""
        return self.amount_minor / 100.0


# =============================================================================
# 3. Admin Review & Lifecycle DTOs
# =============================================================================

class AdminApprovalRequest(BaseModel):
    """Payload submitted by an Admin to approve a pending bank slip subscription."""

    duration_days: int = Field(30, ge=1, le=730, description="Duration in days to grant access for this payment")
    admin_notes: str | None = Field(None, max_length=500, description="Optional verification note by admin")


class AdminRejectionRequest(BaseModel):
    """Payload submitted by an Admin to reject an invalid or fraudulent bank slip."""

    rejection_reason: str = Field(..., min_length=3, max_length=500, description="Reason displayed to the student")


class SignedUploadUrlResponse(BaseModel):
    """Pre-signed GCS upload URL response for direct client-to-cloud storage uploads."""

    upload_url: str = Field(..., description="Short-lived pre-signed PUT URL to upload binary slip image to GCS directly")
    storage_path: str = Field(..., description="Storage object path in GCS (e.g. 'slips/{user_id}/{filename}.jpg')")
    public_url: str = Field(..., description="Permanent storage path / URL for database persistence")


# =============================================================================
# 4. RevenueCat Store Webhook DTOs
# =============================================================================

class RevenueCatEventPayload(BaseModel):
    """Normalized RevenueCat webhook event payload."""

    id: str = Field(..., description="Unique event identifier from RevenueCat used for idempotency")
    type: str = Field(..., description="Event type: INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION, etc.")
    app_user_id: str = Field(..., description="Application user ID matching our Firebase UID")
    product_id: str | None = None
    period_type: str | None = None
    purchased_at_ms: int | None = None
    expiration_at_ms: int | None = None
    store: str | None = "PLAY_STORE"
    environment: str | None = "PRODUCTION"
    entitlement_ids: list[str] | None = None
    transaction_id: str | None = None
    original_transaction_id: str | None = None


class RevenueCatWebhookPayload(BaseModel):
    """Outer wrapper for RevenueCat webhook posts."""

    api_version: str | None = "1.0"
    event: RevenueCatEventPayload


# =============================================================================
# 5. User Subscription Responses (Client & Paywall Status)
# =============================================================================

class UserSubscriptionResponse(BaseModel):
    """
    Lightweight client representation of a subscription record.
    Strips internal database audit timestamps (`created_at`, `updated_at`).
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="සාමාජිකත්වයේ ID")
    plan_id: SubscriptionPlanCode | str = Field(..., description="පැකේජ කේතය හෝ ID")
    status: SubscriptionStatus | str = Field(..., description="තත්වය (ACTIVE, PENDING_APPROVAL, REJECTED, EXPIRED)")
    provider: SubscriptionProvider | str = Field(..., description="නාලිකාව (BANK_TRANSFER, REVENUECAT, etc.)")
    starts_at: datetime = Field(..., description="ආරම්භක දිනය")
    expires_at: datetime | None = Field(None, description="අවසන් වන දිනය (Lifetime සඳහා None)")
    amount_lkr: float | None = Field(None, description="ගෙවූ මුදල (රුපියල් වලින්)")
    amount_minor: int | None = Field(None, description="ගෙවූ මුදල (ශත වලින්)")
    slip_image_url: str | None = Field(None, description="රිසිට්පතේ URL එක")
    reference_note: str | None = Field(None, description="තැන්පත්කරුගේ සටහන")
    admin_notes: str | None = Field(None, description="පරිපාලකගේ සටහන")
    approved_at: datetime | None = Field(None, description="අනුමත කළ දිනය")
    payments: list[PaymentResponse] | None = Field(default=None, description="අදාළ ගෙවීම් වාර්තා (Payments)")


class CurrentSubscriptionStatusResponse(BaseModel):
    """
    Detailed access status returned to the mobile app for paywall gating and countdown.
    Strictly gates access: `is_premium` is FALSE while status is `PENDING_APPROVAL`.
    """

    is_premium: bool = Field(..., description="ශිෂ්‍යයාට මේ මොහොතේ Premium අයිතිය තිබේද යන්න")
    plan_id: SubscriptionPlanCode | str | None = Field(None, description="සක්‍රිය පැකේජ කේතය")
    status: SubscriptionStatus | str | None = Field(None, description="සාමාජිකත්ව තත්වය")
    provider: SubscriptionProvider | str | None = Field(None, description="ගෙවීම් නාලිකාව")
    expires_at: datetime | None = Field(None, description="කල් ඉකුත් වන දිනය")
    days_remaining: int | None = Field(None, description="ඉතිරිව ඇති දින ගණන")
    active_subscription: UserSubscriptionResponse | None = Field(None, description="සක්‍රිය සාමාජිකත්ව විස්තරය")
