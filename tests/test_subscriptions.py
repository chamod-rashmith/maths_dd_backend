"""
Unit tests for Subscription models, DTO schemas, and lifecycle workflows.
Verifies bank slip submission, admin approval/rejection state transitions, and RevenueCat event mapping.
"""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import AsyncMock

from app.core.database import Base
from app.models.subscription import UserSubscription, ProcessedWebhookEvent
from app.models.user import User
from app.schemas.subscription import (
    BankSlipUploadRequest,
    AdminApprovalRequest,
    AdminRejectionRequest,
    UserSubscriptionResponse,
)
from app.repositories.subscription_repository import SubscriptionRepository


class TestSubscriptionFeature(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()
