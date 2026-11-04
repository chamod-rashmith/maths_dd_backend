"""
Unit tests for Subscription, Plans, Pricing, Bank Slips, and Monetization API endpoints.
Verifies:
1. Normalized Table Registration in SQLAlchemy Metadata (Domain 7).
2. Minor-Unit Pricing and Financial Precision (amount_minor in cents, amount_lkr helper).
3. Bank slip submission, pre-signed upload URL generation, and admin approval/rejection workflows.
4. RevenueCat Webhook idempotency, event deduplication, and lifecycle state mapping.
5. Subscription status calculation for student paywall gating (PENDING_APPROVAL gates premium access).
6. Stripping of internal database timestamps from public plan responses.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.api.deps import get_user_repository, require_admin_or_editor
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.subscription import (
    BankTransferSlip,
    Payment,
    PlanPrice,
    ProcessedWebhookEvent,
    SubscriptionPlan,
    UserSubscription,
)
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.subscription import (
    AdminApprovalRequest,
    AdminRejectionRequest,
    BankSlipUploadRequest,
    CurrentSubscriptionStatusResponse,
    PlanPriceResponse,
    RevenueCatEventPayload,
    RevenueCatWebhookPayload,
    SignedUploadUrlResponse,
    SubscriptionPlanResponse,
    UserSubscriptionResponse,
)


class TestSubscriptionFeature(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_tables_registered_in_metadata(self) -> None:
        """Verify that all normalized Domain 7 tables are registered in Base.metadata."""
        table_names = set(Base.metadata.tables.keys())
        self.assertIn("subscription_plans", table_names)
        self.assertIn("plan_prices", table_names)
        self.assertIn("user_subscriptions", table_names)
        self.assertIn("payments", table_names)
        self.assertIn("bank_transfer_slips", table_names)
        self.assertIn("processed_webhook_events", table_names)

    def test_minor_unit_pricing_and_payment_models(self) -> None:
        """Verify integer minor-unit arithmetic prevents floating-point inaccuracies."""
        price = PlanPrice(
            id="prc_01",
            plan_id="plan_01",
            currency="LKR",
            amount_minor=250000,  # Rs. 2,500.00
            is_active=True,
        )
        self.assertEqual(price.amount_minor, 250000)
        self.assertEqual(price.amount_lkr, 2500.0)

        payment = Payment(
            id="pay_01",
            subscription_id="sub_01",
            user_id="usr_01",
            method="BANK_TRANSFER",
            status="PENDING",
            currency="LKR",
            amount_minor=2400000,  # Rs. 24,000.00
        )
        self.assertEqual(payment.amount_minor, 2400000)
        self.assertEqual(payment.amount_lkr, 24000.0)

    def test_bank_slip_request_validation(self) -> None:
        """Verify BankSlipUploadRequest harmonizes amount_lkr and amount_minor."""
        # 1. Given amount_lkr, auto-compute amount_minor
        req1 = BankSlipUploadRequest(
            plan_id="COMBINED_PRO_MONTHLY",
            slip_image_url="https://storage.googleapis.com/mathsdd-slips/sample.jpg",
            amount_lkr=2500.0,
            reference_note="CDM Colombo 07 Ref: 987654",
        )
        self.assertEqual(req1.plan_id, "COMBINED_PRO_MONTHLY")
        self.assertEqual(req1.amount_lkr, 2500.0)
        self.assertEqual(req1.amount_minor, 250000)

        # 2. Given amount_minor, auto-compute amount_lkr
        req2 = BankSlipUploadRequest(
            plan_id="COMBINED_PRO_ANNUAL",
            slip_image_url="https://storage.googleapis.com/mathsdd-slips/sample2.jpg",
            amount_minor=2400000,
        )
        self.assertEqual(req2.amount_minor, 2400000)
        self.assertEqual(req2.amount_lkr, 24000.0)

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

        # Pending approval subscription -> strictly NOT active!
        sub.status = "PENDING_APPROVAL"
        self.assertFalse(sub.is_currently_active())

        sub.status = "CANCELLED"
        self.assertFalse(sub.is_currently_active())

    async def test_repository_bank_slip_creation_creates_normalized_entities(self) -> None:
        """Verify repository atomically creates UserSubscription, Payment, and BankTransferSlip."""
        mock_session = AsyncMock()
        mock_session.add = unittest.mock.MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SubscriptionRepository(mock_session)

        sub = await repo.create_bank_slip_subscription(
            user_id="user_123",
            plan_id="COMBINED_PRO_MONTHLY",
            slip_image_url="https://storage.googleapis.com/slips/slip.jpg",
            amount_lkr=2500.0,
            amount_minor=250000,
            bank_name="Bank of Ceylon",
            deposit_reference="CDM-998877",
            reference_note="Colombo 07 branch",
        )

        self.assertEqual(sub.status, "PENDING_APPROVAL")
        self.assertEqual(sub.provider, "BANK_TRANSFER")
        self.assertEqual(sub.amount_lkr, 2500.0)
        self.assertFalse(sub.is_currently_active())

        # Verify payments and bank slip are attached
        self.assertEqual(len(sub.payments), 1)
        payment = sub.payments[0]
        self.assertEqual(payment.status, "PENDING")
        self.assertEqual(payment.amount_minor, 250000)
        self.assertIsNotNone(payment.bank_slip)
        self.assertEqual(payment.bank_slip.review_status, "PENDING")
        self.assertEqual(payment.bank_slip.bank_name, "Bank of Ceylon")
        self.assertEqual(payment.bank_slip.deposit_reference, "CDM-998877")

    async def test_repository_approval_and_rejection_updates_linked_payment(self) -> None:
        """Verify approve/reject updates UserSubscription, Payment, and BankTransferSlip."""
        mock_session = AsyncMock()
        now = datetime.now(timezone.utc)

        # Build existing mock hierarchy
        sub = UserSubscription(
            id="sub_test_approval",
            user_id="user_123",
            plan_id="COMBINED_PRO_MONTHLY",
            status="PENDING_APPROVAL",
            provider="BANK_TRANSFER",
            starts_at=now,
        )
        payment = Payment(
            id="pay_test_01",
            subscription_id="sub_test_approval",
            user_id="user_123",
            method="BANK_TRANSFER",
            status="PENDING",
            amount_minor=250000,
        )
        slip = BankTransferSlip(
            payment_id="pay_test_01",
            slip_image_url="https://storage/slip.jpg",
            review_status="PENDING",
        )
        payment.bank_slip = slip
        sub.payments = [payment]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sub
        mock_session.execute.return_value = mock_result

        repo = SubscriptionRepository(mock_session)

        # 1. Test Approval
        approved_sub = await repo.approve_subscription(
            subscription_id="sub_test_approval",
            admin_uid="admin_01",
            duration_days=30,
            admin_notes="BOC slip verified with bank statement",
        )
        self.assertIsNotNone(approved_sub)
        self.assertEqual(approved_sub.status, "ACTIVE")
        self.assertTrue(approved_sub.is_currently_active())
        self.assertEqual(payment.status, "COMPLETED")
        self.assertEqual(slip.review_status, "APPROVED")
        self.assertEqual(slip.reviewed_by, "admin_01")
        self.assertEqual(slip.admin_feedback, "BOC slip verified with bank statement")

        # 2. Test Rejection
        sub.status = "PENDING_APPROVAL"
        payment.status = "PENDING"
        slip.review_status = "PENDING"

        rejected_sub = await repo.reject_subscription(
            subscription_id="sub_test_approval",
            admin_uid="admin_01",
            rejection_reason="Unclear photo, please upload again",
        )
        self.assertIsNotNone(rejected_sub)
        self.assertEqual(rejected_sub.status, "REJECTED")
        self.assertFalse(rejected_sub.is_currently_active())
        self.assertEqual(payment.status, "FAILED")
        self.assertEqual(slip.review_status, "REJECTED")
        self.assertEqual(slip.admin_feedback, "Unclear photo, please upload again")

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

    def test_list_plans_endpoint_strips_internal_timestamps(self) -> None:
        """Verify GET /api/v1/subscriptions/plans returns clean models without audit fields."""
        mock_session = AsyncMock()
        mock_result = MagicMock()

        plan1 = SubscriptionPlan(
            id="plan_01",
            code="COMBINED_PRO_MONTHLY",
            name_si="සංයුක්ත ගණිතය මාසික සාමාජිකත්වය",
            name_en="Combined Maths Pro Monthly",
            description_si="දින 30ක පූර්ණ ප්‍රවේශය",
            interval="MONTH",
            duration_days=30,
            display_order=1,
            is_active=True,
            features_si="සියලුම සටහන් සහ අභ්‍යාස",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        price1 = PlanPrice(
            id="prc_01",
            plan_id="plan_01",
            currency="LKR",
            amount_minor=250000,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        plan1.prices = [price1]

        mock_result.scalars.return_value.all.return_value = [plan1]
        mock_session.execute.return_value = mock_result

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)
        response = client.get("/api/v1/subscriptions/plans")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)

        first_plan = data[0]
        self.assertEqual(first_plan["code"], "COMBINED_PRO_MONTHLY")
        self.assertEqual(first_plan["name_si"], "සංයුක්ත ගණිතය මාසික සාමාජිකත්වය")
        self.assertEqual(len(first_plan["prices"]), 1)
        self.assertEqual(first_plan["prices"][0]["amount_minor"], 250000)
        self.assertEqual(first_plan["prices"][0]["amount_lkr"], 2500.0)

        # Verify internal database audit timestamps are NOT exposed to the client
        self.assertNotIn("created_at", first_plan)
        self.assertNotIn("updated_at", first_plan)
        self.assertNotIn("created_at", first_plan["prices"][0])

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

    def test_admin_endpoints_block_standard_users(self) -> None:
        standard_user = {"uid": "usr_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = {"uid": "usr_student", "role": "USER"}
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

        client = TestClient(app)
        # Attempt to access admin pending list as a normal student -> 403 Forbidden
        response = client.get("/api/v1/subscriptions/admin/pending")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Insufficient privileges", response.json()["detail"])

        # Attempt to approve subscription as a normal student -> 403 Forbidden
        response_approve = client.post(
            "/api/v1/subscriptions/admin/sub_123/approve",
            json={"duration_days": 30},
        )
        self.assertEqual(response_approve.status_code, 403)
        self.assertIn("Insufficient privileges", response_approve.json()["detail"])


if __name__ == "__main__":
    unittest.main()
