"""
Repository for Subscription, Billing, Plans, and Bank Slip operations using modern SQLAlchemy 2.0.
මෙම Repository මඟින් ශිෂ්‍ය සාමාජිකත්ව (Subscriptions), ගෙවීම් (Payments), සහ බැංකු රිසිට්පත්
පරීක්ෂා කිරීමේ (Bank Slip Approval/Rejection) සියලුම දත්ත මෙහෙයුම් සුරක්ෂිතව ඉටු කරයි.

Core Architectural Capabilities:
1. Multi-Plan Catalog:
   - Retrieves active plans with associated minor-unit prices (`list_active_plans`).
2. Normalized Bank Slip Workflow:
   - Atomically records `UserSubscription` (PENDING_APPROVAL), `Payment` (PENDING),
     and `BankTransferSlip` (PENDING).
   - Strict verification gate: No premium privileges granted until Admin approves.
3. Admin Approval / Rejection Lifecycle:
   - On approval: Subscription becomes `ACTIVE`, Payment marked `COMPLETED`, Slip marked `APPROVED`.
   - On rejection: Subscription becomes `REJECTED`, Payment marked `FAILED`, Slip marked `REJECTED` with reason.
4. RevenueCat Multi-Store Synchronization:
   - Normalized webhook handling with event deduplication (`ProcessedWebhookEvent`).
5. Maintenance Routine:
   - Automatically expires stale subscriptions whose `expires_at` timestamp has passed.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.exceptions import DatabaseOperationError
from app.models.subscription import (
    BankTransferSlip,
    Payment,
    PlanPrice,
    ProcessedWebhookEvent,
    SubscriptionPlan,
    UserSubscription,
)


class SubscriptionRepository:
    """SQLAlchemy 2.0 Repository for Subscription and Billing Domain."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # =========================================================================
    # 1. Plans & Pricing Queries (පැකේජ සහ මිල විමසුම්)
    # =========================================================================

    async def list_active_plans(self) -> List[SubscriptionPlan]:
        """
        සිසුන් සඳහා විවෘතව පවතින සියලුම සක්‍රිය සාමාජිකත්ව පැකේජ (Subscription Plans) ලබා ගැනීම.
        සෑම පැකේජයකටම අදාළ සක්‍රිය මිල ගණන් (prices) ද සමඟ display_order අනුපිළිවෙලට ලබා දෙයි.
        """
        try:
            stmt = (
                select(SubscriptionPlan)
                .options(selectinload(SubscriptionPlan.prices))
                .where(SubscriptionPlan.is_active.is_(True))
                .order_by(SubscriptionPlan.display_order.asc())
            )
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseOperationError(f"Error fetching active subscription plans: {exc}") from exc

    async def get_plan_by_code(self, plan_code_or_id: str) -> Optional[SubscriptionPlan]:
        """
        පැකේජ කේතය (e.g. COMBINED_PRO_MONTHLY) හෝ UUID මඟින් පැකේජයක් සොයා ගැනීම.
        """
        try:
            stmt = (
                select(SubscriptionPlan)
                .options(selectinload(SubscriptionPlan.prices))
                .where(
                    (SubscriptionPlan.code == plan_code_or_id) | (SubscriptionPlan.id == plan_code_or_id)
                )
            )
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as exc:
            raise DatabaseOperationError(f"Error fetching subscription plan '{plan_code_or_id}': {exc}") from exc

    # =========================================================================
    # 2. Entitlement & Access Checks (අයිතිවාසිකම් පරීක්ෂාව)
    # =========================================================================

    async def get_active_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """
        ශිෂ්‍යයෙකුගේ මේ මොහොතේ වලංගු සහ ක්‍රියාකාරී සාමාජිකත්වය ලබා ගැනීම.
        PENDING_APPROVAL හෝ EXPIRED වාර්තා මෙහිදී ප්‍රතික්ෂේප වන අතර, ACTIVE / GRACE_PERIOD පමණක් ලබා දේ.
        """
        try:
            now = datetime.now(timezone.utc)
            stmt = (
                select(UserSubscription)
                .options(selectinload(UserSubscription.payments))
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
                .options(selectinload(UserSubscription.payments))
                .where(UserSubscription.user_id == user_id)
                .order_by(desc(UserSubscription.created_at))
            )
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseOperationError(f"Error fetching user subscriptions: {exc}") from exc

    # =========================================================================
    # 3. Bank Slip Submission Workflow (බැංකු රිසිට්පත් ඉදිරිපත් කිරීමේ ක්‍රියාවලිය)
    # =========================================================================

    async def create_bank_slip_subscription(
        self,
        user_id: str,
        plan_id: str,
        slip_image_url: str,
        amount_lkr: Optional[float] = None,
        amount_minor: Optional[int] = None,
        bank_name: Optional[str] = None,
        deposit_reference: Optional[str] = None,
        reference_note: Optional[str] = None,
    ) -> UserSubscription:
        """
        ශිෂ්‍යයා තැන්පත් කළ බැංකු රිසිට්පත පද්ධතියට ඇතුළත් කිරීම (Normalized Atomic Creation).
        
        ක්‍රියාත්මක වන පියවර:
        1. මුදල් අගය ශත (minor units) සහ රුපියල් අතර නිරවුල් කිරීම (Minor-Unit Integrity).
        2. අදාළ SubscriptionPlan වාර්තාව සම්බන්ධ කිරීම.
        3. UserSubscription වාර්තාව 'PENDING_APPROVAL' තත්වයෙන් නිර්මාණය කිරීම (ප්‍රවේශය තවම ලබා නොදේ).
        4. Payment වාර්තාවක් 'PENDING' තත්වයෙන් නිර්මාණය කිරීම.
        5. BankTransferSlip වාර්තාවක් සාදා Payment එක සමඟ 1-to-1 සම්බන්ධ කිරීම.
        """
        try:
            now = datetime.now(timezone.utc)

            # 1. Harmonize minor units (cents) and float rupees
            if amount_minor is None and amount_lkr is not None:
                amount_minor = int(round(amount_lkr * 100))
            elif amount_minor is not None and amount_lkr is None:
                amount_lkr = amount_minor / 100.0
            elif amount_minor is None and amount_lkr is None:
                amount_minor = 250000  # Default fallback: 2,500 LKR
                amount_lkr = 2500.0

            # 2. Lookup subscription plan if exists
            plan_obj = await self.get_plan_by_code(plan_id)
            plan_fk_id = plan_obj.id if plan_obj else None

            # 3. Create UserSubscription header (PENDING_APPROVAL)
            sub = UserSubscription(
                user_id=user_id,
                plan_id=plan_id,
                subscription_plan_id=plan_fk_id,
                status="PENDING_APPROVAL",
                provider="BANK_TRANSFER",
                slip_image_url=slip_image_url,
                amount_lkr=amount_lkr,
                reference_note=reference_note or deposit_reference,
                starts_at=now,
                expires_at=None,
                is_auto_renew=False,
            )
            self._session.add(sub)
            await self._session.flush()

            # 4. Create normalized Payment ledger record
            payment = Payment(
                subscription_id=sub.id,
                user_id=user_id,
                method="BANK_TRANSFER",
                status="PENDING",
                currency="LKR",
                amount_minor=amount_minor,
                external_transaction_id=deposit_reference,
                paid_at=None,
            )
            self._session.add(payment)
            await self._session.flush()

            # 5. Create 1-to-1 BankTransferSlip audit evidence
            bank_slip = BankTransferSlip(
                payment_id=payment.id,
                slip_image_url=slip_image_url,
                bank_name=bank_name,
                deposit_reference=deposit_reference,
                depositor_note=reference_note,
                review_status="PENDING",
            )
            self._session.add(bank_slip)
            await self._session.flush()

            # Refresh relationships so the returned model has everything loaded
            sub.payments = [payment]
            payment.bank_slip = bank_slip

            return sub
        except Exception as exc:
            raise DatabaseOperationError(f"Error creating bank slip subscription: {exc}") from exc

    # =========================================================================
    # 4. Admin Verification & Approval (පරිපාලක අනුමැතිය සහ ප්‍රතික්ෂේප කිරීම්)
    # =========================================================================

    async def get_pending_approvals(self) -> List[UserSubscription]:
        """
        පරිපාලකගේ (Admin) පරීක්ෂාව සඳහා රැඳී ඇති සියලුම බැංකු රිසිට්පත් ලැයිස්තුව ලබා ගැනීම.
        """
        try:
            stmt = (
                select(UserSubscription)
                .options(
                    selectinload(UserSubscription.user),
                    selectinload(UserSubscription.payments).selectinload(Payment.bank_slip),
                )
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
        """
        පරිපාලක විසින් බැංකු රිසිට්පත නිවැරදි බව තහවුරු කර අනුමත කිරීම (Admin Verification Approval).
        
        ක්‍රියාත්මක වන වෙනස්කම්:
        1. UserSubscription: status = 'ACTIVE', starts_at = now, expires_at = now + duration_days.
        2. Payment: status = 'COMPLETED', paid_at = now.
        3. BankTransferSlip: review_status = 'APPROVED', reviewed_by = admin_uid, reviewed_at = now.
        """
        try:
            stmt = (
                select(UserSubscription)
                .options(
                    selectinload(UserSubscription.payments).selectinload(Payment.bank_slip)
                )
                .where(UserSubscription.id == subscription_id)
            )
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

            # Update associated payments and bank slip evidence
            for payment in sub.payments:
                if payment.status == "PENDING":
                    payment.status = "COMPLETED"
                    payment.paid_at = now
                    if payment.bank_slip:
                        payment.bank_slip.review_status = "APPROVED"
                        payment.bank_slip.reviewed_by = admin_uid
                        payment.bank_slip.reviewed_at = now
                        payment.bank_slip.admin_feedback = admin_notes

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
        """
        පරිපාලක විසින් අවලංගු හෝ ව්‍යාජ බැංකු රිසිට්පතක් ප්‍රතික්ෂේප කිරීම (Admin Rejection).
        
        ක්‍රියාත්මක වන වෙනස්කම්:
        1. UserSubscription: status = 'REJECTED', admin_notes = rejection_reason.
        2. Payment: status = 'FAILED'.
        3. BankTransferSlip: review_status = 'REJECTED', admin_feedback = rejection_reason.
        """
        try:
            stmt = (
                select(UserSubscription)
                .options(
                    selectinload(UserSubscription.payments).selectinload(Payment.bank_slip)
                )
                .where(UserSubscription.id == subscription_id)
            )
            result = await self._session.execute(stmt)
            sub = result.scalar_one_or_none()
            if not sub:
                return None

            now = datetime.now(timezone.utc)
            sub.status = "REJECTED"
            sub.approved_by = admin_uid
            sub.approved_at = now
            sub.admin_notes = rejection_reason

            # Update associated payments and bank slip evidence
            for payment in sub.payments:
                if payment.status == "PENDING":
                    payment.status = "FAILED"
                    if payment.bank_slip:
                        payment.bank_slip.review_status = "REJECTED"
                        payment.bank_slip.reviewed_by = admin_uid
                        payment.bank_slip.reviewed_at = now
                        payment.bank_slip.admin_feedback = rejection_reason

            await self._session.flush()
            return sub
        except Exception as exc:
            raise DatabaseOperationError(f"Error rejecting subscription: {exc}") from exc

    # =========================================================================
    # 5. RevenueCat Store Webhook Sync (ස්වයංක්‍රීය වෙළඳසැල් ගෙවීම් සම්බන්ධීකරණය)
    # =========================================================================

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
        RevenueCat webhook event එකක් පද්ධතියේ දත්ත සමඟ සමමුහුර්ත කිරීම (State Synchronization).
        
        Event Handling Rules (from RevenueCat Handbook):
        - INITIAL_PURCHASE / RENEWAL: status becomes ACTIVE.
        - CANCELLATION: auto-renew disabled, but user retains access until expires_at!
        - EXPIRATION: access ended, status becomes EXPIRED.
        - BILLING_ISSUE: status becomes GRACE_PERIOD.
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

    # =========================================================================
    # 6. Webhook Idempotency (අනුපිටපත් ඉවෙන්ට් වැළැක්වීම)
    # =========================================================================

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

    # =========================================================================
    # 7. Expiration Maintenance (කල් ඉකුත් වූ සාමාජිකත්ව යාවත්කාලීන කිරීම)
    # =========================================================================

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
