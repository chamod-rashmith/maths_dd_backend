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

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_privileged_staff
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
from app.domain.exceptions import EntityNotFoundError, PermissionDeniedError, ValidationDomainError
from app.models.admin_totp import AdminTotpCredential
from app.schemas.admin_security import (
    ElevatedSessionResponse,
    TotpSetupResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
)

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
    staff_user: dict[str, Any] = Depends(require_privileged_staff),
    session: AsyncSession = Depends(get_db),
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
    staff_user: dict[str, Any] = Depends(require_privileged_staff),
    session: AsyncSession = Depends(get_db),
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
    staff_user: dict[str, Any] = Depends(require_privileged_staff),
    session: AsyncSession = Depends(get_db),
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

    token_info = issue_elevated_session_token(user_id=uid, role=role, ttl_seconds=900)
    return ElevatedSessionResponse(
        elevated_token=token_info["elevated_token"],
        expires_in_seconds=token_info["expires_in_seconds"],
        expires_at=token_info["expires_at"],
        used_recovery_code=used_recovery,
        remaining_recovery_codes=remaining,
    )
