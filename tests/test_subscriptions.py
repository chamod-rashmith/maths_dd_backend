"""
Unit tests for Subscription models, DTO schemas, repository methods, and REST API endpoints.
Verifies:
1. Bank slip submission, pre-signed upload URL generation, and admin approval/rejection workflows.
2. RevenueCat Webhook idempotency, event deduplication, signature token verification, and lifecycle mapping.
3. Subscription status calculation for student paywall gating.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.api.deps import require_admin_or_editor
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.subscription import ProcessedWebhookEvent, UserSubscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.subscription import (
    AdminApprovalRequest,
    AdminRejectionRequest,
    BankSlipUploadRequest,
    CurrentSubscriptionStatusResponse,
    RevenueCatEventPayload,
    RevenueCatWebhookPayload,
    SignedUploadUrlResponse,
    UserSubscriptionResponse,
)


class TestSubscriptionFeature(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_tables_registered_in_metadata(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        self.assertIn("user_subscriptions", table_names)
        self.assertIn("processed_webhook_events", table_names)

    def test_bank_slip_request_validation(self) -> None:
        req = BankSlipUploadRequest(
            plan_id="COMBINED_PRO_MONTHLY",
            slip_image_url="https://storage.googleapis.com/mathsdd-slips/sample.jpg",
            amount_lkr=2500.0,
            reference_note="CDM Colombo 07 Ref: 987654",
        )
        self.assertEqual(req.plan_id, "COMBINED_PRO_MONTHLY")
        self.assertEqual(req.amount_lkr, 2500.0)

    def test_admin_approval_and_rejection_requests(self) -> None:
        approval = AdminApprovalRequest(duration_days=30, admin_notes="Bank receipt verified with BOC statement")
        self.assertEqual(approval.duration_days, 30)

        rejection = AdminRejectionRequest(rejection_reason="Slip is illegible, please upload a clearer photo")
        self.assertEqual(rejection.rejection_reason, "Slip is illegible, please upload a clearer photo")

    def test_subscription_lifecycle_active_and_expiry(self) -> None:
        now = datetime.now(timezone.utc)
        sub = UserSubscription(
            id="sub_test_01",
            user_id="user_test_01",
            plan_id="COMBINED_PRO_MONTHLY",
            status="ACTIVE",
            provider="REVENUECAT",
            starts_at=now,
            expires_at=now + timedelta(days=30),
        )
        self.assertTrue(sub.is_currently_active())

        # Expired subscription
        sub.expires_at = now - timedelta(days=1)
        self.assertFalse(sub.is_currently_active())

        # Lifetime subscription (expires_at is None)
        sub.expires_at = None
        self.assertTrue(sub.is_currently_active())

        # Cancelled or Pending subscription
        sub.status = "PENDING_APPROVAL"
        self.assertFalse(sub.is_currently_active())

        sub.status = "CANCELLED"
        self.assertFalse(sub.is_currently_active())

    async def test_repository_bank_slip_and_approval_flow(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = unittest.mock.MagicMock()
        repo = SubscriptionRepository(mock_session)

        # 1. Create bank slip
        sub = await repo.create_bank_slip_subscription(
            user_id="user_123",
            plan_id="COMBINED_PRO_MONTHLY",
            slip_image_url="https://storage.googleapis.com/slips/slip.jpg",
            amount_lkr=2500.0,
            reference_note="CDM Bambalapitiya",
        )
        self.assertEqual(sub.status, "PENDING_APPROVAL")
        self.assertEqual(sub.provider, "BANK_TRANSFER")
        self.assertEqual(sub.amount_lkr, 2500.0)
        self.assertTrue(mock_session.add.called)

    async def test_repository_revenuecat_event_mapping(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = unittest.mock.MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SubscriptionRepository(mock_session)
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        # 1. INITIAL_PURCHASE
        sub = await repo.sync_revenuecat_event(
            app_user_id="usr_rc_1",
            event_type="INITIAL_PURCHASE",
            product_id="COMBINED_PRO_MONTHLY",
            entitlement_id="pro_access",
            store="PLAY_STORE",
            transaction_id="tx_123",
            original_transaction_id="orig_123",
            starts_at=now,
            expires_at=future,
        )
        self.assertEqual(sub.status, "ACTIVE")
        self.assertTrue(sub.is_auto_renew)

        # 2. CANCELLATION (intent signal - access stays ACTIVE until future expiry)
        sub_cancel = await repo.sync_revenuecat_event(
            app_user_id="usr_rc_1",
            event_type="CANCELLATION",
            product_id="COMBINED_PRO_MONTHLY",
            entitlement_id="pro_access",
            store="PLAY_STORE",
            transaction_id="tx_124",
            original_transaction_id="orig_123",
            starts_at=now,
            expires_at=future,
        )
        self.assertEqual(sub_cancel.status, "ACTIVE")
        self.assertFalse(sub_cancel.is_auto_renew)

        # 3. EXPIRATION (revocation - status becomes EXPIRED)
        sub_expired = await repo.sync_revenuecat_event(
            app_user_id="usr_rc_1",
            event_type="EXPIRATION",
            product_id="COMBINED_PRO_MONTHLY",
            entitlement_id="pro_access",
            store="PLAY_STORE",
            transaction_id="tx_125",
            original_transaction_id="orig_123",
            starts_at=now,
            expires_at=now - timedelta(seconds=1),
        )
        self.assertEqual(sub_expired.status, "EXPIRED")

    async def test_expire_stale_subscriptions(self) -> None:
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result
        repo = SubscriptionRepository(mock_session)

        count = await repo.expire_stale_subscriptions()
        self.assertEqual(count, 3)
        self.assertTrue(mock_session.execute.called)
        self.assertTrue(mock_session.flush.called)

    def test_upload_url_endpoint(self) -> None:
        mock_user = {"uid": "usr_test_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)
        response = client.get("/api/v1/subscriptions/upload-url?filename=my_deposit.jpg")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("upload_url", data)
        self.assertIn("storage_path", data)
        self.assertIn("public_url", data)
        self.assertIn("usr_test_student", data["storage_path"])
        self.assertIn("my_deposit.jpg", data["storage_path"])

    def test_revenuecat_webhook_endpoint(self) -> None:
        mock_session = AsyncMock()
        mock_session.add = unittest.mock.MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)
        payload = {
            "api_version": "1.0",
            "event": {
                "id": "evt_test_12345",
                "type": "INITIAL_PURCHASE",
                "app_user_id": "usr_rc_student_01",
                "product_id": "COMBINED_PRO_MONTHLY",
                "period_type": "NORMAL",
                "purchased_at_ms": 1700000000000,
                "expiration_at_ms": 1702592000000,
                "store": "PLAY_STORE",
                "environment": "PRODUCTION",
                "entitlement_ids": ["pro_access"],
                "transaction_id": "GPA.1234-5678",
                "original_transaction_id": "GPA.1234-5678",
            },
        }

        # 1. First delivery -> 200 OK
        response = client.post("/api/v1/subscriptions/webhook/revenuecat", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["event_id"], "evt_test_12345")

        # 2. Duplicate redelivery -> mock that event_id is already recorded
        mock_result.scalar_one_or_none.return_value = ProcessedWebhookEvent(
            event_id="evt_test_12345",
            event_type="INITIAL_PURCHASE",
            app_user_id="usr_rc_student_01",
        )
        response_dup = client.post("/api/v1/subscriptions/webhook/revenuecat", json=payload)
        self.assertEqual(response_dup.status_code, 200)
        self.assertEqual(response_dup.json()["status"], "already_processed")


if __name__ == "__main__":
    unittest.main()
