"""
FastAPI Router for Admin Security & TOTP Step-Up Authentication (RFC 6238 Google Authenticator).
Implements the 3 TOTP Hardening Rules from PROTECT_ADMIN.md:
1. Secret Encryption at Rest: Base32 secrets are encrypted using Fernet/AES before database storage.
2. Emergency Recovery Codes: Generates 8 single-use 8-character backup codes stored as salted PBKDF2-HMAC-SHA256 hashes.
3. Replay Protection: Caches verified 6-digit TOTP codes in Redis/In-Memory with a 90s TTL to block replay attacks.
"""

from datetime import datetime, timezone
import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_admin_audit_service,
    require_admin_or_account_audit,
    require_privileged_staff,
)
from app.core.database import get_db
from app.core.totp import (
    build_provisioning_uri,
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_base32_secret,
    generate_recovery_codes,
    hash_recovery_code,
    issue_elevated_session_token,
    verify_and_consume_recovery_code,
    verify_totp_code,
)
from app.domain.enums import AuditAction, AuditResourceType
from app.domain.exceptions import EntityNotFoundError, PermissionDeniedError, ValidationDomainError
from app.models.admin_totp import AdminTotpCredential
from app.schemas.admin_security import (
    AdminAuditLogResponse,
    ElevatedSessionResponse,
    TotpSetupResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
)
from app.schemas.pagination import PaginatedResponse, PaginationMetadata
from app.services.admin_audit_service import AdminAuditService

router = APIRouter(prefix="/admin/security", tags=["Admin Security & TOTP Sudo v1"])


@router.get(
    "/totp/status",
    response_model=TotpStatusResponse,
    summary="Get TOTP 2FA Status for Current Staff Member",
    description="Returns whether Google Authenticator TOTP is enabled and how many emergency backup codes remain.",
)
async def get_totp_status(
    staff_user: dict[str, Any] = Depends(require_privileged_staff),
    session: AsyncSession = Depends(get_db),
) -> TotpStatusResponse:
    """Fetches current TOTP enrollment status for ADMIN, EDITOR, or ACCOUNT_AUDIT staff."""
    uid = str(staff_user["uid"])
    cred = (
        await session.execute(
            select(AdminTotpCredential).where(AdminTotpCredential.user_id == uid)
        )
    ).scalar_one_or_none()

    if not cred:
        return TotpStatusResponse(
            is_enabled=False,
            remaining_recovery_codes=0,
            last_verified_at=None,
        )

    try:
        hashes = json.loads(cred.recovery_codes_hash or "[]")
    except (json.JSONDecodeError, TypeError):
        hashes = []

    return TotpStatusResponse(
        is_enabled=cred.is_enabled,
        remaining_recovery_codes=len(hashes),
        last_verified_at=cred.last_verified_at,
    )


@router.post(
    "/totp/setup",
    response_model=TotpSetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize TOTP Enrollment & Generate 8 Recovery Codes",
    description=(
        "Generates a fresh Base32 TOTP secret (encrypted at rest), an `otpauth://` provisioning URI "
        "for Google Authenticator / 1Password QR scanning, and 8 single-use emergency backup codes "
        "(hashed at rest via PBKDF2-HMAC-SHA256)."
    ),
)
async def setup_totp(
    request: Request,
    staff_user: dict[str, Any] = Depends(require_privileged_staff),
    session: AsyncSession = Depends(get_db),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> TotpSetupResponse:
    """Enrolls or resets TOTP credentials for the authenticated staff member."""
    uid = str(staff_user["uid"])
    email = str(staff_user.get("email") or f"{uid}@mathsdd.lk")

    raw_secret = generate_base32_secret()
    encrypted_secret = encrypt_totp_secret(raw_secret)
    provisioning_uri = build_provisioning_uri(secret=raw_secret, account_name=email)

    plain_recovery_codes = generate_recovery_codes(count=8)
    hashed_codes = [hash_recovery_code(c) for c in plain_recovery_codes]
    recovery_codes_json = json.dumps(hashed_codes)

    cred = (
        await session.execute(
            select(AdminTotpCredential).where(AdminTotpCredential.user_id == uid)
        )
    ).scalar_one_or_none()

    if cred:
        cred.encrypted_secret = encrypted_secret
        cred.recovery_codes_hash = recovery_codes_json
        cred.is_enabled = False
    else:
        cred = AdminTotpCredential(
            user_id=uid,
            encrypted_secret=encrypted_secret,
            recovery_codes_hash=recovery_codes_json,
            is_enabled=False,
        )
        session.add(cred)

    await session.flush()

    await audit_service.record_action(
        actor=staff_user,
        action=AuditAction.ADMIN_TOTP_SETUP_INITIATED.value,
        resource_type=AuditResourceType.ADMIN_TOTP.value,
        resource_id=uid,
        request=request,
    )

    return TotpSetupResponse(
        secret=raw_secret,
        provisioning_uri=provisioning_uri,
        recovery_codes=plain_recovery_codes,
        is_enabled=False,
    )


@router.post(
    "/totp/verify-setup",
    response_model=TotpStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate TOTP Enrollment with Initial 6-Digit Code",
    description="Verifies the first 6-digit code from Google Authenticator and marks TOTP 2FA as enabled.",
)
async def verify_totp_setup(
    body: TotpVerifyRequest,
    request: Request,
    staff_user: dict[str, Any] = Depends(require_privileged_staff),
    session: AsyncSession = Depends(get_db),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> TotpStatusResponse:
    """Verifies initial 6-digit TOTP code and enables TOTP for the staff account."""
    uid = str(staff_user["uid"])
    cred = (
        await session.execute(
            select(AdminTotpCredential).where(AdminTotpCredential.user_id == uid)
        )
    ).scalar_one_or_none()

    if not cred:
        raise EntityNotFoundError(
            "TOTP enrollment not found. Call POST /api/v1/admin/security/totp/setup first."
        )

    raw_secret = decrypt_totp_secret(cred.encrypted_secret)
    is_valid = verify_totp_code(
        secret=raw_secret,
        code=body.code,
        user_id=uid,
        enforce_replay_protection=True,
    )
    if not is_valid:
        raise ValidationDomainError(
            "Invalid or replayed 6-digit TOTP code. Please check your Authenticator app and try again."
        )

    now = datetime.now(timezone.utc)
    cred.is_enabled = True
    cred.last_verified_at = now
    await session.flush()

    await audit_service.record_action(
        actor=staff_user,
        action=AuditAction.ADMIN_TOTP_ENABLED.value,
        resource_type=AuditResourceType.ADMIN_TOTP.value,
        resource_id=uid,
        request=request,
    )

    try:
        hashes = json.loads(cred.recovery_codes_hash or "[]")
    except (json.JSONDecodeError, TypeError):
        hashes = []

    return TotpStatusResponse(
        is_enabled=True,
        remaining_recovery_codes=len(hashes),
        last_verified_at=now,
    )


@router.post(
    "/elevate",
    response_model=ElevatedSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Step-Up Sudo Elevation via TOTP or Single-Use Recovery Code",
    description=(
        "Verifies a 6-digit Google Authenticator TOTP code (with Redis replay protection) "
        "OR one of the 8 single-use emergency backup codes, and issues a 15-minute `X-Elevated-Token`."
    ),
)
async def elevate_admin_session(
    body: TotpVerifyRequest,
    request: Request,
    staff_user: dict[str, Any] = Depends(require_privileged_staff),
    session: AsyncSession = Depends(get_db),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> ElevatedSessionResponse:
    """Validates TOTP or consumes a recovery code to grant a 15-minute elevated sudo session token."""
    uid = str(staff_user["uid"])
    role = str(staff_user.get("role", "ADMIN")).upper()

    cred = (
        await session.execute(
            select(AdminTotpCredential).where(AdminTotpCredential.user_id == uid)
        )
    ).scalar_one_or_none()

    if not cred or not cred.is_enabled:
        raise ValidationDomainError(
            "TOTP 2FA is not enabled for this staff account. Complete /totp/setup and /totp/verify-setup first."
        )

    raw_secret = decrypt_totp_secret(cred.encrypted_secret)
    clean_input = body.code.strip()
    used_recovery = False

    # 1. Try 6-digit RFC 6238 TOTP verification with replay protection
    if len(clean_input.replace(" ", "")) == 6 and clean_input.replace(" ", "").isdigit():
        is_valid_totp = verify_totp_code(
            secret=raw_secret,
            code=clean_input,
            user_id=uid,
            enforce_replay_protection=True,
        )
        if not is_valid_totp:
            raise PermissionDeniedError(
                "Invalid or already-used (replayed) 6-digit TOTP code."
            )
    else:
        # 2. Fallback: Check single-use emergency recovery codes
        matched, updated_hashes_json = verify_and_consume_recovery_code(
            provided_code=clean_input,
            stored_hashes_json=cred.recovery_codes_hash,
        )
        if not matched:
            raise PermissionDeniedError(
                "Invalid TOTP code or emergency recovery code."
            )
        cred.recovery_codes_hash = updated_hashes_json
        used_recovery = True

    cred.last_verified_at = datetime.now(timezone.utc)
    await session.flush()

    try:
        remaining = len(json.loads(cred.recovery_codes_hash or "[]"))
    except (json.JSONDecodeError, TypeError):
        remaining = 0

    await audit_service.record_action(
        actor=staff_user,
        action=AuditAction.ADMIN_SESSION_ELEVATED.value,
        resource_type=AuditResourceType.ADMIN_TOTP.value,
        resource_id=uid,
        request=request,
        details={
            "used_recovery_code": used_recovery,
            "remaining_recovery_codes": remaining,
        },
    )

    token_info = issue_elevated_session_token(user_id=uid, role=role, ttl_seconds=900)
    return ElevatedSessionResponse(
        elevated_token=token_info["elevated_token"],
        expires_in_seconds=token_info["expires_in_seconds"],
        expires_at=token_info["expires_at"],
        used_recovery_code=used_recovery,
        remaining_recovery_codes=remaining,
    )


@router.get(
    "/audit-logs",
    response_model=PaginatedResponse[AdminAuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="List Immutable Admin Audit Logs (Ring 4)",
    description=(
        "Returns the append-only, immutable audit trail of all privileged staff operations "
        "(Bank Slip Approvals/Rejections, Question/Study Note/Curriculum mutations, and TOTP Sudo events) "
        "with actor UID, role, IP address, User-Agent, and UTC timestamp. Accessible to ADMIN and ACCOUNT_AUDIT roles."
    ),
)
async def list_admin_audit_logs(
    actor_uid: str | None = Query(None, description="Filter by staff member UID"),
    actor_role: str | None = Query(None, description="Filter by staff role (ADMIN, EDITOR, ACCOUNT_AUDIT)"),
    action: str | None = Query(None, description="Filter by action code (e.g. BANK_SLIP_APPROVED, QUESTION_DELETED)"),
    resource_type: str | None = Query(None, description="Filter by resource category (SUBSCRIPTION, QUESTION, STUDY_NOTE, etc.)"),
    resource_id: str | None = Query(None, description="Filter by target resource ID"),
    limit: int = Query(50, ge=1, le=200, description="Number of audit log entries per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    _auditor: dict[str, Any] = Depends(require_admin_or_account_audit),
    audit_service: AdminAuditService = Depends(get_admin_audit_service),
) -> PaginatedResponse[AdminAuditLogResponse]:
    """Queries the immutable `admin_audit_logs` ledger in reverse-chronological order."""
    result = await audit_service.list_audit_logs(
        actor_uid=actor_uid,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
        offset=offset,
    )
    items = [AdminAuditLogResponse.model_validate(item) for item in result["items"]]
    total = int(result["total"])
    return PaginatedResponse(
        items=items,
        pagination=PaginationMetadata.from_offset(
            total=total,
            limit=limit,
            offset=offset,
            items_count=len(items),
        ),
    )
