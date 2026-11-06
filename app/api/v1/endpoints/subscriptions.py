"""
Subscriptions & Monetization REST API Endpoints.
මෙම API මොඩියුලය මඟින් සාමාජිකත්ව (Subscriptions), පැකේජ විස්තර (Plans), සහ බැංකු රිසිට්පත්
පරීක්ෂා කිරීමේ (Bank Slip Approval) සියලුම HTTP Endpoints කළමනාකරණය කරයි.

Supported Capabilities:
1. Public / Student Catalog:
   - `GET /subscriptions/plans`: Returns active educational subscription plans with minor-unit pricing.
2. Sri Lankan Direct Bank Deposit Slip Workflow:
   - `GET /subscriptions/upload-url`: Generates pre-signed Cloud Storage PUT URLs for client-direct uploads.
   - `POST /subscriptions/bank-slip`: Student uploads deposit slip for admin verification (PENDING_APPROVAL).
3. Access & Paywall Gating:
   - `GET /subscriptions/status`: Real-time premium check and expiry countdown for mobile paywalls.
   - `GET /subscriptions/history`: Student's historical subscription records.
4. Automated In-App Purchases (RevenueCat):
   - `POST /subscriptions/webhook/revenuecat`: Server-to-server webhook receiver with idempotency deduplication.
5. Human Admin Verification Operations:
   - `GET /subscriptions/admin/pending`: List all pending bank slips awaiting verification.
   - `POST /subscriptions/admin/{subscription_id}/approve`: Admin approves deposit, activating premium access.
   - `POST /subscriptions/admin/{subscription_id}/reject`: Admin rejects invalid slip with reason.
   - `POST /subscriptions/admin/maintenance/expire-stale`: Scheduled worker for expiring overdue subscriptions.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_or_account_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import generate_signed_upload_url
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.common import (
    MaintenanceExpirationResponse,
    WebhookAckResponse,
)
from app.schemas.subscription import (
    AdminApprovalRequest,
    AdminRejectionRequest,
    BankSlipUploadRequest,
    CurrentSubscriptionStatusResponse,
    RevenueCatWebhookPayload,
    SignedUploadUrlResponse,
    SubscriptionPlanResponse,
    UserSubscriptionResponse,
)

logger = logging.getLogger("maths_dd.subscriptions")

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions & Billing"])


# =============================================================================
# 1. Public & Student Catalog Endpoints (පැකේජ සහ මිල ගණන්)
# =============================================================================

@router.get(
    "/plans",
    response_model=List[SubscriptionPlanResponse],
    summary="Get Active Subscription Plans & Pricing",
    description=(
        "Returns all currently active educational subscription plans with localized Sinhala titles, "
        "descriptions, duration days, feature lists, and prices. Internal database audit timestamps are stripped."
    ),
)
async def list_subscription_plans(
    session: AsyncSession = Depends(get_db),
) -> List[SubscriptionPlanResponse]:
    """
    ශිෂ්‍යයන්ට සහ සාමාන්‍ය පරිශීලකයින්ට පෙන්වීම සඳහා සක්‍රිය සාමාජිකත්ව පැකේජ (Plans) ලැයිස්තුව ලබා දීම.
    """
    repo = SubscriptionRepository(session)
    plans = await repo.list_active_plans()
    return [SubscriptionPlanResponse.model_validate(p) for p in plans]


@router.get(
    "/upload-url",
    response_model=SignedUploadUrlResponse,
    summary="Get Pre-signed GCS Upload URL for Bank Slip",
    description=(
        "Generates a short-lived (15 minutes) pre-signed PUT URL allowing the client mobile app "
        "to upload the bank deposit slip image directly to Google Cloud Storage (Firebase Storage). "
        "This completely bypasses backend memory and bandwidth overhead."
    ),
)
async def get_slip_upload_url(
    filename: str = Query(..., description="Original image filename (e.g. 'deposit_slip.jpg')"),
    content_type: str = Query("image/jpeg", description="MIME type of the slip image (e.g. 'image/jpeg', 'image/png')"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SignedUploadUrlResponse:
    """Generate a pre-signed GCS upload URL for a student's deposit slip."""
    user_id = current_user.get("uid")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user authentication.")

    # Generate a unique storage blob path to prevent collisions
    unique_suffix = uuid.uuid4().hex[:12]
    clean_filename = filename.replace(" ", "_").strip()
    storage_path = f"slips/{user_id}/{unique_suffix}_{clean_filename}"

    upload_url = generate_signed_upload_url(
        storage_path=storage_path,
        content_type=content_type,
        expiration_minutes=15,
    )

    # Permanent reference path for database persistence
    bucket_name = settings.STORAGE_BUCKET_NAME.replace("gs://", "").strip()
    public_url = f"https://storage.googleapis.com/{bucket_name}/{storage_path}"

    return SignedUploadUrlResponse(
        upload_url=upload_url,
        storage_path=storage_path,
        public_url=public_url,
    )


@router.post(
    "/bank-slip",
    response_model=UserSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Bank Deposit Slip for Approval",
    description=(
        "Student submits details of a physical bank deposit or CDM transfer with the uploaded slip URL. "
        "Creates a subscription record with PENDING_APPROVAL status and a linked pending payment. "
        "Zero premium access is granted until an admin approves the submission."
    ),
)
async def submit_bank_slip(
    payload: BankSlipUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserSubscriptionResponse:
    """Create a pending bank slip subscription submission."""
    user_id = current_user.get("uid")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User authentication required.")

    repo = SubscriptionRepository(session)
    sub = await repo.create_bank_slip_subscription(
        user_id=user_id,
        plan_id=payload.plan_id,
        slip_image_url=payload.slip_image_url,
        amount_lkr=payload.amount_lkr,
        amount_minor=payload.amount_minor,
        bank_name=payload.bank_name,
        deposit_reference=payload.deposit_reference,
        reference_note=payload.reference_note,
    )
    return UserSubscriptionResponse.model_validate(sub)


@router.get(
    "/status",
    response_model=CurrentSubscriptionStatusResponse,
    summary="Get Current User's Active Premium & Subscription Status",
    description=(
        "Checks whether the student currently has active premium access, the active plan details, "
        "and days remaining before expiration. Used by Flutter client for paywall gating."
    ),
)
async def get_subscription_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CurrentSubscriptionStatusResponse:
    """Fetch current premium status and remaining days for authenticated student."""
    user_id = current_user.get("uid")
    user_role = str(current_user.get("role", "")).upper()

    # Admins automatically have unrestricted premium access
    if user_role == "ADMIN":
        return CurrentSubscriptionStatusResponse(
            is_premium=True,
            plan_id="ADMIN_OVERRIDE",
            status="ACTIVE",
            provider="MANUAL_ADMIN",
            expires_at=None,
            days_remaining=9999,
            active_subscription=None,
        )

    repo = SubscriptionRepository(session)
    active_sub = await repo.get_active_subscription(user_id)

    if not active_sub:
        return CurrentSubscriptionStatusResponse(
            is_premium=False,
            plan_id=None,
            status="NONE",
            provider=None,
            expires_at=None,
            days_remaining=0,
            active_subscription=None,
        )

    now = datetime.now(timezone.utc)
    days_remaining = None
    if active_sub.expires_at:
        delta = active_sub.expires_at - now
        days_remaining = max(0, delta.days)

    return CurrentSubscriptionStatusResponse(
        is_premium=True,
        plan_id=active_sub.plan_id,
        status=active_sub.status,
        provider=active_sub.provider,
        expires_at=active_sub.expires_at,
        days_remaining=days_remaining,
        active_subscription=UserSubscriptionResponse.model_validate(active_sub),
    )


@router.get(
    "/history",
    response_model=List[UserSubscriptionResponse],
    summary="Get User's Subscription History",
    description="Returns all previous and current subscription records for the student ordered newest first.",
)
async def get_subscription_history(
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[UserSubscriptionResponse]:
    """Fetch subscription history records for current user."""
    user_id = current_user.get("uid")
    repo = SubscriptionRepository(session)
    subs = await repo.get_user_subscriptions(user_id)
    return [UserSubscriptionResponse.model_validate(s) for s in subs]


# =============================================================================
# 2. RevenueCat Webhook Receiver (Google Play & Apple App Store)
# =============================================================================

@router.post(
    "/webhook/revenuecat",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="RevenueCat Server-to-Server Webhook Receiver",
    description=(
        "Receives normalized webhook events from RevenueCat for automated store purchases. "
        "Enforces idempotency using `event.id` and updates subscription entitlements accordingly."
    ),
)
async def handle_revenuecat_webhook(
    payload: RevenueCatWebhookPayload,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Consumes RevenueCat webhook events with signature verification and deduplication.
    Always returns HTTP 200 upon successful receipt or duplicate detection to prevent retry spam.
    """
    # 1. Authorization check if configured
    expected_token = settings.REVENUECAT_WEBHOOK_AUTH_TOKEN
    if expected_token:
        auth_header = authorization or ""
        token = auth_header.replace("Bearer ", "").strip()
        if token != expected_token:
            logger.warning("Unauthorized RevenueCat webhook attempt with token: %s", token[:6] + "..." if token else "empty")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook authorization token.")

    event = payload.event
    event_id = event.id
    event_type = event.type
    app_user_id = event.app_user_id

    logger.info("Processing RevenueCat event: id=%s, type=%s, user=%s", event_id, event_type, app_user_id)

    repo = SubscriptionRepository(session)

    # 2. Idempotency deduplication check
    is_processed = await repo.is_webhook_event_processed(event_id)
    if is_processed:
        logger.info("RevenueCat event '%s' was already processed. Acknowledging with HTTP 200.", event_id)
        return {"status": "already_processed", "event_id": event_id}

    # 3. Parse millisecond timestamps to Python UTC datetime objects
    starts_at = (
        datetime.fromtimestamp(event.purchased_at_ms / 1000, tz=timezone.utc)
        if event.purchased_at_ms
        else datetime.now(timezone.utc)
    )
    expires_at = (
        datetime.fromtimestamp(event.expiration_at_ms / 1000, tz=timezone.utc)
        if event.expiration_at_ms
        else None
    )

    # 4. Resolve product and entitlement details
    product_id = event.product_id or "COMBINED_PRO_MONTHLY"
    entitlement_ids = event.entitlement_ids or ["pro_access"]
    primary_entitlement = entitlement_ids[0] if entitlement_ids else "pro_access"
    store = event.store or "PLAY_STORE"
    transaction_id = event.transaction_id or event_id
    original_transaction_id = event.original_transaction_id or transaction_id

    # 5. Synchronize subscription state
    await repo.sync_revenuecat_event(
        app_user_id=app_user_id,
        event_type=event_type,
        product_id=product_id,
        entitlement_id=primary_entitlement,
        store=store,
        transaction_id=transaction_id,
        original_transaction_id=original_transaction_id,
        starts_at=starts_at,
        expires_at=expires_at,
        is_auto_renew=event_type not in ("CANCELLATION", "EXPIRATION"),
    )

    # 6. Record event ID in processed_webhook_events for future idempotency
    await repo.record_webhook_event(
        event_id=event_id,
        event_type=event_type,
        app_user_id=app_user_id,
    )

    logger.info("Successfully synchronized RevenueCat event: %s for user %s", event_id, app_user_id)
    return {"status": "success", "event_id": event_id, "type": event_type}


# =============================================================================
# 3. Admin Verification & Management Endpoints (පරිපාලක මෙහෙයුම්)
# =============================================================================

@router.get(
    "/admin/pending",
    response_model=List[UserSubscriptionResponse],
    summary="List Pending Bank Slips for Admin Review",
    description="Returns all subscriptions with PENDING_APPROVAL status awaiting human admin review.",
)
async def list_pending_subscriptions(
    admin: Dict[str, Any] = Depends(require_admin_or_account_audit),
    session: AsyncSession = Depends(get_db),
) -> List[UserSubscriptionResponse]:
    """Retrieve all pending bank slip submissions."""
    repo = SubscriptionRepository(session)
    pending = await repo.get_pending_approvals()
    return [UserSubscriptionResponse.model_validate(p) for p in pending]


@router.post(
    "/admin/{subscription_id}/approve",
    response_model=UserSubscriptionResponse,
    summary="Approve a Bank Slip Subscription",
    description=(
        "Admin approves a valid deposit slip, activating premium access for the specified duration "
        "and marking associated payment records as COMPLETED."
    ),
)
async def approve_subscription(
    subscription_id: str,
    payload: AdminApprovalRequest,
    admin: Dict[str, Any] = Depends(require_admin_or_account_audit),
    session: AsyncSession = Depends(get_db),
) -> UserSubscriptionResponse:
    """Approve a pending subscription and grant active access."""
    admin_uid = admin.get("uid", "admin")
    repo = SubscriptionRepository(session)
    sub = await repo.approve_subscription(
        subscription_id=subscription_id,
        admin_uid=admin_uid,
        duration_days=payload.duration_days,
        admin_notes=payload.admin_notes,
    )
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with id '{subscription_id}' not found.",
        )
    return UserSubscriptionResponse.model_validate(sub)


@router.post(
    "/admin/{subscription_id}/reject",
    response_model=UserSubscriptionResponse,
    summary="Reject an Invalid or Fraudulent Bank Slip",
    description=(
        "Admin marks a bank slip submission as REJECTED with a required reason displayed to the student "
        "and marks associated payment records as FAILED."
    ),
)
async def reject_subscription(
    subscription_id: str,
    payload: AdminRejectionRequest,
    admin: Dict[str, Any] = Depends(require_admin_or_account_audit),
    session: AsyncSession = Depends(get_db),
) -> UserSubscriptionResponse:
    """Reject a bank slip submission with reason."""
    admin_uid = admin.get("uid", "admin")
    repo = SubscriptionRepository(session)
    sub = await repo.reject_subscription(
        subscription_id=subscription_id,
        admin_uid=admin_uid,
        rejection_reason=payload.rejection_reason,
    )
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with id '{subscription_id}' not found.",
        )
    return UserSubscriptionResponse.model_validate(sub)


@router.post(
    "/admin/maintenance/expire-stale",
    response_model=MaintenanceExpirationResponse,
    summary="Trigger Subscription Expiration Maintenance Routine",
    description=(
        "Scans all ACTIVE subscriptions whose expires_at timestamp has passed and updates "
        "their status to EXPIRED. Can be triggered by Google Cloud Scheduler or Admin Cron."
    ),
)
async def trigger_expire_stale_subscriptions(
    admin: Dict[str, Any] = Depends(require_admin_or_account_audit),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Expire subscriptions past their expiration date."""
    repo = SubscriptionRepository(session)
    expired_count = await repo.expire_stale_subscriptions()
    return {
        "status": "success",
        "expired_count": expired_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
