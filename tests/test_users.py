"""
Unit tests for User Profile and Demographic Authentication Sync endpoints.
Verifies normalized StudentProfile fields (exam_year, attempt_number, exam_district_id).
"""

from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_user_service
from app.main import app
from app.services.user_service import UserService


class TestUserFeature(unittest.TestCase):
    """Tests the /users/me and /users/sync endpoints."""

    def setUp(self) -> None:
        self.mock_service = AsyncMock(spec=UserService)
        app.dependency_overrides[get_user_service] = lambda: self.mock_service

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_get_my_profile_unauthorized(self) -> None:
        client = TestClient(app)
        response = client.get("/api/v1/users/me")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authorization header is required", response.json()["detail"])

    def test_get_my_profile_success(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "usr_student_001",
            "email": "student@mathsdd.lk",
            "name": "Kamal Perera",
        }
        now = datetime.now(timezone.utc)
        self.mock_service.get_my_profile.return_value = {
            "uid": "usr_student_001",
            "email": "student@mathsdd.lk",
            "name": "Kamal Perera",
            "role": "USER",
            "avatar_url": "https://lh3.googleusercontent.com/photo.jpg",
            "school_name": "Royal College",
            "district_id": 1,
            "district": {
                "id": 1,
                "code": "COLOMBO",
                "name_en": "Colombo",
                "name_si": "කොළඹ",
                "name_ta": "கொழும்பு",
                "province": "WESTERN",
                "display_order": 1,
            },
            "exam_district_id": 1,
            "exam_year": 2026,
            "attempt_number": 1,
            "medium": "SINHALA",
            "stream": "PHYSICAL_SCIENCE",
            "grade": "GRADE_13",
            "attempt": "FIRST",
            "xp": 150,
            "streak_count": 5,
            "questions_solved": 24,
            "is_premium": True,
            "active_subscription": {
                "id": "sub_01",
                "plan_id": "COMBINED_PRO_MONTHLY",
                "status": "ACTIVE",
                "provider": "REVENUECAT",
                "starts_at": now,
            },
        }

        client = TestClient(app)
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer fake_token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["uid"], "usr_student_001")
        self.assertNotIn("district_id", data)
        self.assertNotIn("exam_district_id", data)
        self.assertNotIn("accuracy_rate", data)
        self.assertEqual(data["district"]["id"], 1)
        self.assertEqual(data["district"]["code"], "COLOMBO")
        self.assertEqual(data["exam_year"], 2026)
        self.assertEqual(data["attempt_number"], 1)
        self.assertEqual(data["medium"], "SINHALA")
        self.assertEqual(data["stream"], "PHYSICAL_SCIENCE")
        self.assertEqual(data["xp"], 150)
        self.assertTrue(data["is_premium"])

    def test_sync_user_profile_success(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "usr_student_002",
            "email": "nimal@mathsdd.lk",
            "name": "Nimal Silva",
            "email_verified": True,
        }
        self.mock_service.sync_profile.return_value = {
            "uid": "usr_student_002",
            "email": "nimal@mathsdd.lk",
            "name": "Nimal Silva",
            "role": "USER",
            "avatar_url": None,
            "school_name": "Ananda College",
            "district": {
                "id": 1,
                "code": "COLOMBO",
                "name_en": "Colombo",
                "name_si": "කොළඹ",
                "name_ta": "கொழும்பு",
                "province": "WESTERN",
            },
            "exam_year": 2026,
            "attempt_number": 1,
            "medium": "SINHALA",
            "stream": "PHYSICAL_SCIENCE",
            "grade": "GRADE_12",
            "xp": 0,
            "streak_count": 0,
            "questions_solved": 0,
            "is_premium": False,
            "active_subscription": None,
        }

        payload = {
            "name": "Nimal Silva",
            "school_name": "Ananda College",
            "district_id": 1,
            "stream": "PHYSICAL_SCIENCE",
            "grade": "GRADE_12",
            "attempt": "FIRST",
            "exam_year": 2026,
            "attempt_number": 1,
            "exam_district_id": 1,
        }

        client = TestClient(app)
        response = client.post(
            "/api/v1/users/sync",
            json=payload,
            headers={"Authorization": "Bearer fake_token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["school_name"], "Ananda College")
        self.assertNotIn("district_id", data)
        self.assertNotIn("exam_district_id", data)
        self.assertEqual(data["district"]["id"], 1)
        self.assertEqual(data["district"]["code"], "COLOMBO")
        self.assertEqual(data["exam_year"], 2026)
        self.assertEqual(data["attempt_number"], 1)
        self.assertEqual(data["grade"], "GRADE_12")


if __name__ == "__main__":
    unittest.main()
