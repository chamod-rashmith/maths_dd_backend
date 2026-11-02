"""
Unit tests for Study Notes catalog, details retrieval, and admin CRUD RBAC protection.
"""

import unittest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.api.deps import (
    get_current_user,
    get_study_note_service,
    get_user_repository,
)
from app.main import app
from app.services.study_note_service import StudyNoteService


class TestStudyNotesFeature(unittest.TestCase):
    """Tests the study notes listing, on-demand detail loading, and admin write authorization."""

    def setUp(self) -> None:
        self.mock_service = AsyncMock(spec=StudyNoteService)
        app.dependency_overrides[get_study_note_service] = lambda: self.mock_service

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_list_study_notes(self) -> None:
        self.mock_service.list_notes.return_value = [
            {
                "id": "note_trig_01",
                "title": "Trigonometric Formula Cheatsheet",
                "description": "Essential double-angle and compound-angle identities",
                "subject_id": "sub_pmat",
                "lesson_id": "les_trig",
                "content_type": "pdf",
                "is_premium": False,
                "order_index": 1,
                "author": "Maths DD Editorial",
            }
        ]
        client = TestClient(app)
        response = client.get("/api/v1/study-notes?lesson_id=les_trig")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "note_trig_01")
        self.assertEqual(data[0]["content_type"], "pdf")

    def test_get_study_note_detail(self) -> None:
        self.mock_service.get_note_by_id.return_value = {
            "id": "note_trig_01",
            "title": "Trigonometric Formula Cheatsheet",
            "description": "Essential double-angle and compound-angle identities",
            "subject_id": "sub_pmat",
            "lesson_id": "les_trig",
            "content_text": None,
            "pdf_url": "https://storage.googleapis.com/mathsdd-notes/trig.pdf?signed=1",
            "is_premium": False,
            "order_index": 1,
            "author": "Maths DD Editorial",
        }
        client = TestClient(app)
        response = client.get("/api/v1/study-notes/note_trig_01")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "note_trig_01")
        self.assertIn("signed=1", response.json()["pdf_url"])

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
            "content_text": r"$\frac{d}{dx} \sin(x) = \cos(x)$",
        }
        response = client.post("/api/v1/study-notes", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], "note_new_01")

    def test_delete_study_note_blocks_standard_user(self) -> None:
        standard_user = {"uid": "usr_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = standard_user
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

        client = TestClient(app)
        response = client.delete("/api/v1/study-notes/note_trig_01")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
