"""
Unit & Integration tests for Ring 4 Immutable Admin Audit Logs (`admin_audit_logs` table).
Verifies:
1. Automatic recording of every privileged action across all staff endpoints:
   - Bank Slip Approve, Reject, and Stale Subscription Expiration Sweep
   - Question Upsert and Delete
   - Study Note Upsert and Delete
   - Curriculum Subject & Lesson Upsert and Delete
   - Admin Security TOTP Setup, TOTP Verify, and Sudo Session Elevation
2. Capture of actor UID, email, role, client IP (`X-Forwarded-For` / `X-Real-IP` / `client.host`),
   User-Agent, HTTP method/path, resource type/ID, JSON details, and UTC timestamp.
3. Strict Immutability Guarantees (100% SQLAlchemy 2.0 ORM):
   - Updating an existing `AdminAuditLog` record raises `PermissionDeniedError`.
   - Deleting an existing `AdminAuditLog` record raises `PermissionDeniedError`.
   - Bulk `update(AdminAuditLog)` and `delete(AdminAuditLog)` statements raise `PermissionDeniedError`.
4. `GET /api/v1/admin/security/audit-logs` paginated querying, multi-field filtering, RBAC protection,
   and SQL injection immunity.
"""

from datetime import datetime, timezone
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.core.totp import generate_totp_code
from app.domain.exceptions import PermissionDeniedError
from app.main import app
from app.models.admin_audit_log import AdminAuditLog
from app.models.question import Question
from app.models.study_note import StudyNote
from app.models.subject import Subject
from app.models.subscription import BankTransferSlip, Payment, UserSubscription
from app.models.user import User


class TestImmutableAdminAuditLogs(unittest.IsolatedAsyncioTestCase):
    """Verifies Ring 4 Immutable Admin Audit Log creation, querying, and tamper-resistance."""

    async def asyncSetUp(self) -> None:
        app.dependency_overrides.clear()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        now = datetime.now(timezone.utc)
        async with self.session_factory() as session:
            session.add_all(
                [
                    User(uid="admin_001", email="admin@mathsdd.lk", name="Super Admin", role="ADMIN"),
                    User(uid="editor_001", email="editor@mathsdd.lk", name="Content Editor", role="EDITOR"),
                    User(uid="auditor_001", email="audit@mathsdd.lk", name="Finance Auditor", role="ACCOUNT_AUDIT"),
                    User(uid="student_001", email="student@mathsdd.lk", name="Kasun Student", role="USER"),
                    Subject(id="subj_pmat", name="Pure Mathematics", code="PMAT", order_index=1),
                ]
            )
            session.add(
                Question(
                    id="q_to_delete",
                    title="Sample Question",
                    subject_id="subj_pmat",
                    content_text="Solve x^2 = 4",
                )
            )
            session.add(
                StudyNote(
                    id="note_to_delete",
                    title="Sample Note",
                    subject_id="subj_pmat",
                    content_text="Calculus notes",
                )
            )
            sub1 = UserSubscription(
                id="sub_slip_approve",
                user_id="student_001",
                plan_id="COMBINED_PRO_MONTHLY",
                status="PENDING_APPROVAL",
                provider="BANK_TRANSFER",
                amount_lkr=1500.0,
                starts_at=now,
            )
            pay1 = Payment(
                id="pay_slip_1",
                subscription_id="sub_slip_approve",
                user_id="student_001",
                method="BANK_TRANSFER",
                status="PENDING",
                amount_minor=150000,
            )
            slip1 = BankTransferSlip(
                payment_id="pay_slip_1",
                slip_image_url="https://storage.googleapis.com/slips/1.jpg",
                review_status="PENDING",
            )
            pay1.bank_slip = slip1
            sub1.payments = [pay1]

            sub2 = UserSubscription(
                id="sub_slip_reject",
                user_id="student_001",
                plan_id="COMBINED_PRO_MONTHLY",
                status="PENDING_APPROVAL",
                provider="BANK_TRANSFER",
                amount_lkr=1500.0,
                starts_at=now,
            )
            session.add_all([sub1, sub2])
            await session.commit()

        async def override_get_db():
            async with self.session_factory() as session:
                yield session
                await session.commit()

        app.dependency_overrides[get_db] = override_get_db

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_bank_slip_approve_reject_and_expire_sweep_recorded(self) -> None:
        """Verifies ACCOUNT_AUDIT and ADMIN subscription actions record immutable audit logs with IP."""
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "auditor_001",
            "email": "audit@mathsdd.lk",
            "role": "ACCOUNT_AUDIT",
        }
        client = TestClient(app)

        # 1. Approve bank slip with X-Forwarded-For IP header
        approve_res = client.post(
            "/api/v1/subscriptions/admin/sub_slip_approve/approve",
            json={"duration_days": 30, "admin_notes": "BOC receipt verified"},
            headers={"X-Forwarded-For": "203.94.72.10, 10.0.0.1", "User-Agent": "MathsDD-AdminPortal/1.0"},
        )
        self.assertEqual(approve_res.status_code, 200)

        # 2. Reject bank slip with X-Real-IP header
        reject_res = client.post(
            "/api/v1/subscriptions/admin/sub_slip_reject/reject",
            json={"rejection_reason": "Blurry slip image"},
            headers={"X-Real-IP": "112.134.55.88"},
        )
        self.assertEqual(reject_res.status_code, 200)

        # 3. Run maintenance expire-stale sweep as ADMIN
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "admin_001",
            "email": "admin@mathsdd.lk",
            "role": "ADMIN",
        }
        sweep_res = client.post(
            "/api/v1/subscriptions/admin/maintenance/expire-stale",
            headers={"X-Forwarded-For": "203.94.72.99"},
        )
        self.assertEqual(sweep_res.status_code, 200)

        # 4. Query audit logs via GET /api/v1/admin/security/audit-logs
        logs_res = client.get("/api/v1/admin/security/audit-logs")
        self.assertEqual(logs_res.status_code, 200)
        payload = logs_res.json()
        self.assertEqual(payload["pagination"]["total"], 3)

        actions_by_action = {item["action"]: item for item in payload["items"]}
        approve_log = actions_by_action["BANK_SLIP_APPROVED"]
        self.assertEqual(approve_log["actor_uid"], "auditor_001")
        self.assertEqual(approve_log["actor_role"], "ACCOUNT_AUDIT")
        self.assertEqual(approve_log["resource_type"], "SUBSCRIPTION")
        self.assertEqual(approve_log["resource_id"], "sub_slip_approve")
        self.assertEqual(approve_log["ip_address"], "203.94.72.10")
        self.assertEqual(approve_log["user_agent"], "MathsDD-AdminPortal/1.0")
        self.assertEqual(approve_log["request_method"], "POST")
        self.assertEqual(approve_log["details"]["duration_days"], 30)
        self.assertEqual(approve_log["details"]["admin_notes"], "BOC receipt verified")

        reject_log = actions_by_action["BANK_SLIP_REJECTED"]
        self.assertEqual(reject_log["ip_address"], "112.134.55.88")
        self.assertEqual(reject_log["details"]["rejection_reason"], "Blurry slip image")

        sweep_log = actions_by_action["SUBSCRIPTIONS_EXPIRE_STALE"]
        self.assertEqual(sweep_log["actor_uid"], "admin_001")
        self.assertEqual(sweep_log["ip_address"], "203.94.72.99")

    async def test_content_and_curriculum_crud_recorded_in_audit_log(self) -> None:
        """Verifies Question, Study Note, Subject, and Lesson Upsert & Delete actions are audited."""
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "editor_001",
            "email": "editor@mathsdd.lk",
            "role": "EDITOR",
        }
        client = TestClient(app)

        # 1. Upsert Subject & Lesson
        sub_res = client.post(
            "/api/v1/curriculum/subjects",
            json={"id": "subj_amat", "name": "Applied Mathematics", "code": "AMAT", "order_index": 2},
            headers={"X-Forwarded-For": "175.157.10.22"},
        )
        self.assertEqual(sub_res.status_code, 201)

        les_res = client.post(
            "/api/v1/curriculum/lessons",
            json={"id": "les_statics", "subject_id": "subj_amat", "title": "Statics", "order_index": 1},
            headers={"X-Forwarded-For": "175.157.10.22"},
        )
        self.assertEqual(les_res.status_code, 201)

        # 2. Upsert Question & Study Note
        q_res = client.post(
            "/api/v1/questions",
            json={
                "id": "q_created_1",
                "title": "Vectors Question",
                "subject_id": "subj_amat",
                "content_text": "Find the resultant force.",
                "solution_text": "R = F1 + F2",
            },
            headers={"X-Forwarded-For": "175.157.10.22"},
        )
        self.assertEqual(q_res.status_code, 201)

        note_res = client.post(
            "/api/v1/study-notes",
            json={
                "id": "note_created_1",
                "title": "Statics Summary",
                "subject_id": "subj_amat",
                "content_text": "Equilibrium conditions",
            },
            headers={"X-Forwarded-For": "175.157.10.22"},
        )
        self.assertEqual(note_res.status_code, 201)

        # 3. Delete Question, Study Note, Lesson, and Subject
        self.assertEqual(client.delete("/api/v1/questions/q_to_delete").status_code, 200)
        self.assertEqual(client.delete("/api/v1/study-notes/note_to_delete").status_code, 200)
        self.assertEqual(client.delete("/api/v1/curriculum/lessons/les_statics").status_code, 200)
        self.assertEqual(client.delete("/api/v1/curriculum/subjects/subj_amat").status_code, 200)

        # Verify RBAC: EDITOR and USER cannot read audit logs
        self.assertEqual(client.get("/api/v1/admin/security/audit-logs").status_code, 403)
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "student_001",
            "email": "student@mathsdd.lk",
            "role": "USER",
        }
        self.assertEqual(client.get("/api/v1/admin/security/audit-logs").status_code, 403)

        # Switch to ADMIN to inspect and filter recorded logs
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "admin_001",
            "email": "admin@mathsdd.lk",
            "role": "ADMIN",
        }
        admin_audit_res = client.get("/api/v1/admin/security/audit-logs?actor_uid=editor_001")
        self.assertEqual(admin_audit_res.status_code, 200)
        items = admin_audit_res.json()["items"]
        self.assertEqual(len(items), 8)
        recorded_actions = {i["action"] for i in items}
        self.assertEqual(
            recorded_actions,
            {
                "SUBJECT_UPSERTED",
                "LESSON_UPSERTED",
                "QUESTION_UPSERTED",
                "STUDY_NOTE_UPSERTED",
                "QUESTION_DELETED",
                "STUDY_NOTE_DELETED",
                "LESSON_DELETED",
                "SUBJECT_DELETED",
            },
        )

        # Test filtering by action and resource_type
        q_del_res = client.get(
            "/api/v1/admin/security/audit-logs",
            params={"action": "QUESTION_DELETED", "resource_type": "QUESTION", "resource_id": "q_to_delete"},
        )
        self.assertEqual(q_del_res.status_code, 200)
        self.assertEqual(q_del_res.json()["pagination"]["total"], 1)
        self.assertEqual(q_del_res.json()["items"][0]["resource_id"], "q_to_delete")

        # Verify SQL injection string in filter parameters is safely bound as a literal value
        sqli_res = client.get(
            "/api/v1/admin/security/audit-logs",
            params={"actor_uid": "' OR '1'='1", "action": "QUESTION_DELETED; DROP TABLE admin_audit_logs;--"},
        )
        self.assertEqual(sqli_res.status_code, 200)
        self.assertEqual(sqli_res.json()["pagination"]["total"], 0)

    async def test_totp_setup_verify_and_sudo_elevation_audited(self) -> None:
        """Verifies TOTP 2FA setup, verification, and Sudo Mode elevation record security audit logs."""
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "admin_001",
            "email": "admin@mathsdd.lk",
            "role": "ADMIN",
        }
        client = TestClient(app)

        # 1. Initiate TOTP setup
        setup_res = client.post(
            "/api/v1/admin/security/totp/setup",
            headers={"X-Forwarded-For": "203.94.72.50"},
        )
        self.assertEqual(setup_res.status_code, 200)
        setup_payload = setup_res.json()
        secret = setup_payload["secret"]
        recovery_code = setup_payload["recovery_codes"][0]

        # 2. Verify TOTP setup with 6-digit code
        code = generate_totp_code(secret)
        verify_res = client.post(
            "/api/v1/admin/security/totp/verify-setup",
            json={"code": code},
            headers={"X-Forwarded-For": "203.94.72.50"},
        )
        self.assertEqual(verify_res.status_code, 200)

        # 3. Elevate to Sudo session using single-use recovery code
        sudo_res = client.post(
            "/api/v1/admin/security/elevate",
            json={"code": recovery_code},
            headers={"X-Forwarded-For": "203.94.72.50"},
        )
        self.assertEqual(sudo_res.status_code, 200)

        # 4. Verify all 3 security events are recorded in admin_audit_logs
        logs_res = client.get("/api/v1/admin/security/audit-logs?resource_type=ADMIN_TOTP")
        self.assertEqual(logs_res.status_code, 200)
        security_actions = [item["action"] for item in logs_res.json()["items"]]
        self.assertEqual(
            set(security_actions),
            {"ADMIN_TOTP_SETUP_INITIATED", "ADMIN_TOTP_ENABLED", "ADMIN_SESSION_ELEVATED"},
        )

    async def test_immutability_blocks_orm_and_bulk_updates_or_deletes(self) -> None:
        """Verifies that once an AdminAuditLog row is created, it cannot be updated or deleted."""
        async with self.session_factory() as session:
            entry = AdminAuditLog(
                actor_uid="admin_001",
                actor_email="admin@mathsdd.lk",
                actor_role="ADMIN",
                action="QUESTION_DELETED",
                resource_type="QUESTION",
                resource_id="q_999",
                ip_address="127.0.0.1",
            )
            session.add(entry)
            await session.commit()
            entry_id = entry.id

        # 1. Attempt ORM attribute update -> blocked by before_update listener
        async with self.session_factory() as session:
            fetched = (
                await session.execute(select(AdminAuditLog).where(AdminAuditLog.id == entry_id))
            ).scalar_one()
            fetched.action = "FORGED_ACTION"
            with self.assertRaises(PermissionDeniedError):
                await session.flush()
            await session.rollback()

        # 2. Attempt ORM instance delete -> blocked by before_delete listener
        async with self.session_factory() as session:
            fetched = (
                await session.execute(select(AdminAuditLog).where(AdminAuditLog.id == entry_id))
            ).scalar_one()
            await session.delete(fetched)
            with self.assertRaises(PermissionDeniedError):
                await session.flush()
            await session.rollback()

        # 3. Attempt SQLAlchemy bulk update(AdminAuditLog) -> blocked by do_orm_execute listener
        async with self.session_factory() as session:
            with self.assertRaises(PermissionDeniedError):
                await session.execute(
                    update(AdminAuditLog)
                    .where(AdminAuditLog.id == entry_id)
                    .values(action="TAMPERED")
                )

        # 4. Attempt SQLAlchemy bulk delete(AdminAuditLog) -> blocked by do_orm_execute listener
        async with self.session_factory() as session:
            with self.assertRaises(PermissionDeniedError):
                await session.execute(
                    delete(AdminAuditLog).where(AdminAuditLog.id == entry_id)
                )

        # 5. Verify original record remains 100% intact
        async with self.session_factory() as session:
            intact = (
                await session.execute(select(AdminAuditLog).where(AdminAuditLog.id == entry_id))
            ).scalar_one()
            self.assertEqual(intact.action, "QUESTION_DELETED")
            self.assertEqual(intact.resource_id, "q_999")


if __name__ == "__main__":
    unittest.main()
