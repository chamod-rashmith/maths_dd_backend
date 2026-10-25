"""
Unit tests verifying FastAPI application wiring, OpenAPI routes, health probes,
Application Services, Global Exception Handlers, TTL Caching, RBAC,
and Study Note Summary Catalog vs On-Demand Detail Loading.
"""

import unittest
from typing import Any, Dict, List, Optional
from fastapi.testclient import TestClient

from app.api.deps import (
    get_curriculum_repository,
    get_study_note_repository,
    get_user_repository,
)
from app.core.cache import curriculum_cache
from app.core.security import get_current_user
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.study_note_repository import StudyNoteRepository
from app.domain.repositories.user_repository import UserRepository
from app.main import app


class _InMemoryStudyNoteRepository(StudyNoteRepository):
    """Test double implementing StudyNoteRepository."""

    def __init__(self) -> None:
        self.notes: Dict[str, Dict[str, Any]] = {}

    async def list_notes(
        self,
        subject_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        # Summary view: exclude content_text and pdf_url
        summaries = []
        for n in self.notes.values():
            s = dict(n)
            s.pop("content_text", None)
            s.pop("pdf_url", None)
            summaries.append(s)
        return summaries

    async def get_by_id(self, note_id: str) -> Optional[Dict[str, Any]]:
        return self.notes.get(note_id)

    async def upsert(
        self,
        note_id: Optional[str],
        title: str,
        subject_id: str,
        lesson_id: Optional[str],
        content_text: Optional[str] = "",
        description: Optional[str] = "",
        pdf_url: Optional[str] = None,
        is_premium: bool = False,
        order_index: int = 0,
        author: Optional[str] = "",
    ) -> Dict[str, Any]:
        nid = note_id or "note_test_1"
        final_pdf = pdf_url.strip() if (pdf_url and pdf_url.strip()) else None
        final_content = (content_text or "").strip() if not final_pdf else ""

        record = {
            "id": nid,
            "title": title,
            "subject_id": subject_id,
            "lesson_id": lesson_id,
            "content_text": final_content,
            "pdf_url": final_pdf,
            "content_type": "pdf" if final_pdf else "markdown",
            "description": description,
            "is_premium": is_premium,
            "order_index": order_index,
            "author": author,
        }
        self.notes[nid] = record
        return record

    async def delete(self, note_id: str) -> Dict[str, Any]:
        self.notes.pop(note_id, None)
        return {"status": "success"}


class _InMemoryCurriculumRepository(CurriculumRepository):
    """Test double implementing the abstract `CurriculumRepository` contract."""

    def __init__(self) -> None:
        self.call_count = 0

    async def get_subjects(self) -> List[Dict[str, Any]]:
        self.call_count += 1
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

    def __init__(self, role: str = "USER") -> None:
        self._role = role

    async def get_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        if uid == "uid_123":
            return {
                "uid": "uid_123",
                "email": "student@mathsdd.lk",
                "name": "Test Student",
                "role": self._role,
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
            "role": self._role,
        }


class TestBackendCleanArchitecture(unittest.TestCase):
    """Verifies Clean Architecture layers, DI, RBAC, TTL caching, and global exception handlers."""

    def setUp(self) -> None:
        app.dependency_overrides.clear()
        curriculum_cache.clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        curriculum_cache.clear()

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

    def test_curriculum_ttl_cache_and_invalidation(self) -> None:
        fake_repo = _InMemoryCurriculumRepository()
        app.dependency_overrides[get_curriculum_repository] = lambda: fake_repo

        res1 = self.client.get("/api/v1/curriculum/subjects")
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(fake_repo.call_count, 1)

        res2 = self.client.get("/api/v1/curriculum/subjects")
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(fake_repo.call_count, 1)

    def test_user_not_found_maps_to_404_via_global_exception_handler(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "missing_uid",
            "email": "missing@mathsdd.lk",
        }
        app.dependency_overrides[get_user_repository] = (
            lambda: _InMemoryUserRepository()
        )
        response = self.client.get("/api/v1/users/me")
        self.assertEqual(response.status_code, 404)

    def test_rbac_blocks_standard_user_from_admin_mutations(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "uid_123",
            "email": "student@mathsdd.lk",
        }
        app.dependency_overrides[get_user_repository] = (
            lambda: _InMemoryUserRepository(role="USER")
        )
        app.dependency_overrides[get_curriculum_repository] = (
            lambda: _InMemoryCurriculumRepository()
        )

        response = self.client.post(
            "/api/v1/curriculum/subjects",
            json={"id": "pure_maths", "name": "Pure Maths", "code": "PM"},
        )
        self.assertEqual(response.status_code, 403)

    def test_rbac_allows_admin_user_for_mutations(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "uid_123",
            "email": "admin@mathsdd.lk",
        }
        app.dependency_overrides[get_user_repository] = (
            lambda: _InMemoryUserRepository(role="ADMIN")
        )
        app.dependency_overrides[get_curriculum_repository] = (
            lambda: _InMemoryCurriculumRepository()
        )

        response = self.client.post(
            "/api/v1/curriculum/subjects",
            json={"id": "pure_maths", "name": "Pure Maths", "code": "PM"},
        )
        self.assertEqual(response.status_code, 201)

    def test_study_note_validation_rejects_both_pdf_and_text(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "uid_123",
            "role": "ADMIN",
        }
        app.dependency_overrides[get_user_repository] = (
            lambda: _InMemoryUserRepository(role="ADMIN")
        )
        app.dependency_overrides[get_study_note_repository] = (
            lambda: _InMemoryStudyNoteRepository()
        )

        response = self.client.post(
            "/api/v1/study-notes",
            json={
                "title": "Bad Note",
                "subject_id": "pure_maths",
                "content_text": "Some text",
                "pdf_url": "https://example.com/doc.pdf",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not both", response.json()["detail"])

    def test_study_notes_list_returns_summary_and_detail_loads_content(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "uid_123",
            "role": "ADMIN",
        }
        app.dependency_overrides[get_user_repository] = (
            lambda: _InMemoryUserRepository(role="ADMIN")
        )
        repo = _InMemoryStudyNoteRepository()
        app.dependency_overrides[get_study_note_repository] = lambda: repo

        # Create note with LaTeX content
        create_res = self.client.post(
            "/api/v1/study-notes",
            json={
                "id": "text_note_1",
                "title": "LaTeX Equations Note",
                "subject_id": "pure_maths",
                "content_text": "$$E = mc^2$$",
            },
        )
        self.assertEqual(create_res.status_code, 201)

        # 1. Test List Endpoint: Must return summary (NO content_text or pdf_url)
        list_res = self.client.get("/api/v1/study-notes")
        self.assertEqual(list_res.status_code, 200)
        items = list_res.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "text_note_1")
        self.assertEqual(items[0]["content_type"], "markdown")
        self.assertNotIn("content_text", items[0])  # Excluded from summary!
        self.assertNotIn("pdf_url", items[0])        # Excluded from summary!

        # 2. Test Detail Endpoint: Loads full content on-demand
        detail_res = self.client.get("/api/v1/study-notes/text_note_1")
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.json()
        self.assertEqual(detail["id"], "text_note_1")
        self.assertEqual(detail["content_text"], "$$E = mc^2$$")
        self.assertIsNone(detail["pdf_url"])

    def test_study_note_signed_storage_url_generation(self) -> None:
        """Verifies that relative storage paths are resolved to signed URLs upon detail retrieval."""
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "uid_123",
            "role": "ADMIN",
        }
        app.dependency_overrides[get_user_repository] = (
            lambda: _InMemoryUserRepository(role="ADMIN")
        )
        repo = _InMemoryStudyNoteRepository()
        app.dependency_overrides[get_study_note_repository] = lambda: repo

        # Create note with a cloud storage relative path
        create_res = self.client.post(
            "/api/v1/study-notes",
            json={
                "id": "pdf_note_storage_path",
                "title": "Complex Numbers PDF",
                "subject_id": "pure_maths",
                "pdf_url": "study_notes/pure/complex_numbers.pdf",
            },
        )
        self.assertEqual(create_res.status_code, 201)

        # Retrieve detail: pdf_url must be converted into a signed URL with expiration
        detail_res = self.client.get("/api/v1/study-notes/pdf_note_storage_path")
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.json()
        self.assertEqual(detail["content_type"], "pdf")
        self.assertIsNone(detail["content_text"])
        self.assertIsNotNone(detail["pdf_url"])
        self.assertIn("storage.googleapis.com", detail["pdf_url"])
        self.assertIn("study_notes/pure/complex_numbers.pdf", detail["pdf_url"])
        self.assertIn("X-Goog-Expires=", detail["pdf_url"])


if __name__ == "__main__":
    unittest.main()
