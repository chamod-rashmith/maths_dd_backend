"""
Unit tests verifying FastAPI application wiring, OpenAPI routes, health probes,
and Clean Architecture Abstract Repository Dependency Injection.
"""

import unittest
from typing import Any, Dict, List, Optional
from fastapi.testclient import TestClient

from app.api.deps import get_curriculum_repository, get_user_repository
from app.core.security import get_current_user
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.user_repository import UserRepository
from app.main import app


class _InMemoryCurriculumRepository(CurriculumRepository):
    """Test double implementing the abstract `CurriculumRepository` contract."""

    async def get_subjects(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "pure_maths",
                "name": "Pure Mathematics",
                "sinhala_name": None,
                "code": "PM",
                "order_index": 1,
                "description": "Algebra and Calculus",
            }
        ]

    async def upsert_subject(
        self,
        subject_id: str,
        name: str,
        sinhala_name: str,
        code: str,
        order_index: int,
        description: str = "",
    ) -> Dict[str, Any]:
        return {
            "id": subject_id,
            "name": name,
            "sinhala_name": sinhala_name,
            "code": code,
            "order_index": order_index,
            "description": description,
        }

    async def delete_subject(self, subject_id: str) -> Dict[str, Any]:
        return {"status": "success", "deleted_id": subject_id}

    async def get_lessons(
        self, subject_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return []

    async def upsert_lesson(
        self,
        lesson_id: str,
        subject_id: str,
        title: str,
        sinhala_title: str,
        order_index: int,
        description: str = "",
    ) -> Dict[str, Any]:
        return {
            "id": lesson_id,
            "subject_id": subject_id,
            "title": title,
            "sinhala_title": sinhala_title,
            "order_index": order_index,
            "description": description,
        }


class _InMemoryUserRepository(UserRepository):
    """Test double implementing the abstract `UserRepository` contract."""

    async def get_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        if uid == "uid_123":
            return {
                "uid": "uid_123",
                "email": "student@mathsdd.lk",
                "name": "Test Student",
                "role": "USER",
            }
        return None

    async def sync_or_create(
        self,
        uid: str,
        email: str,
        name: str,
        avatar_url: Optional[str] = None,
        telephone_no: Optional[str] = None,
        school_name: Optional[str] = None,
        district: Optional[str] = None,
        stream: Optional[str] = None,
        grade: Optional[str] = None,
        attempt: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "uid": uid,
            "email": email,
            "name": name,
            "avatar_url": avatar_url,
            "telephone_no": telephone_no,
            "school_name": school_name,
            "district": district,
            "stream": stream,
            "grade": grade,
            "attempt": attempt,
            "role": "USER",
        }


class TestBackendHealthAndRoutes(unittest.TestCase):
    """Verifies core endpoints, DI overrides, and zero mock/seed endpoints."""

    def setUp(self) -> None:
        app.dependency_overrides.clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "maths_dd_backend")

    def test_seed_endpoint_removed(self) -> None:
        response = self.client.post("/api/seed")
        self.assertEqual(response.status_code, 404)

    def test_v1_routes_registered(self) -> None:
        openapi_paths = set(app.openapi().get("paths", {}).keys())
        expected_paths = {
            "/health",
            "/db-test",
            "/api/v1/users/me",
            "/api/v1/users/sync",
            "/api/v1/curriculum/subjects",
            "/api/v1/curriculum/lessons",
            "/api/v1/questions/recent",
            "/api/v1/questions",
            "/api/v1/study-notes",
            "/api/v1/study-notes/{note_id}",
        }
        self.assertTrue(expected_paths.issubset(openapi_paths))

    def test_abstract_curriculum_repository_di_override(self) -> None:
        app.dependency_overrides[get_curriculum_repository] = (
            lambda: _InMemoryCurriculumRepository()
        )
        response = self.client.get("/api/v1/curriculum/subjects")
        self.assertEqual(response.status_code, 200)
        subjects = response.json()
        self.assertEqual(len(subjects), 1)
        self.assertEqual(subjects[0]["id"], "pure_maths")

    def test_abstract_user_repository_di_override(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "uid_123",
            "email": "student@mathsdd.lk",
        }
        app.dependency_overrides[get_user_repository] = (
            lambda: _InMemoryUserRepository()
        )
        response = self.client.get("/api/v1/users/me")
        self.assertEqual(response.status_code, 200)
        profile = response.json()
        self.assertEqual(profile["uid"], "uid_123")
        self.assertEqual(profile["email"], "student@mathsdd.lk")


if __name__ == "__main__":
    unittest.main()
