"""
Pydantic DTO schemas for Admin TOTP (RFC 6238 Google Authenticator) Registration,
Emergency Recovery Codes, and Step-Up Sudo Elevation.
"""

from datetime import datetime
import json
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TotpSetupResponse(BaseModel):
    """
    Returned when an Admin, Editor, or Account Auditor initiates TOTP enrollment.
    Contains the Base32 secret (for manual entry), standard `otpauth://` URI (for QR code rendering),
    and 8 single-use emergency recovery codes (displayed only once upon setup).
    """

    model_config = ConfigDict(from_attributes=True)

    secret: str = Field(..., description="Base32 RFC 6238 TOTP secret for Google Authenticator / 1Password")
    provisioning_uri: str = Field(..., description="Standard otpauth://totp/... URI to render as QR code")
    recovery_codes: list[str] = Field(
        ...,
        description="8 single-use emergency backup codes (save these safely; they are hashed at rest and shown only once)",
    )
    is_enabled: bool = Field(
        False,
        description="Becomes True once the user verifies their first 6-digit code via /verify-setup",
    )


class TotpVerifyRequest(BaseModel):
    """Request payload for verifying a 6-digit TOTP code or an 8-character emergency recovery code."""

    code: str = Field(
        ...,
        min_length=6,
        max_length=16,
        description="6-digit Google Authenticator TOTP code (e.g. '482910') or 8-char recovery code (e.g. 'ABCD-1234')",
    )


class TotpStatusResponse(BaseModel):
    """Current TOTP configuration status for the authenticated privileged user."""

    model_config = ConfigDict(from_attributes=True)

    is_enabled: bool = Field(..., description="Whether TOTP 2FA is active for this account")
    remaining_recovery_codes: int = Field(0, ge=0, description="Number of unused emergency backup codes remaining")
    last_verified_at: datetime | None = Field(None, description="Timestamp of most recent TOTP or recovery verification")


class ElevatedSessionResponse(BaseModel):
    """
    Short-lived Sudo / Step-Up session token returned after successful TOTP or Recovery Code verification.
    Pass `elevated_token` in the `X-Elevated-Token` header for high-risk mutations when sudo mode is active.
    """

    elevated_token: str = Field(..., description="Short-lived sudo token for X-Elevated-Token header")
    expires_in_seconds: int = Field(900, description="Token lifespan in seconds (default 900s = 15 minutes)")
    expires_at: int = Field(..., description="Unix epoch expiration timestamp")
    used_recovery_code: bool = Field(False, description="True if an emergency single-use recovery code was consumed")
    remaining_recovery_codes: int = Field(0, ge=0, description="Number of unused emergency backup codes remaining")


class AdminAuditLogResponse(BaseModel):
    """
    Immutable Admin Audit Log entry response DTO (Ring 4 of PROTECT_ADMIN.md).
    Shows who performed a privileged action, when, from which IP, and on which resource.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique UUIDv4 audit log identifier")
    actor_uid: str = Field(..., description="UID of the Admin, Editor, or Account Auditor who performed the action")
    actor_email: str | None = Field(None, description="Email of the privileged staff member")
    actor_role: str = Field(..., description="Role held at the time of action (ADMIN, EDITOR, ACCOUNT_AUDIT)")
    action: str = Field(
        ...,
        description="Standardized action identifier (e.g. BANK_SLIP_APPROVED, BANK_SLIP_REJECTED, QUESTION_DELETED, STUDY_NOTE_DELETED)",
    )
    resource_type: str = Field(
        ...,
        description="Target entity category (SUBSCRIPTION, QUESTION, STUDY_NOTE, SUBJECT, LESSON, ADMIN_TOTP)",
    )
    resource_id: str | None = Field(None, description="Target entity primary key / ID")
    ip_address: str | None = Field(None, description="Client IP address of the actor")
    user_agent: str | None = Field(None, description="HTTP User-Agent string")
    request_method: str | None = Field(None, description="HTTP verb (POST, DELETE, PUT)")
    request_path: str | None = Field(None, description="Request endpoint path")
    details: dict[str, Any] | None = Field(
        None,
        description="Structured contextual details (e.g. rejection_reason, duration_days, title)",
    )
    created_at: datetime = Field(..., description="Immutable UTC timestamp when the action occurred")

    @field_validator("details", mode="before")
    @classmethod
    def parse_json_details(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            try:
                parsed = json.loads(s)
                return parsed if isinstance(parsed, dict) else {"value": parsed}
            except json.JSONDecodeError:
                return {"raw": s}
        return None

