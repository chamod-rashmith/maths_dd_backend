"""
Unit & Integration tests for Admin TOTP (RFC 6238) Hardening Rules:
1. Secret Encryption at Rest (Fernet/AES encryption of Base32 TOTP secret in `admin_totp_credentials`).
2. Emergency Recovery Codes (8 single-use backup codes hashed with salted PBKDF2-HMAC-SHA256).
3. Replay Protection (Redis/In-Memory 90-second replay cache blocking reuse of a 6-digit code in the same window).
4. Step-Up Sudo Session Tokens (`X-Elevated-Token` 15-minute TTL) and development-friendly enforcement.
"""

import unittest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_curriculum_service, get_user_repository
from app.core.database import Base, get_db
from app.core.totp import (
    decrypt_totp_secret,
    elevated_session_cache,
    encrypt_totp_secret,
    generate_base32_secret,
    generate_recovery_codes,
    generate_totp_code,
    hash_recovery_code,
    totp_replay_cache,
    verify_and_consume_recovery_code,
    verify_totp_code,
)
from app.main import app
from app.models.admin_totp import AdminTotpCredential
from app.models.user import User
from app.services.curriculum_service import CurriculumService


class TestTotpHardeningEngine(unittest.TestCase):
    """Tests the cryptographic TOTP engine, secret encryption, recovery codes, and replay protection."""

    def setUp(self) -> None:
        totp_replay_cache.clear()
        elevated_session_cache.clear()

    def tearDown(self) -> None:
        totp_replay_cache.clear()
        elevated_session_cache.clear()

    def test_rule1_secret_encryption_at_rest(self) -> None:
        """Rule 1: Verify Base32 TOTP secret is encrypted at rest and never stored in plaintext."""
        raw_secret = generate_base32_secret()
        self.assertEqual(len(raw_secret), 32)

        encrypted = encrypt_totp_secret(raw_secret)
        self.assertNotEqual(encrypted, raw_secret)
        self.assertTrue(encrypted.startswith("gAAAA"))

        decrypted = decrypt_totp_secret(encrypted)
        self.assertEqual(decrypted, raw_secret)

    def test_rule2_recovery_codes_hashed_and_single_use(self) -> None:
        """Rule 2: Verify 8 recovery codes are hashed with salted PBKDF2 and consumed on first use."""
        import json

        codes = generate_recovery_codes(count=8)
        self.assertEqual(len(codes), 8)
        for c in codes:
            self.assertEqual(len(c), 9)  # XXXX-XXXX

        hashed_list = [hash_recovery_code(c) for c in codes]
        stored_json = json.dumps(hashed_list)

        # Verify plaintext code is not present in stored JSON
        self.assertNotIn(codes[0], stored_json)

        # First use of code[0] -> succeeds and removes it from remaining hashes
        ok1, updated_json = verify_and_consume_recovery_code(codes[0], stored_json)
        self.assertTrue(ok1)
        self.assertEqual(len(json.loads(updated_json)), 7)

        # Second use of the exact same recovery code -> strictly rejected!
        ok2, _ = verify_and_consume_recovery_code(codes[0], updated_json)
        self.assertFalse(ok2)

    def test_rule3_totp_replay_protection_blocks_reused_code(self) -> None:
        """Rule 3: Verify a 6-digit TOTP code cannot be replayed within the same time window."""
        secret = generate_base32_secret()
        fixed_ts = 1700000000.0
        code = generate_totp_code(secret, timestamp=fixed_ts)

        # 1st verification succeeds
        first_try = verify_totp_code(
            secret,
            code,
            user_id="admin_001",
            timestamp=fixed_ts,
            enforce_replay_protection=True,
        )
        self.assertTrue(first_try)

        # 2nd verification with the exact same code in the same window -> blocked by replay cache!
        second_try = verify_totp_code(
            secret,
            code,
            user_id="admin_001",
            timestamp=fixed_ts + 5.0,
            enforce_replay_protection=True,
        )
        self.assertFalse(second_try)


class TestAdminTotpEndpoints(unittest.IsolatedAsyncioTestCase):
    """End-to-end tests for /api/v1/admin/security TOTP setup, verification, and sudo elevation."""

    async def asyncSetUp(self) -> None:
        totp_replay_cache.clear()
        elevated_session_cache.clear()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        async with self.session_factory() as session:
            session.add(
                User(
                    uid="admin_totp_1",
                    email="admin@mathsdd.lk",
                    name="Admin User",
                    role="ADMIN",
                )
            )
            await session.commit()

        async def override_get_db():
            async with self.session_factory() as session:
                yield session
                await session.commit()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "admin_totp_1",
            "email": "admin@mathsdd.lk",
            "role": "ADMIN",
        }

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()
        totp_replay_cache.clear()
        elevated_session_cache.clear()
        await self.engine.dispose()

    def test_full_totp_lifecycle_setup_verify_elevate_and_recovery(self) -> None:
        client = TestClient(app)

        # 1. Initial status is disabled
        status_res = client.get("/api/v1/admin/security/totp/status")
        self.assertEqual(status_res.status_code, 200)
        self.assertFalse(status_res.json()["is_enabled"])

        # 2. Setup TOTP -> returns secret, otpauth URI, and 8 recovery codes
        setup_res = client.post("/api/v1/admin/security/totp/setup")
        self.assertEqual(setup_res.status_code, 200)
        setup_data = setup_res.json()
        secret = setup_data["secret"]
        recovery_codes = setup_data["recovery_codes"]
        self.assertEqual(len(recovery_codes), 8)
        self.assertIn("otpauth://totp/", setup_data["provisioning_uri"])

        # 3. Verify setup with valid 6-digit TOTP code
        valid_code = generate_totp_code(secret)
        verify_res = client.post(
            "/api/v1/admin/security/totp/verify-setup",
            json={"code": valid_code},
        )
        self.assertEqual(verify_res.status_code, 200)
        self.assertTrue(verify_res.json()["is_enabled"])
        self.assertEqual(verify_res.json()["remaining_recovery_codes"], 8)

        # 4. Replay Attack Check: Re-submitting the exact same 6-digit TOTP code to /elevate is blocked!
        replay_res = client.post(
            "/api/v1/admin/security/elevate",
            json={"code": valid_code},
        )
        self.assertEqual(replay_res.status_code, 403)
        self.assertIn("replayed", replay_res.json()["detail"].lower())

        # 5. Elevate using one of the 8 single-use Emergency Recovery Codes
        elevate_res = client.post(
            "/api/v1/admin/security/elevate",
            json={"code": recovery_codes[0]},
        )
        self.assertEqual(elevate_res.status_code, 200)
        elev_data = elevate_res.json()
        self.assertTrue(elev_data["used_recovery_code"])
        self.assertEqual(elev_data["remaining_recovery_codes"], 7)
        elevated_token = elev_data["elevated_token"]
        self.assertTrue(elevated_token.startswith("sudo_"))

        # 6. Use X-Elevated-Token header on an admin mutation endpoint
        mock_curr_service = AsyncMock(spec=CurriculumService)
        mock_curr_service.delete_lesson.return_value = {
            "status": "success",
            "deleted_id": "les_trig",
        }
        app.dependency_overrides[get_curriculum_service] = lambda: mock_curr_service

        del_res = client.delete(
            "/api/v1/curriculum/lessons/les_trig",
            headers={"X-Elevated-Token": elevated_token},
        )
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["deleted_id"], "les_trig")

        # 7. Passing an invalid X-Elevated-Token header is rejected with 403 Forbidden
        bad_del_res = client.delete(
            "/api/v1/curriculum/lessons/les_trig",
            headers={"X-Elevated-Token": "sudo_invalid_forged_token"},
        )
        self.assertEqual(bad_del_res.status_code, 403)
        self.assertIn("Invalid or expired X-Elevated-Token", bad_del_res.json()["detail"])

    def test_standard_student_blocked_from_totp_endpoints(self) -> None:
        student = {"uid": "student_01", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: student
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = student
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

        client = TestClient(app)
        res = client.post("/api/v1/admin/security/totp/setup")
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
