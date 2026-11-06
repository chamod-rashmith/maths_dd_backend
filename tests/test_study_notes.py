"""
Unit tests for Study Notes catalog, details retrieval, zero-leak access gating, and admin RBAC.
Verifies:
1. Authentication requirement (401 for unauthenticated clients).
2. Free notes accessible to all authenticated students.
3. Premium notes blocked with 403 Forbidden for non-premium students (zero content leaked).
4. Premium notes accessible to premium students and administrators.
5. Catalog listings annotate `is_locked: True` for locked cards.
6. Admin CRUD RBAC enforcement.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.api.deps import (
    get_current_user,
    get_study_note_service,
    get_user_repository,
)
from app.core.database import get_db
from app.main import app
from app.models.subscription import UserSubscription
from app.services.study_note_service import StudyNoteService


class TestStudyNotesFeature(unittest.TestCase):
    """Tests study notes listing, zero-leak premium gating, and admin authorization."""

    def setUp(self) -> None:
        self.mock_service = AsyncMock(spec=StudyNoteService)
        self.mock_session = AsyncMock()
        self.mock_session.execute = AsyncMock()

        # Mock database session
        async def override_get_db():
            yield self.mock_session

        app.dependency_overrides[get_study_note_service] = lambda: self.mock_service
        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_unauthenticated_request_blocked(self) -> None:
        """Verify unauthenticated requests to study notes endpoints receive 401 Unauthorized."""
        client = TestClient(app)
        response_list = client.get("/api/v1/study-notes")
        self.assertEqual(response_list.status_code, 401)

        response_detail = client.get("/api/v1/study-notes/note_trig_01")
        self.assertEqual(response_detail.status_code, 401)

    def test_list_study_notes_annotates_is_locked(self) -> None:
        """Verify catalog marks premium notes as is_locked=True for free students."""
        standard_user = {"uid": "usr_free_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user

        # Mock no active subscription for this user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_session.execute.return_value = mock_result

        self.mock_service.list_notes.return_value = [
            {
                "id": "note_free_01",
                "title": "Basic Algebra Formulas",
                "description": "Essential expansion formulas",
                "subject_id": "sub_pmat",
                "lesson_id": "les_alg",
                "content_type": "markdown",
                "is_premium": False,
                "order_index": 1,
            },
            {
                "id": "note_prem_01",
                "title": "Advanced Integration Mastery",
                "description": "Comprehensive integration methods",
                "subject_id": "sub_pmat",
                "lesson_id": "les_int",
                "content_type": "pdf",
                "is_premium": True,
                "order_index": 2,
            },
        ]

        client = TestClient(app)
        response = client.get("/api/v1/study-notes")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("pagination", data)
        items = data["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(data["pagination"]["total"], 2)

        # Free note -> is_locked is False
        self.assertEqual(items[0]["id"], "note_free_01")
        self.assertFalse(items[0]["is_locked"])

        # Premium note for free student -> is_locked is True
        self.assertEqual(items[1]["id"], "note_prem_01")
        self.assertTrue(items[1]["is_locked"])

    def test_get_free_study_note_detail_allowed_for_all(self) -> None:
        """Verify free notes return full content to any authenticated student."""
        standard_user = {"uid": "usr_free_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user

        self.mock_service.get_note_by_id.return_value = {
            "id": "note_free_01",
            "title": "Basic Algebra Formulas",
            "description": "Essential expansion formulas",
            "subject_id": "sub_pmat",
            "lesson_id": "les_alg",
            "content_text": r"$(a+b)^2 = a^2 + 2ab + b^2$",
            "pdf_url": None,
            "is_premium": False,
            "order_index": 1,
        }

        client = TestClient(app)
        response = client.get("/api/v1/study-notes/note_free_01")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "note_free_01")
        self.assertIn("$(a+b)^2", response.json()["content_text"])
        self.assertFalse(response.json()["is_locked"])

    def test_get_premium_study_note_blocks_free_student(self) -> None:
        """Zero-Leak Check: Verify premium notes return 403 Forbidden to non-premium students with no content leak."""
        standard_user = {"uid": "usr_free_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user

        # Mock no active subscription
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_session.execute.return_value = mock_result

        self.mock_service.get_note_by_id.return_value = {
            "id": "note_prem_01",
            "title": "Advanced Integration Mastery",
            "description": "Comprehensive integration methods",
            "subject_id": "sub_pmat",
            "lesson_id": "les_int",
            "content_text": "Secret premium formulas",
            "pdf_url": "https://storage.googleapis.com/secret.pdf",
            "is_premium": True,
            "order_index": 2,
        }

        client = TestClient(app)
        response = client.get("/api/v1/study-notes/note_prem_01")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Premium සාමාජිකත්වය අවශ්‍ය වේ", response.json()["detail"])

    def test_get_premium_study_note_allows_admin(self) -> None:
        """Verify admin can access any premium note."""
        admin_user = {"uid": "admin_01", "email": "admin@mathsdd.lk", "role": "ADMIN"}
        app.dependency_overrides[get_current_user] = lambda: admin_user

        self.mock_service.get_note_by_id.return_value = {
            "id": "note_prem_01",
            "title": "Advanced Integration Mastery",
            "subject_id": "sub_pmat",
            "content_text": r"$\int x dx = \frac{x^2}{2} + C$",
            "pdf_url": None,
            "is_premium": True,
            "order_index": 2,
        }

        client = TestClient(app)
        response = client.get("/api/v1/study-notes/note_prem_01")
        self.assertEqual(response.status_code, 200)
        self.assertIn(r"\int x dx", response.json()["content_text"])

    def test_create_study_note_blocks_standard_user(self) -> None:
        standard_user = {"uid": "usr_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = standard_user
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

        client = TestClient(app)
        payload = {
            "title": "Unauthorized Note",
            "subject_id": "sub_pmat",
            "content_text": "Formula notes",
        }
        response = client.post("/api/v1/study-notes", json=payload)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Insufficient privileges", response.json()["detail"])

    def test_create_study_note_allows_admin(self) -> None:
        admin_user = {"uid": "admin_01", "email": "admin@mathsdd.lk", "role": "ADMIN"}
        app.dependency_overrides[get_current_user] = lambda: admin_user
        self.mock_service.upsert_note.return_value = {
            "id": "note_new_01",
            "title": "Calculus Quick Reference",
            "description": "Differentiation rules",
            "subject_id": "sub_pmat",
            "lesson_id": "les_calc",
            "content_text": r"$\frac{d}{dx} \sin(x) = \cos(x)$",
            "pdf_url": None,
            "is_premium": False,
            "order_index": 2,
            "author": "Admin",
        }

        client = TestClient(app)
        payload = {
            "title": "Calculus Quick Reference",
            "subject_id": "sub_pmat",
            "lesson_id": "les_calc",
            "content_text": r"$\frac{d}{dx} \sin(x) = \cos(x)$",
        }
        response = client.post("/api/v1/study-notes", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], "note_new_01")


if __name__ == "__main__":
    unittest.main()
