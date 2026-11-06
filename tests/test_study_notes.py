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

    def test_list_study_notes_includes_vote_and_bookmark_state(self) -> None:
        """Verify catalog summary includes upvote_count, downvote_count, user_vote (1/-1/0), and is_bookmarked."""
        standard_user = {"uid": "usr_student_01", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_session.execute.return_value = mock_result

        self.mock_service.list_notes.return_value = {
            "items": [
                {
                    "id": "note_trig_01",
                    "title": "Trigonometry Identities",
                    "subject_id": "sub_pmat",
                    "content_type": "markdown",
                    "is_premium": False,
                    "order_index": 1,
                    "upvote_count": 25,
                    "downvote_count": 3,
                    "user_vote": 1,
                    "is_bookmarked": True,
                }
            ],
            "total": 1,
        }

        client = TestClient(app)
        response = client.get("/api/v1/study-notes?bookmarked_only=true")
        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(item["id"], "note_trig_01")
        self.assertEqual(item["upvote_count"], 25)
        self.assertEqual(item["downvote_count"], 3)
        self.assertEqual(item["user_vote"], 1)
        self.assertTrue(item["is_bookmarked"])
        self.mock_service.list_notes.assert_awaited_once_with(
            subject_id=None,
            lesson_id=None,
            search=None,
            limit=50,
            offset=0,
            user_id="usr_student_01",
            bookmarked_only=True,
        )

    def test_vote_study_note_endpoint(self) -> None:
        """Verify POST /api/v1/study-notes/{note_id}/vote accepts 1, -1, 0 and rejects invalid integers."""
        standard_user = {"uid": "usr_student_01", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user

        self.mock_service.vote_note.return_value = {
            "status": "success",
            "note_id": "note_trig_01",
            "user_vote": 1,
            "upvote_count": 11,
            "downvote_count": 2,
        }

        client = TestClient(app)
        res = client.post("/api/v1/study-notes/note_trig_01/vote", json={"vote": 1})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["user_vote"], 1)
        self.assertEqual(data["upvote_count"], 11)
        self.assertEqual(data["downvote_count"], 2)
        self.mock_service.vote_note.assert_awaited_once_with(
            note_id="note_trig_01",
            user_id="usr_student_01",
            vote=1,
        )

        # Invalid vote value (e.g. 5) must be rejected with 422
        bad_res = client.post("/api/v1/study-notes/note_trig_01/vote", json={"vote": 5})
        self.assertEqual(bad_res.status_code, 422)

    def test_bookmark_study_note_endpoint(self) -> None:
        """Verify POST /api/v1/study-notes/{note_id}/bookmark supports explicit boolean and body-less toggle."""
        standard_user = {"uid": "usr_student_01", "email": "student@mathsdd.lk", "role": "USER"}
        app.dependency_overrides[get_current_user] = lambda: standard_user

        self.mock_service.toggle_bookmark.return_value = {
            "status": "success",
            "note_id": "note_trig_01",
            "is_bookmarked": True,
        }

        client = TestClient(app)
        # 1. Explicit bookmark
        res = client.post("/api/v1/study-notes/note_trig_01/bookmark", json={"is_bookmarked": True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_bookmarked"])

        # 2. Toggle without body
        res_toggle = client.post("/api/v1/study-notes/note_trig_01/bookmark")
        self.assertEqual(res_toggle.status_code, 200)
        self.assertTrue(res_toggle.json()["is_bookmarked"])


class TestNormalizedStudyNoteRepository(unittest.IsolatedAsyncioTestCase):
    """Tests 3NF normalized row creation, transition, and deletion in PostgresStudyNoteRepository."""

    async def test_vote_transitions_and_3nf_deletion_on_zero(self) -> None:
        from app.models.study_note import StudyNote, StudyNoteVote
        from app.repositories.study_note_repository import PostgresStudyNoteRepository

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        repo = PostgresStudyNoteRepository(mock_session)

        fake_note = StudyNote(
            id="note_01",
            title="Vectors",
            subject_id="sub_amat",
            upvote_count=5,
            downvote_count=1,
        )

        # Case 1: User has no previous vote (None) -> casts Upvote (+1)
        res_note = MagicMock()
        res_note.scalar_one_or_none.return_value = fake_note
        res_vote_none = MagicMock()
        res_vote_none.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [res_note, res_vote_none]

        out1 = await repo.vote_note(note_id="note_01", user_id="usr_1", vote=1)
        self.assertEqual(out1["user_vote"], 1)
        self.assertEqual(out1["upvote_count"], 6)
        self.assertEqual(out1["downvote_count"], 1)
        mock_session.add.assert_called_once()

        # Case 2: User switches Upvote (+1) -> Downvote (-1)
        existing_vote = StudyNoteVote(id="usr_1_note_01", user_id="usr_1", note_id="note_01", vote_type=1)
        res_vote_up = MagicMock()
        res_vote_up.scalar_one_or_none.return_value = existing_vote
        mock_session.execute.side_effect = [res_note, res_vote_up]

        out2 = await repo.vote_note(note_id="note_01", user_id="usr_1", vote=-1)
        self.assertEqual(out2["user_vote"], -1)
        self.assertEqual(out2["upvote_count"], 5)
        self.assertEqual(out2["downvote_count"], 2)
        self.assertEqual(existing_vote.vote_type, -1)

        # Case 3: User removes vote (-1 -> 0) -> 3NF row is DELETED from study_note_votes
        res_vote_down = MagicMock()
        res_vote_down.scalar_one_or_none.return_value = existing_vote
        mock_session.execute.side_effect = [res_note, res_vote_down]

        out3 = await repo.vote_note(note_id="note_01", user_id="usr_1", vote=0)
        self.assertEqual(out3["user_vote"], 0)
        self.assertEqual(out3["upvote_count"], 5)
        self.assertEqual(out3["downvote_count"], 1)
        mock_session.delete.assert_awaited_once_with(existing_vote)

    async def test_bookmark_3nf_insert_and_delete(self) -> None:
        from app.models.study_note import StudyNote, StudyNoteBookmark
        from app.repositories.study_note_repository import PostgresStudyNoteRepository

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        repo = PostgresStudyNoteRepository(mock_session)

        fake_note = StudyNote(id="note_01", title="Vectors", subject_id="sub_amat")
        res_note = MagicMock()
        res_note.scalar_one_or_none.return_value = fake_note

        # 1. Toggle when not bookmarked -> inserts StudyNoteBookmark row
        res_bm_none = MagicMock()
        res_bm_none.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [res_note, res_bm_none]

        out1 = await repo.toggle_bookmark(note_id="note_01", user_id="usr_1", is_bookmarked=None)
        self.assertTrue(out1["is_bookmarked"])
        mock_session.add.assert_called_once()

        # 2. Toggle when already bookmarked -> deletes StudyNoteBookmark row
        existing_bm = StudyNoteBookmark(id="usr_1_note_01", user_id="usr_1", note_id="note_01")
        res_bm_existing = MagicMock()
        res_bm_existing.scalar_one_or_none.return_value = existing_bm
        mock_session.execute.side_effect = [res_note, res_bm_existing]

        out2 = await repo.toggle_bookmark(note_id="note_01", user_id="usr_1", is_bookmarked=None)
        self.assertFalse(out2["is_bookmarked"])
        mock_session.delete.assert_awaited_once_with(existing_bm)


if __name__ == "__main__":
    unittest.main()

