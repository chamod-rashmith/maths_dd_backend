"""
RFC 6238 Time-based One-Time Password (TOTP) & Hardening Engine for Admin Sudo Mode.
Provides zero-dependency RFC 6238 TOTP generation/verification, AES/Fernet secret encryption,
PBKDF2-HMAC-SHA256 single-use recovery code hashing, Redis/In-Memory replay protection,
and short-lived elevated session tokens.
"""

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from typing import Any
from urllib.parse import quote

from cryptography.fernet import Fernet

from app.core.cache import HybridCache
from app.core.config import settings
from app.core.field_encryption import decrypt_field, encrypt_field

# Dedicated cache for TOTP replay protection (90s TTL covers +/- 1 step window)
totp_replay_cache = HybridCache(default_ttl_seconds=90)

# Dedicated cache for short-lived Elevated Admin Tokens (15 minutes TTL)
elevated_session_cache = HybridCache(default_ttl_seconds=900)

_DEV_FALLBACK_FERNET_KEY = base64.urlsafe_b64encode(
    hashlib.sha256(b"maths-dd-dev-totp-encryption-key-v1").digest()
).decode("ascii")


def encrypt_totp_secret(secret: str) -> str:
    """
    Encrypts a Base32 TOTP secret at rest.
    Uses configured DATA_ENCRYPTION_KEY in production, with a deterministic
    fallback key in development/test environments if DATA_ENCRYPTION_KEY is unset.
    """
    if settings.DATA_ENCRYPTION_KEY:
        encrypted = encrypt_field(secret)
        if encrypted:
            return encrypted
    cipher = Fernet(_DEV_FALLBACK_FERNET_KEY.encode("ascii"))
    return cipher.encrypt(secret.strip().encode("utf-8")).decode("ascii")


def decrypt_totp_secret(encrypted_secret: str) -> str:
    """Decrypts an encrypted Base32 TOTP secret retrieved from database."""
    if not encrypted_secret:
        return ""
    if settings.DATA_ENCRYPTION_KEY:
        decrypted = decrypt_field(encrypted_secret)
        if decrypted and not decrypted.startswith("gAAAA"):
            return decrypted
    if encrypted_secret.startswith("gAAAA"):
        cipher = Fernet(_DEV_FALLBACK_FERNET_KEY.encode("ascii"))
        return cipher.decrypt(encrypted_secret.encode("ascii")).decode("utf-8")
    return encrypted_secret


def generate_base32_secret(length: int = 32) -> str:
    """Generates a cryptographically random 160-bit (32-char) Base32 secret per RFC 4226/6238."""
    random_bytes = secrets.token_bytes(20)
    return base64.b32encode(random_bytes).decode("ascii")[:length]


def build_provisioning_uri(
    secret: str,
    account_name: str,
    issuer: str = "Maths DD Admin Portal",
) -> str:
    """Constructs a standard otpauth://totp/ URI for Google Authenticator / 1Password QR codes."""
    clean_issuer = quote(issuer.strip())
    clean_account = quote(account_name.strip())
    return (
        f"otpauth://totp/{clean_issuer}:{clean_account}"
        f"?secret={secret.strip()}&issuer={clean_issuer}&algorithm=SHA1&digits=6&period=30"
    )


def _hotp(secret: str, counter: int, digits: int = 6) -> str:
    """Computes RFC 4226 HOTP 6-digit code for a given Base32 secret and time counter."""
    # Pad Base32 secret to a multiple of 8 characters if necessary
    clean_secret = secret.strip().upper().replace(" ", "")
    padding = (8 - len(clean_secret) % 8) % 8
    key = base64.b32decode(clean_secret + ("=" * padding), casefold=True)
    counter_bytes = struct.pack(">Q", counter)
    mac = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    binary = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**digits)).zfill(digits)


def generate_totp_code(
    secret: str,
    timestamp: float | None = None,
    interval: int = 30,
) -> str:
    """Generates the current 6-digit RFC 6238 TOTP code."""
    ts = timestamp if timestamp is not None else time.time()
    counter = int(ts // interval)
    return _hotp(secret, counter)


def verify_totp_code(
    secret: str,
    code: str,
    *,
    user_id: str | None = None,
    valid_window: int = 1,
    timestamp: float | None = None,
    enforce_replay_protection: bool = True,
) -> bool:
    """
    Verifies a 6-digit RFC 6238 TOTP code with +/- 1 step clock drift tolerance
    and strict Redis/In-Memory replay protection.
    """
    cleaned_code = (code or "").strip().replace(" ", "")
    if len(cleaned_code) != 6 or not cleaned_code.isdigit():
        return False

    ts = timestamp if timestamp is not None else time.time()
    current_counter = int(ts // 30)

    matched_counter: int | None = None
    for offset in range(-valid_window, valid_window + 1):
        candidate_counter = current_counter + offset
        expected = _hotp(secret, candidate_counter)
        if hmac.compare_digest(expected, cleaned_code):
            matched_counter = candidate_counter
            break

    if matched_counter is None:
        return False

    if enforce_replay_protection and user_id:
        replay_key = f"totp:used:{user_id}:{matched_counter}:{cleaned_code}"
        if totp_replay_cache.get(replay_key) is not None:
            # Replay detected! Code was already used in this time window.
            return False
        totp_replay_cache.set(replay_key, True, ttl_seconds=90)

    return True


# -----------------------------------------------------------------------------
# Emergency Recovery Codes (8 Single-Use 8-Character Backup Codes)
# -----------------------------------------------------------------------------

def generate_recovery_codes(count: int = 8) -> list[str]:
    """
    Generates `count` single-use emergency backup recovery codes formatted as XXXX-XXXX
    (8 alphanumeric/digit characters).
    """
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    codes: list[str] = []
    for _ in range(count):
        part1 = "".join(secrets.choice(alphabet) for _ in range(4))
        part2 = "".join(secrets.choice(alphabet) for _ in range(4))
        codes.append(f"{part1}-{part2}")
    return codes


def hash_recovery_code(code: str, salt: str | None = None) -> str:
    """Hashes a recovery code using salted PBKDF2-HMAC-SHA256 (200,000 iterations)."""
    normalized = code.strip().upper().replace("-", "").replace(" ", "")
    resolved_salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        normalized.encode("utf-8"),
        resolved_salt.encode("ascii"),
        200_000,
    ).hex()
    return f"pbkdf2_sha256${resolved_salt}${derived}"


def verify_and_consume_recovery_code(
    provided_code: str,
    stored_hashes_json: str,
) -> tuple[bool, str]:
    """
    Verifies a recovery code against the JSON list of hashed codes.
    If valid, removes the matched hash (single-use consumption) and returns (True, updated_json).
    """
    normalized = (provided_code or "").strip().upper().replace("-", "").replace(" ", "")
    if len(normalized) < 6:
        return False, stored_hashes_json

    try:
        hashes: list[str] = json.loads(stored_hashes_json or "[]")
    except (json.JSONDecodeError, TypeError):
        return False, "[]"

    remaining_hashes: list[str] = []
    matched = False

    for entry in hashes:
        if matched:
            remaining_hashes.append(entry)
            continue

        parts = entry.split("$")
        if len(parts) == 3 and parts[0] == "pbkdf2_sha256":
            salt = parts[1]
            candidate_hash = hash_recovery_code(normalized, salt=salt)
            if hmac.compare_digest(candidate_hash, entry):
                matched = True
                continue
        remaining_hashes.append(entry)

    return matched, json.dumps(remaining_hashes)


# -----------------------------------------------------------------------------
# Elevated Sudo Session Token (15-Minute TTL)
# -----------------------------------------------------------------------------

def issue_elevated_session_token(
    user_id: str,
    role: str,
    ttl_seconds: int = 900,
) -> dict[str, Any]:
    """Issues a short-lived elevated sudo token stored in Redis/In-Memory cache."""
    token = f"sudo_{secrets.token_urlsafe(32)}"
    expires_at = int(time.time()) + ttl_seconds
    payload = {
        "uid": user_id,
        "role": role,
        "expires_at": expires_at,
    }
    elevated_session_cache.set(f"sudo:token:{token}", payload, ttl_seconds=ttl_seconds)
    return {
        "elevated_token": token,
        "expires_in_seconds": ttl_seconds,
        "expires_at": expires_at,
    }


def verify_elevated_session_token(token: str | None, expected_uid: str) -> bool:
    """Verifies that an X-Elevated-Token is valid, unexpired, and bound to `expected_uid`."""
    if not token or not token.strip():
        return False
    clean_token = token.strip()
    data = elevated_session_cache.get(f"sudo:token:{clean_token}")
    if not isinstance(data, dict):
        return False
    if data.get("uid") != expected_uid:
        return False
    if int(data.get("expires_at", 0)) < int(time.time()):
        return False
    return True
