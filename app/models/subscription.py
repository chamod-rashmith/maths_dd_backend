"""
SQLAlchemy 2.0 ORM models for Subscriptions and Billing.
Supports multi-provider lifecycle:
1. RevenueCat / Google Play / App Store (Automated In-App Purchases)
2. Direct Bank Deposit Slip Upload + Admin Approval Workflow
3. Manual Admin Grants & Promotional Access
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        server_default=text("'ACTIVE'"),
        nullable=False,
        index=True,
    )  # ACTIVE, PENDING_APPROVAL, REJECTED, EXPIRED, CANCELLED, TRIAL, GRACE_PERIOD
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # REVENUECAT, PLAY_STORE, APP_STORE, BANK_TRANSFER, MANUAL_ADMIN

    # RevenueCat / Store Metadata
    original_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    latest_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    store_entitlement_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default="pro_access",
    )

    # Bank Deposit / Slip Upload Metadata
    amount_lkr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    slip_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    admin_notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("users.uid", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Lifecycle Timestamps
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,  # None means Lifetime Access
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_auto_renew: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
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

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="subscriptions",
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by],
    )

    __table_args__ = (
        Index(
            "idx_user_subs_active_lookup",
            "user_id",
            "status",
            "expires_at",
        ),
    )

    def is_currently_active(self) -> bool:
        """Check if this subscription grant is currently valid and active."""
        if self.status not in ("ACTIVE", "GRACE_PERIOD"):
            return False
        if self.expires_at is None:
            return True  # Lifetime access
        return self.expires_at > datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (
            f"<UserSubscription(id='{self.id}', user_id='{self.user_id}', "
            f"plan='{self.plan_id}', status='{self.status}', provider='{self.provider}')>"
        )


class ProcessedWebhookEvent(Base):
    """Stores deduplication keys for RevenueCat / Store webhooks to guarantee idempotency."""

    __tablename__ = "processed_webhook_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    app_user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ProcessedWebhookEvent(event_id='{self.event_id}', type='{self.event_type}')>"
