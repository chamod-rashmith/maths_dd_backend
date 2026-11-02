"""
Repository for Subscription and Billing operations using modern SQLAlchemy 2.0.
Handles:
1. Active entitlement lookups for users.
2. Direct Bank Slip upload & Admin approval/rejection workflows.
3. RevenueCat Webhook idempotency and state synchronization.
4. Maintenance routine for expiring stale subscriptions.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.exceptions import DatabaseOperationError
from app.models.subscription import ProcessedWebhookEvent, UserSubscription


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """Fetch the current active and unexpired subscription for a user."""
        try:
            now = datetime.now(timezone.utc)
            stmt = (
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status.in_(["ACTIVE", "GRACE_PERIOD"]),
                    (UserSubscription.expires_at.is_(None)) | (UserSubscription.expires_at > now),
                )
                .order_by(desc(UserSubscription.created_at))
                .limit(1)
            )
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as exc:
            raise DatabaseOperationError(f"Error fetching active subscription: {exc}") from exc

    async def is_user_premium(self, user_id: str) -> bool:
        """Lightweight check whether user currently has active premium access."""
        sub = await self.get_active_subscription(user_id)
        return sub is not None

    async def get_user_subscriptions(self, user_id: str) -> List[UserSubscription]:
        """Fetch all subscription history records for a user ordered newest first."""
        try:
            stmt = (
                select(UserSubscription)
                .where(UserSubscription.user_id == user_id)
                .order_by(desc(UserSubscription.created_at))
            )
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseOperationError(f"Error fetching user subscriptions: {exc}") from exc

    async def create_bank_slip_subscription(
        self,
        user_id: str,
        plan_id: str,
        slip_image_url: str,
        amount_lkr: float,
        reference_note: Optional[str] = None,
    ) -> UserSubscription:
        """Create a new subscription record in PENDING_APPROVAL status from a bank slip upload."""
        try:
            now = datetime.now(timezone.utc)
            sub = UserSubscription(
                user_id=user_id,
                plan_id=plan_id,
                status="PENDING_APPROVAL",
                provider="BANK_TRANSFER",
                slip_image_url=slip_image_url,
                amount_lkr=amount_lkr,
                reference_note=reference_note,
                starts_at=now,
                expires_at=None,
                is_auto_renew=False,
            )
            self._session.add(sub)
            await self._session.flush()
            return sub
        except Exception as exc:
            raise DatabaseOperationError(f"Error creating bank slip subscription: {exc}") from exc

    async def get_pending_approvals(self) -> List[UserSubscription]:
        """Retrieve all pending bank slip submissions for admin review."""
        try:
            stmt = (
                select(UserSubscription)
                .options(selectinload(UserSubscription.user))
                .where(UserSubscription.status == "PENDING_APPROVAL")
                .order_by(UserSubscription.created_at.asc())
            )
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseOperationError(f"Error fetching pending subscriptions: {exc}") from exc

    async def approve_subscription(
        self,
        subscription_id: str,
        admin_uid: str,
        duration_days: int = 30,
        admin_notes: Optional[str] = None,
    ) -> Optional[UserSubscription]:
        """Admin approves a pending bank slip, activating access for duration_days."""
        try:
            stmt = select(UserSubscription).where(UserSubscription.id == subscription_id)
            result = await self._session.execute(stmt)
            sub = result.scalar_one_or_none()
            if not sub:
                return None

            now = datetime.now(timezone.utc)
            sub.status = "ACTIVE"
            sub.approved_by = admin_uid
            sub.approved_at = now
            sub.admin_notes = admin_notes
            sub.starts_at = now
            sub.expires_at = now + timedelta(days=duration_days)

            await self._session.flush()
            return sub
        except Exception as exc:
            raise DatabaseOperationError(f"Error approving subscription: {exc}") from exc

    async def reject_subscription(
        self,
        subscription_id: str,
        admin_uid: str,
        rejection_reason: str,
    ) -> Optional[UserSubscription]:
        """Admin rejects an invalid or fraudulent bank slip submission."""
        try:
            stmt = select(UserSubscription).where(UserSubscription.id == subscription_id)
            result = await self._session.execute(stmt)
            sub = result.scalar_one_or_none()
            if not sub:
                return None

            now = datetime.now(timezone.utc)
            sub.status = "REJECTED"
            sub.approved_by = admin_uid
            sub.approved_at = now
            sub.admin_notes = rejection_reason

            await self._session.flush()
            return sub
        except Exception as exc:
            raise DatabaseOperationError(f"Error rejecting subscription: {exc}") from exc

    async def sync_revenuecat_event(
        self,
        app_user_id: str,
        event_type: str,
        product_id: str,
        entitlement_id: str,
        store: str,
        transaction_id: str,
        original_transaction_id: str,
        starts_at: datetime,
        expires_at: Optional[datetime],
        is_auto_renew: bool = True,
    ) -> UserSubscription:
        """
        Synchronize an incoming RevenueCat webhook event with industry-standard state mapping.

        Event Handling Rules (from RevenueCat Handbook):
        - INITIAL_PURCHASE / RENEWAL / UNCANCELLATION:
          Grants or extends active entitlement. Status becomes ACTIVE.
        - CANCELLATION:
          Intent signal indicating auto-renew was disabled. Does NOT revoke access immediately.
          Access remains ACTIVE until expires_at, while auto_renew is set to False.
        - EXPIRATION:
          Access actually ended. Status becomes EXPIRED.
        - BILLING_ISSUE:
          Temporary payment failure (user may be in store grace period). Status is GRACE_PERIOD.
        - PRODUCT_CHANGE:
          Plan upgraded or downgraded.
        """
        try:
            now = datetime.now(timezone.utc)

            # Determine subscription status based on RevenueCat event type and expiry
            status = "ACTIVE"
            auto_renew = is_auto_renew
            cancelled_at = None

            if event_type in ("INITIAL_PURCHASE", "RENEWAL", "UNCANCELLATION"):
                status = "ACTIVE"
                auto_renew = True
            elif event_type == "CANCELLATION":
                auto_renew = False
                cancelled_at = now
                # User retains paid access until expires_at!
                if expires_at and expires_at > now:
                    status = "ACTIVE"
                else:
                    status = "CANCELLED"
            elif event_type == "EXPIRATION":
                status = "EXPIRED"
                auto_renew = False
            elif event_type == "BILLING_ISSUE":
                status = "GRACE_PERIOD"
            elif event_type == "PRODUCT_CHANGE":
                if expires_at and expires_at > now:
                    status = "ACTIVE"
                else:
                    status = "EXPIRED"

            # Check if an existing subscription matches original_transaction_id
            existing_sub = None
            if original_transaction_id:
                stmt = select(UserSubscription).where(
                    UserSubscription.original_transaction_id == original_transaction_id
                )
                result = await self._session.execute(stmt)
                existing_sub = result.scalar_one_or_none()

            # Fallback check by app_user_id and plan_id if original_transaction_id not yet linked
            if not existing_sub:
                stmt_user = (
                    select(UserSubscription)
                    .where(
                        UserSubscription.user_id == app_user_id,
                        UserSubscription.plan_id == product_id,
                    )
                    .order_by(desc(UserSubscription.created_at))
                    .limit(1)
                )
                res_user = await self._session.execute(stmt_user)
                existing_sub = res_user.scalar_one_or_none()

            if existing_sub:
                existing_sub.status = status
                existing_sub.plan_id = product_id
                existing_sub.store_entitlement_id = entitlement_id
                existing_sub.provider = store
                existing_sub.latest_transaction_id = transaction_id
                if original_transaction_id:
                    existing_sub.original_transaction_id = original_transaction_id
                existing_sub.starts_at = starts_at
                existing_sub.expires_at = expires_at
                existing_sub.is_auto_renew = auto_renew
                if cancelled_at:
                    existing_sub.cancelled_at = cancelled_at
                await self._session.flush()
                return existing_sub

            sub = UserSubscription(
                user_id=app_user_id,
                plan_id=product_id,
                store_entitlement_id=entitlement_id,
                status=status,
                provider=store,
                original_transaction_id=original_transaction_id,
                latest_transaction_id=transaction_id,
                starts_at=starts_at,
                expires_at=expires_at,
                is_auto_renew=auto_renew,
                cancelled_at=cancelled_at,
            )
            self._session.add(sub)
            await self._session.flush()
            return sub
        except Exception as exc:
            raise DatabaseOperationError(f"Error synchronizing RevenueCat event: {exc}") from exc

    async def is_webhook_event_processed(self, event_id: str) -> bool:
        """Check whether a RevenueCat webhook event has already been recorded."""
        try:
            stmt = select(ProcessedWebhookEvent).where(ProcessedWebhookEvent.event_id == event_id)
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as exc:
            raise DatabaseOperationError(f"Error checking webhook idempotency: {exc}") from exc

    async def record_webhook_event(self, event_id: str, event_type: str, app_user_id: str) -> None:
        """Mark a webhook event ID as processed."""
        try:
            record = ProcessedWebhookEvent(
                event_id=event_id,
                event_type=event_type,
                app_user_id=app_user_id,
            )
            self._session.add(record)
            await self._session.flush()
        except Exception as exc:
            raise DatabaseOperationError(f"Error recording webhook event: {exc}") from exc

    async def expire_stale_subscriptions(self) -> int:
        """Maintenance worker: marks active subscriptions whose expires_at < now as EXPIRED."""
        try:
            now = datetime.now(timezone.utc)
            stmt = (
                update(UserSubscription)
                .where(
                    UserSubscription.status == "ACTIVE",
                    UserSubscription.expires_at.is_not(None),
                    UserSubscription.expires_at < now,
                )
                .values(status="EXPIRED", updated_at=now)
            )
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount or 0
        except Exception as exc:
            raise DatabaseOperationError(f"Error expiring stale subscriptions: {exc}") from exc
