"""
Pydantic DTO schemas for Admin TOTP (RFC 6238 Google Authenticator) Registration,
Emergency Recovery Codes, and Step-Up Sudo Elevation.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


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
