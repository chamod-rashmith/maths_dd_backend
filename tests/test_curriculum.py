"""
Unit tests for Curriculum (Subjects & Syllabus Lessons) endpoints and RBAC security.
Verifies hierarchical sub-lessons, parent lesson filtering, and admin CRUD protection.
"""

import unittest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.api.deps import (
    get_current_user,
    get_curriculum_service,
    get_user_repository,
)
from app.main import app
from app.services.curriculum_service import CurriculumService


class TestCurriculumFeature(unittest.TestCase):
    """Tests curriculum retrieval, hierarchical sub-lessons, and admin CRUD protection."""

    def setUp(self) -> None:
        self.mock_service = AsyncMock(spec=CurriculumService)
        app.dependency_overrides[get_curriculum_service] = lambda: self.mock_service

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_list_subjects(self) -> None:
        self.mock_service.list_subjects.return_value = [
            {
                "id": "sub_pmat",
                "name": "Pure Mathematics",
                "sinhala_name": "ශුද්ධ ගණිතය",
                "code": "PMAT",
                "order_index": 1,
                "description": "G.C.E. A/L Pure Mathematics",
            },
            {
                "id": "sub_amat",
                "name": "Applied Mathematics",
                "sinhala_name": "ව්‍යවහාරික ගණිතය",
                "code": "AMAT",
                "order_index": 2,
                "description": "G.C.E. A/L Applied Mathematics",
            },
        ]
        client = TestClient(app)
        response = client.get("/api/v1/curriculum/subjects")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["code"], "PMAT")
        self.assertEqual(data[1]["code"], "AMAT")

    def test_list_lessons(self) -> None:
        self.mock_service.list_lessons.return_value = [
            {
                "id": "les_trig",
                "subject_id": "sub_pmat",
                "parent_lesson_id": None,
                "title": "Trigonometry",
                "sinhala_title": "ත්‍රිකෝණමිතිය",
                "order_index": 1,
                "description": "Ratios, Identities, and General Solutions",
                "question_count": 45,
                "premium_count": 10,
            }
        ]
        client = TestClient(app)
        response = client.get("/api/v1/curriculum/lessons?subject_code=PMAT")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Trigonometry")
        self.assertIsNone(data[0]["parent_lesson_id"])

    def test_list_sub_lessons_hierarchy_filter(self) -> None:
        """Verifies filtering sub-lessons by parent_lesson_id query parameter."""
        self.mock_service.list_lessons.return_value = [
            {
                "id": "les_trig_01",
                "subject_id": "sub_pmat",
                "parent_lesson_id": "les_trig",
                "title": "Trigonometric Ratios",
                "sinhala_title": "ත්‍රිකෝණමිතික අනුපාත",
                "order_index": 1,
                "description": "Sin, Cos, Tan formulas and identities",
                "question_count": 15,
                "premium_count": 2,
            },
            {
                "id": "les_trig_02",
                "subject_id": "sub_pmat",
                "parent_lesson_id": "les_trig",
                "title": "General Solutions",
                "sinhala_title": "සාමාන්‍ය විසඳුම්",
                "order_index": 2,
                "description": "Solving trig equations",
                "question_count": 20,
                "premium_count": 5,
            },
        ]
        client = TestClient(app)
        response = client.get("/api/v1/curriculum/lessons?parent_lesson_id=les_trig")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["parent_lesson_id"], "les_trig")
        self.assertEqual(data[1]["parent_lesson_id"], "les_trig")
        self.assertEqual(data[0]["sinhala_title"], "ත්‍රිකෝණමිතික අනුපාත")

    def test_add_sub_lesson_allows_admin(self) -> None:
        """Verifies admin can create a sub-lesson linked to a parent unit."""
        admin_user = {"uid": "admin_001", "email": "admin@mathsdd.lk", "role": "ADMIN"}
        app.dependency_overrides[get_current_user] = lambda: admin_user
        self.mock_service.upsert_lesson.return_value = {
            "id": "les_trig_01",
            "subject_id": "sub_pmat",
            "parent_lesson_id": "les_trig",
            "title": "Trigonometric Ratios",
            "sinhala_title": "ත්‍රිකෝණමිතික අනුපාත",
            "order_index": 1,
            "description": "Subtopic 1",
            "question_count": 0,
            "premium_count": 0,
        }

        client = TestClient(app)
        payload = {
            "subject_id": "sub_pmat",
            "parent_lesson_id": "les_trig",
            "title": "Trigonometric Ratios",
            "sinhala_title": "ත්‍රිකෝණමිතික අනුපාත",
            "order_index": 1,
        }
        response = client.post("/api/v1/curriculum/lessons", json=payload)
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertEqual(res_data["id"], "les_trig_01")
        self.assertEqual(res_data["parent_lesson_id"], "les_trig")

    def test_add_subject_blocks_standard_user(self) -> None:
        standard_user = {"uid": "usr_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = standard_user
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

        client = TestClient(app)
        payload = {
            "name": "Higher Mathematics",
            "code": "HMAT",
            "order_index": 3,
        }
        response = client.post("/api/v1/curriculum/subjects", json=payload)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Insufficient privileges", response.json()["detail"])

    def test_add_subject_allows_admin(self) -> None:
        admin_user = {"uid": "admin_001", "email": "admin@mathsdd.lk", "role": "ADMIN"}
        app.dependency_overrides[get_current_user] = lambda: admin_user
        self.mock_service.upsert_subject.return_value = {
            "id": "sub_new",
            "name": "Higher Mathematics",
            "code": "HMAT",
            "order_index": 3,
            "description": None,
            "sinhala_name": None,
        }

        client = TestClient(app)
        payload = {
            "name": "Higher Mathematics",
            "code": "HMAT",
            "order_index": 3,
        }
        response = client.post("/api/v1/curriculum/subjects", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["code"], "HMAT")

    def test_delete_lesson_blocks_standard_user(self) -> None:
        standard_user = {"uid": "usr_student", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = standard_user
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

        client = TestClient(app)
        response = client.delete("/api/v1/curriculum/lessons/les_trig")
        self.assertEqual(response.status_code, 403)

    def test_account_audit_role_blocked_from_content_mutations(self) -> None:
        """Verifies ACCOUNT_AUDIT role cannot add/delete curriculum lessons or subjects."""
        auditor_user = {"uid": "usr_audit_01", "email": "audit@mathsdd.lk", "role": "ACCOUNT_AUDIT"}
        app.dependency_overrides[get_current_user] = lambda: auditor_user
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_uid.return_value = auditor_user
        app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

        client = TestClient(app)
        response = client.delete("/api/v1/curriculum/lessons/les_trig")
        self.assertEqual(response.status_code, 403)
        self.assertIn("ADMIN or EDITOR role is required", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
