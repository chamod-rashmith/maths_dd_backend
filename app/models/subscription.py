"""
SQLAlchemy 2.0 ORM models for Subscriptions, Billing, Plans, and Bank Slips.
මෙම මොඩියුලය මඟින් සාමාජිකත්ව (Subscriptions), ගෙවීම් (Payments), සහ බැංකු රිසිට්පත් අනුමත කිරීම් (Bank Slip Approval)
සම්බන්ධ සියලුම දත්ත ව්‍යුහයන් පූර්ණ සාමාන්‍යකරණයෙන් (3NF/BCNF) කළමනාකරණය කරයි.

Architecture Highlights:
1. Multi-Provider Support:
   - Automated Store In-App Purchases (RevenueCat, Google Play, Apple App Store).
   - Direct Sri Lankan Bank CDM / Transfer Slips with strict Admin Approval verification.
   - Manual Admin promotional grants.
2. Minor-Unit Currency Integrity:
   - All monetary amounts are stored in minor units (`amount_minor` as BIGINT cents / ශත, e.g. 250000 = Rs. 2,500.00).
   - Prevents floating-point rounding errors and financial discrepancies.
3. Strict Access Gating:
   - Bank slips are created with `PENDING_APPROVAL` status.
   - `is_premium` strictly evaluates to `False` until a human admin verifies the deposit and marks it `APPROVED`.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class SubscriptionPlan(Base):
    """
    ශිෂ්‍යයන් සඳහා පවතින සාමාජිකත්ව පැකේජ (Subscription Plans).
    උදාහරණ: මාසික (Monthly), වාර්ෂික (Annual), සම්පූර්ණ ජීවිත කාලීන (Lifetime).
    """

    __tablename__ = "subscription_plans"

    # UUID Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="පැකේජයේ අනන්‍ය හඳුනාගැනීමේ අංකය (UUID)",
    )

    # Unique human-readable plan identifier code (e.g. COMBINED_PRO_MONTHLY)
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="පැකේජ කේතය (e.g. COMBINED_PRO_MONTHLY, COMBINED_PRO_ANNUAL)",
    )

    # Sinhala localized plan title for Sri Lankan A/L students
    name_si: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="පැකේජයේ සිංහල නම (e.g. 'සංයුක්ත ගණිතය මාසික සාමාජිකත්වය')",
    )

    # English title (optional)
    name_en: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="පැකේජයේ ඉංග්‍රීසි නම (e.g. 'Combined Maths Pro Monthly')",
    )

    # Detailed description in Sinhala
    description_si: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="පැකේජයේ විස්තරය (Sinhala Description)",
    )

    # Billing frequency: MONTH, YEAR, LIFETIME, CUSTOM
    interval: Mapped[str] = mapped_column(
        String(32),
        default="MONTH",
        server_default=text("'MONTH'"),
        nullable=False,
        comment="ගෙවීම් කාල සීමාව (MONTH, YEAR, LIFETIME, CUSTOM)",
    )

    # Duration in calendar days (None denotes Lifetime permanent access)
    duration_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="වලංගු දින ගණන (30, 365, හෝ Lifetime සඳහා None)",
    )

    # Active flag to control public plan visibility on paywalls
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        index=True,
        comment="පැකේජය සිසුන්ට මිලදී ගැනීමට සක්‍රියද යන්න",
    )

    # Ordering index for display on mobile UI
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="තිරයේ පෙන්වන අනුපිළිවෙල (Display Order)",
    )

    # List of perks or features formatted in Sinhala (JSON or newline-separated)
    features_si: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="පැකේජයට අදාළ පහසුකම් ලැයිස්තුව (Sinhala Features / Perks)",
    )

    # Audit Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    # Relationships
    prices: Mapped[List["PlanPrice"]] = relationship(
        "PlanPrice",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="desc(PlanPrice.created_at)",
        lazy="selectin",
    )

    subscriptions: Mapped[List["UserSubscription"]] = relationship(
        "UserSubscription",
        back_populates="subscription_plan",
    )

    def __repr__(self) -> str:
        return f"<SubscriptionPlan(code='{self.code}', name_si='{self.name_si}', interval='{self.interval}')>"


class PlanPrice(Base):
    """
    පැකේජ සඳහා මිල නියම කිරීම් (Plan Pricing with Minor-Unit Precision).
    මෙහි මිල ශත (cents / minor units) වලින් ගබඩා වන අතර, float භාවිත නොකරයි.
    උදාහරණයක් ලෙස රුපියල් 2,500.00 යනු 250000 ශත වේ.
    """

    __tablename__ = "plan_prices"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="මිල වාර්තාවේ අනන්‍ය හැඳුනුම් අංකය (UUID)",
    )

    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="අදාළ පැකේජයේ හැඳුනුම් අංකය (FK to subscription_plans)",
    )

    # ISO 4217 Currency Code (Standard 'LKR' for Sri Lankan Rupee)
    currency: Mapped[str] = mapped_column(
        String(3),
        default="LKR",
        server_default=text("'LKR'"),
        nullable=False,
        comment="මුදල් ඒකකය (LKR, USD)",
    )

    # Price stored in minor units (Cents / ශත) to prevent float inaccuracies
    amount_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="මිල ශත වලින් (Minor Units / Cents - NEVER FLOAT e.g. 250000 = Rs. 2,500.00)",
    )

    # Pricing validity dates (supports promotional pricing periods)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        index=True,
        comment="මෙම මිල සක්‍රියද යන්න",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="මිලෙහි වලංගු කාලය අවසන් වන දිනය (ප්‍රවර්ධන මිල සඳහා)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    # Relationships
    plan: Mapped["SubscriptionPlan"] = relationship(
        "SubscriptionPlan",
        back_populates="prices",
    )

    @property
    def amount_lkr(self) -> float:
        """Convert minor units (cents) to rupees for display purposes."""
        return self.amount_minor / 100.0

    def __repr__(self) -> str:
        return f"<PlanPrice(plan_id='{self.plan_id}', currency='{self.currency}', amount_minor={self.amount_minor})>"


class UserSubscription(Base):
    """
    ශිෂ්‍යයෙකුගේ සක්‍රිය හෝ පෙර සාමාජිකත්ව වාර්තාව (User Subscription Entitlement).
    RevenueCat වෙළඳසැල් ගෙවීම් හෝ බැංකු තැන්පතු රිසිට්පත් හරහා ලබාගත් අයිතිවාසිකම් කළමනාකරණය කරයි.
    """

    __tablename__ = "user_subscriptions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="සාමාජිකත්ව වාර්තාවේ හැඳුනුම් අංකය (UUID)",
    )
    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ශිෂ්‍යයාගේ Firebase UID",
    )
    plan_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="පැකේජ කේතය හෝ ID (e.g. COMBINED_PRO_MONTHLY)",
    )
    subscription_plan_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="සාමාජිකත්ව පැකේජයේ විදේශ යතුර (FK to subscription_plans.id)",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        server_default=text("'ACTIVE'"),
        nullable=False,
        index=True,
        comment="තත්වය: ACTIVE, PENDING_APPROVAL, REJECTED, EXPIRED, CANCELLED, GRACE_PERIOD",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="නාලිකාව: REVENUECAT, PLAY_STORE, APP_STORE, BANK_TRANSFER, MANUAL_ADMIN",
    )

    # RevenueCat / Store Metadata
    original_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Google Play හෝ App Store මුල් ගනුදෙනු අංකය",
    )
    latest_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="නවතම ගනුදෙනු අංකය",
    )
    store_entitlement_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default="pro_access",
        comment="RevenueCat Entitlement ID (e.g. pro_access)",
    )

    # Bank Deposit / Slip Upload Metadata (Preserved for backward-compatibility)
    amount_lkr: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="ගෙවූ මුදල (රුපියල් වලින් - Legacy column)",
    )
    slip_image_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="රිසිට්පත් ඡායාරූපයේ URL එක (Cloud Storage)",
    )
    reference_note: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="තැන්පත්කරු දැමූ සටහන හෝ බැංකු ශාඛාව",
    )
    admin_notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="පරිපාලකගේ (Admin) සටහන හෝ ප්‍රතික්ෂේප කළ හේතුව",
    )
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="SET NULL"),
        nullable=True,
        comment="අනුමත කළ පරිපාලකගේ UID",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="අනුමත කළ දිනය සහ වේලාව",
    )

    # Lifecycle Timestamps
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="සාමාජිකත්වය ආරම්භ වන දිනය සහ වේලාව",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="සාමාජිකත්වය අවසන් වන දිනය (Lifetime සඳහා None)",
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="අවලංගු කළ දිනය සහ වේලාව",
    )
    is_auto_renew: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="ස්වයංක්‍රීයව අලුත් වේද යන්න",
    )

    # Audit Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="subscriptions",
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by],
    )
    subscription_plan: Mapped[Optional["SubscriptionPlan"]] = relationship(
        "SubscriptionPlan",
        foreign_keys=[subscription_plan_id],
        back_populates="subscriptions",
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="desc(Payment.created_at)",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "idx_user_subs_active_lookup",
            "user_id",
            "status",
            "expires_at",
        ),
        Index(
            "idx_active_subs_partial",
            "user_id",
            postgresql_where=text("status IN ('ACTIVE', 'GRACE_PERIOD')"),
        ),
    )

    def is_currently_active(self) -> bool:
        """
        සාමාජිකත්වය මේ මොහොතේ වලංගු සහ සක්‍රියදැයි පරීක්ෂා කිරීම.
        PENDING_APPROVAL තත්වයේ ඇති විට කිසිදු ප්‍රවේශයක් (premium access) හිමි නොවේ.
        """
        if self.status not in ("ACTIVE", "GRACE_PERIOD"):
            return False
        if self.expires_at is None:
            return True  # Lifetime permanent access
        exp = (
            self.expires_at.replace(tzinfo=timezone.utc)
            if self.expires_at.tzinfo is None
            else self.expires_at
        )
        return exp > datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (
            f"<UserSubscription(id='{self.id}', user_id='{self.user_id}', "
            f"plan='{self.plan_id}', status='{self.status}', provider='{self.provider}')>"
        )


class Payment(Base):
    """
    ගෙවීම් වාර්තාව (Payment Entity - 3NF Normalized).
    සාමාජිකත්වයක් සඳහා සිදුකළ එක් එක් ගෙවීම් ගනුදෙනුව වෙනම වාර්තාවක් ලෙස මෙහි සටහන් වේ.
    """

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="ගෙවීමේ අනන්‍ය හැඳුනුම් අංකය (UUID)",
    )

    subscription_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="අදාළ සාමාජිකත්ව වාර්තාව (FK to user_subscriptions.id)",
    )

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ගෙවීම සිදුකළ ශිෂ්‍යයාගේ UID",
    )

    # Payment method: BANK_TRANSFER, PLAY_STORE, APP_STORE, MANUAL_ADMIN
    method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="ගෙවීම් ක්‍රමය (BANK_TRANSFER, PLAY_STORE, APP_STORE, MANUAL_ADMIN)",
    )

    # Payment status: PENDING, COMPLETED, FAILED, REFUNDED
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        server_default=text("'PENDING'"),
        nullable=False,
        index=True,
        comment="ගෙවීමේ තත්වය (PENDING, COMPLETED, FAILED, REFUNDED)",
    )

    # Currency code
    currency: Mapped[str] = mapped_column(
        String(3),
        default="LKR",
        server_default=text("'LKR'"),
        nullable=False,
        comment="මුදල් ඒකකය (LKR, USD)",
    )

    # Amount in minor units (Cents / ශත)
    amount_minor: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="ගෙවූ මුදල ශත වලින් (Minor Units / Cents - NEVER FLOAT e.g. 250000 = Rs. 2,500.00)",
    )

    # External transaction identifier (e.g. Google Play order ID, bank deposit ref)
    external_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="බාහිර ගනුදෙනු අංකය (Bank Ref හෝ Store Order ID)",
    )

    # When the payment was settled
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="මුදල් ගෙවූ දිනය සහ වේලාව",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    # Relationships
    subscription: Mapped["UserSubscription"] = relationship(
        "UserSubscription",
        back_populates="payments",
    )

    bank_slip: Mapped[Optional["BankTransferSlip"]] = relationship(
        "BankTransferSlip",
        back_populates="payment",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def amount_lkr(self) -> float:
        """Convert minor units (cents) to rupees for display."""
        return self.amount_minor / 100.0

    def __repr__(self) -> str:
        return (
            f"<Payment(id='{self.id}', sub='{self.subscription_id}', "
            f"amount_minor={self.amount_minor}, status='{self.status}')>"
        )


class BankTransferSlip(Base):
    """
    බැංකු රිසිට්පත් සාක්ෂි විස්තර (Bank Transfer Slip Evidence - 1-to-1 with Payment).
    ශිෂ්‍යයා තැන්පත් කළ රිසිට්පත, බැංකුව, සහ පරිපාලකගේ අනුමැතිය මෙහි ගබඩා වේ.
    """

    __tablename__ = "bank_transfer_slips"

    # Payment ID serves as both Primary Key and Foreign Key (1-to-1 relationship with Payment)
    payment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("payments.id", ondelete="CASCADE"),
        primary_key=True,
        comment="අදාළ ගෙවීමේ හැඳුනුම් අංකය (PK & FK to payments.id)",
    )

    # Storage URL of the bank deposit slip image in Google Cloud Storage
    slip_image_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="තැන්පතු රිසිට්පත් ඡායාරූපයේ URL එක (Cloud Storage)",
    )

    # Bank Name (e.g. Bank of Ceylon, Commercial Bank, Sampath Bank, People's Bank)
    bank_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="තැන්පත් කළ බැංකුව (e.g. BOC, Commercial Bank, Sampath Bank)",
    )

    # Bank CDM machine or branch transaction reference number
    deposit_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="බැංකු රිසිට්පත් අංකය හෝ CDM යන්ත්‍ර යොමු අංකය",
    )

    # Depositor note or additional comments submitted by student
    depositor_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="ශිෂ්‍යයා ඇතුළත් කළ අමතර සටහන් (Depositor remarks)",
    )

    # Slip Review Status: PENDING, APPROVED, REJECTED
    review_status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        server_default=text("'PENDING'"),
        nullable=False,
        index=True,
        comment="අනුමත කිරීමේ තත්වය (PENDING, APPROVED, REJECTED)",
    )

    # Admin user who reviewed this slip
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="SET NULL"),
        nullable=True,
        comment="පරීක්ෂා කළ පරිපාලකගේ UID (FK to users.uid)",
    )

    # When the admin approved or rejected this slip
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="පරිපාලක පරීක්ෂා කළ දිනය සහ වේලාව",
    )

    # Feedback or reason if rejected (or remarks if approved)
    admin_feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="ප්‍රතික්ෂේප කළ හේතුව හෝ පරිපාලකගේ විශේෂ සටහන (Admin feedback)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    # Relationships
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="bank_slip",
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by],
    )

    def __repr__(self) -> str:
        return f"<BankTransferSlip(payment_id='{self.payment_id}', review_status='{self.review_status}')>"


class ProcessedWebhookEvent(Base):
    """
    RevenueCat සහ Store Webhooks අනුපිටපත් වැළැක්වීම සඳහා වන ලේඛනය (Idempotency deduplication).
    එකම webhook ඉවෙන්ට් එක දෙවරක් සැකසීම (duplicate processing) සම්පූර්ණයෙන්ම වළක්වයි.
    """

    __tablename__ = "processed_webhook_events"

    event_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        comment="RevenueCat අනන්‍ය ඉවෙන්ට් අංකය (Unique Webhook Event ID)",
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="ඉවෙන්ට් වර්ගය (e.g. INITIAL_PURCHASE, RENEWAL, CANCELLATION)",
    )
    app_user_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="ශිෂ්‍යයාගේ UID",
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ProcessedWebhookEvent(event_id='{self.event_id}', type='{self.event_type}')>"
