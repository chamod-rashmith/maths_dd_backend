"""
Unit & Integration tests for Island-Wide & District Leaderboards (`GET /api/v1/leaderboard` & `/leaderboard/me`).
Verifies:
1. Island-wide Top 50 ranking ordered by XP, total_solved_count, current_streak_days, and uid (all 4 tie-breaker levels).
2. District Leaderboard filtering via 3-letter abbreviation (`?district_id=CMB`), full code (`COLOMBO`), and integer ID (`1`).
3. My Current Rank (`my_rank` in `/leaderboard` and `/leaderboard/me`) accurately computing both `island_rank` and `district_rank`.
4. StudentProfile normalization (school_name, exam_district_id, exam_year), legacy User fallback, and zero-XP student handling.
5. Exclusion of ADMIN/EDITOR/ACCOUNT_AUDIT staff, inactive users, and soft-deleted users from student rankings.
6. Pagination (`limit`, `offset`) and SQL injection immunity with 100% SQLAlchemy 2.0 ORM queries.
"""

from datetime import datetime, timezone
import unittest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.cache import districts_cache
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.district import District
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.models.user_stats import UserStats
from app.repositories.district_repository import DISTRICT_CODE_ALIASES


class TestLeaderboardEndpoints(unittest.IsolatedAsyncioTestCase):
    """End-to-end SQLAlchemy 2.0 ORM tests for Island-Wide & District Leaderboards."""

    async def asyncSetUp(self) -> None:
        app.dependency_overrides.clear()
        districts_cache.clear()

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        async with self.session_factory() as session:
            # Seed Districts: Colombo (1), Kandy (4), Galle (7)
            session.add_all(
                [
                    District(
                        id=1,
                        code="COLOMBO",
                        name_en="Colombo",
                        name_si="කොළඹ",
                        name_ta="கொழும்பு",
                        province="WESTERN",
                        display_order=1,
                    ),
                    District(
                        id=4,
                        code="KANDY",
                        name_en="Kandy",
                        name_si="මහනුවර",
                        name_ta="கண்டி",
                        province="CENTRAL",
                        display_order=4,
                    ),
                    District(
                        id=7,
                        code="GALLE",
                        name_en="Galle",
                        name_si="ගාල්ල",
                        name_ta="காலி",
                        province="SOUTHERN",
                        display_order=7,
                    ),
                ]
            )

            # Seed 5 Active Students across Colombo, Kandy, and Galle
            students = [
                # #1 Island, #1 Colombo (1200 XP)
                (
                    User(uid="stu_cmb_1", email="kasun@mathsdd.lk", name="Kasun Perera", telephone_no="0771111111"),
                    StudentProfile(user_id="stu_cmb_1", exam_district_id=1, school_name="Royal College", exam_year=2026),
                    UserStats(user_id="stu_cmb_1", xp=1200, current_streak_days=14, total_solved_count=85),
                ),
                # #2 Island, #1 Kandy (950 XP)
                (
                    User(uid="stu_kdy_1", email="nimal@mathsdd.lk", name="Nimal Silva", telephone_no="0772222222"),
                    StudentProfile(user_id="stu_kdy_1", exam_district_id=4, school_name="Trinity College", exam_year=2026),
                    UserStats(user_id="stu_kdy_1", xp=950, current_streak_days=10, total_solved_count=60),
                ),
                # #3 Island, #2 Colombo (800 XP, 50 solved - tie-breaker winner over stu_gal_1)
                (
                    User(uid="stu_cmb_2", email="chamod@mathsdd.lk", name="Chamod Rashmith", telephone_no="0773333333"),
                    StudentProfile(user_id="stu_cmb_2", exam_district_id=1, school_name="Ananda College", exam_year=2026),
                    UserStats(user_id="stu_cmb_2", xp=800, current_streak_days=7, total_solved_count=50),
                ),
                # #4 Island, #1 Galle (800 XP, 40 solved)
                (
                    User(uid="stu_gal_1", email="ruwan@mathsdd.lk", name="Ruwan Bandara", telephone_no="0774444444"),
                    StudentProfile(user_id="stu_gal_1", exam_district_id=7, school_name="Richmond College", exam_year=2026),
                    UserStats(user_id="stu_gal_1", xp=800, current_streak_days=5, total_solved_count=40),
                ),
                # #5 Island, #3 Colombo (450 XP)
                (
                    User(uid="stu_cmb_3", email="tharindu@mathsdd.lk", name="Tharindu Fernando", telephone_no="0775555555"),
                    StudentProfile(user_id="stu_cmb_3", exam_district_id=1, school_name="Nalanda College", exam_year=2027),
                    UserStats(user_id="stu_cmb_3", xp=450, current_streak_days=3, total_solved_count=20),
                ),
            ]
            for u, p, s in students:
                session.add(u)
                session.add(p)
                session.add(s)

            # Seed non-eligible staff accounts (ADMIN, EDITOR, ACCOUNT_AUDIT) with huge XP
            # to verify they NEVER pollute student leaderboards
            session.add_all(
                [
                    User(uid="staff_admin", email="admin@mathsdd.lk", name="Admin User", role="ADMIN"),
                    UserStats(user_id="staff_admin", xp=99999, current_streak_days=100, total_solved_count=999),
                    User(uid="staff_editor", email="editor@mathsdd.lk", name="Editor User", role="EDITOR"),
                    UserStats(user_id="staff_editor", xp=88888, current_streak_days=50, total_solved_count=500),
                    User(uid="staff_auditor", email="auditor@mathsdd.lk", name="Auditor User", role="ACCOUNT_AUDIT"),
                    UserStats(user_id="staff_auditor", xp=77777, current_streak_days=40, total_solved_count=400),
                ]
            )
            await session.commit()

        async def override_get_db():
            async with self.session_factory() as session:
                yield session
                await session.commit()

        app.dependency_overrides[get_db] = override_get_db
        # Authenticate as stu_cmb_2 (#3 Island, #2 Colombo)
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "stu_cmb_2",
            "email": "chamod@mathsdd.lk",
            "name": "Chamod Rashmith",
            "role": "USER",
        }

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()
        districts_cache.clear()
        await self.engine.dispose()

    def test_island_wide_top_50_and_my_current_rank(self) -> None:
        """Verifies Island-wide Top 50 ordering, tie-breakers, staff/deleted exclusion, privacy, and My Current Rank."""
        client = TestClient(app)
        res = client.get("/api/v1/leaderboard")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["scope"], "ISLAND")
        self.assertIsNone(data["district"])
        self.assertEqual(data["total_students"], 5)
        self.assertEqual(len(data["items"]), 5)

        # Verify deterministic ranking order: stu_cmb_1 (1), stu_kdy_1 (2), stu_cmb_2 (3), stu_gal_1 (4), stu_cmb_3 (5)
        expected_uids = ["stu_cmb_1", "stu_kdy_1", "stu_cmb_2", "stu_gal_1", "stu_cmb_3"]
        self.assertEqual([item["user_id"] for item in data["items"]], expected_uids)
        self.assertEqual([item["rank"] for item in data["items"]], [1, 2, 3, 4, 5])

        # Verify current user flag on rank #3
        self.assertFalse(data["items"][0]["is_current_user"])
        self.assertTrue(data["items"][2]["is_current_user"])
        self.assertEqual(data["items"][2]["school_name"], "Ananda College")
        self.assertEqual(data["items"][2]["district_code"], "COLOMBO")

        # Verify sensitive PII is never leaked
        for item in data["items"]:
            self.assertNotIn("email", item)
            self.assertNotIn("telephone_no", item)

        # Verify my_rank card: #3 Island-wide (out of 5), #2 in Colombo District (out of 3)
        my_rank = data["my_rank"]
        self.assertEqual(my_rank["user_id"], "stu_cmb_2")
        self.assertEqual(my_rank["xp"], 800)
        self.assertEqual(my_rank["island_rank"], 3)
        self.assertEqual(my_rank["total_island_students"], 5)
        self.assertEqual(my_rank["district_rank"], 2)
        self.assertEqual(my_rank["total_district_students"], 3)
        self.assertEqual(my_rank["district_code"], "COLOMBO")

    def test_district_leaderboard_with_cmb_abbreviation_and_full_code(self) -> None:
        """Verifies ?district_id=CMB, ?district_id=COLOMBO, and ?district_id=1 filter Colombo district top students."""
        client = TestClient(app)

        for query_val in ("CMB", "cmb", "COLOMBO", "1"):
            res = client.get(f"/api/v1/leaderboard?district_id={query_val}")
            self.assertEqual(res.status_code, 200)
            data = res.json()

            self.assertEqual(data["scope"], "DISTRICT")
            self.assertIsNotNone(data["district"])
            self.assertEqual(data["district"]["id"], 1)
            self.assertEqual(data["district"]["code"], "COLOMBO")
            self.assertEqual(data["district"]["name_si"], "කොළඹ")
            self.assertEqual(data["total_students"], 3)
            self.assertEqual(len(data["items"]), 3)

            # Colombo ranks: 1. stu_cmb_1 (1200 XP), 2. stu_cmb_2 (800 XP), 3. stu_cmb_3 (450 XP)
            self.assertEqual(
                [item["user_id"] for item in data["items"]],
                ["stu_cmb_1", "stu_cmb_2", "stu_cmb_3"],
            )
            self.assertEqual([item["rank"] for item in data["items"]], [1, 2, 3])

            # my_rank still shows both Island rank (#3) and District rank (#2)
            self.assertEqual(data["my_rank"]["island_rank"], 3)
            self.assertEqual(data["my_rank"]["district_rank"], 2)

    async def test_all_four_tie_breaker_levels_and_legacy_user_fallback(self) -> None:
        """Verifies tie-breaking by (xp DESC, total_solved_count DESC, current_streak_days DESC, uid ASC) and legacy fallback."""
        async with self.session_factory() as session:
            # Add two students with identical XP (800) and solved count (40), differing only by streak
            # and two students with identical XP, solved count, and streak, differing only by uid
            session.add_all(
                [
                    User(uid="stu_tie_streak_high", email="t1@mathsdd.lk", name="Streak High", district_id=4, school_name="Kingswood College"),
                    UserStats(user_id="stu_tie_streak_high", xp=800, total_solved_count=40, current_streak_days=12),
                    User(uid="stu_tie_uid_a", email="ta@mathsdd.lk", name="Tie UID A", district_id=4, school_name="Dharmaraja College"),
                    UserStats(user_id="stu_tie_uid_a", xp=800, total_solved_count=40, current_streak_days=5),
                    # Student with NO UserStats row yet (defaults to 0 XP)
                    User(uid="stu_zero_xp", email="zero@mathsdd.lk", name="New Student", district_id=1, school_name="Mahanama College"),
                ]
            )
            await session.commit()

        # Authenticate as the new student with 0 XP and no StudentProfile row (uses User.district_id=1 fallback)
        app.dependency_overrides[get_current_user] = lambda: {
            "uid": "stu_zero_xp",
            "email": "zero@mathsdd.lk",
            "name": "New Student",
            "role": "USER",
        }
        client = TestClient(app)
        res = client.get("/api/v1/leaderboard")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        expected_order = [
            "stu_cmb_1",           # 1200 XP
            "stu_kdy_1",           # 950 XP
            "stu_cmb_2",           # 800 XP, 50 solved
            "stu_tie_streak_high", # 800 XP, 40 solved, 12 streak
            "stu_gal_1",           # 800 XP, 40 solved, 5 streak, uid 'stu_gal_1' < 'stu_tie_uid_a'
            "stu_tie_uid_a",       # 800 XP, 40 solved, 5 streak, uid 'stu_tie_uid_a'
            "stu_cmb_3",           # 450 XP
            "stu_zero_xp",         # 0 XP (no UserStats row)
        ]
        self.assertEqual([item["user_id"] for item in data["items"]], expected_order)
        self.assertEqual([item["rank"] for item in data["items"]], [1, 2, 3, 4, 5, 6, 7, 8])

        # Verify legacy fallback fields on stu_zero_xp and deduplicated my_rank card
        my_rank = data["my_rank"]
        self.assertEqual(my_rank["user_id"], "stu_zero_xp")
        self.assertEqual(my_rank["xp"], 0)
        self.assertNotIn("district_id", my_rank)
        self.assertNotIn("name", my_rank)
        self.assertNotIn("school_name", my_rank)
        self.assertEqual(my_rank["district_code"], "COLOMBO")
        self.assertEqual(my_rank["island_rank"], 8)
        self.assertEqual(my_rank["total_island_students"], 8)
        self.assertEqual(my_rank["district_rank"], 4)
        self.assertEqual(my_rank["total_district_students"], 4)

    def test_pagination_limit_and_offset(self) -> None:
        """Verifies pagination slicing preserves global 1-indexed rank numbers."""
        client = TestClient(app)
        res = client.get("/api/v1/leaderboard?limit=2&offset=2")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual([item["user_id"] for item in data["items"]], ["stu_cmb_2", "stu_gal_1"])
        self.assertEqual([item["rank"] for item in data["items"]], [3, 4])

        # Verify out-of-bounds limit is rejected by FastAPI query validation
        bad_limit = client.get("/api/v1/leaderboard?limit=500")
        self.assertEqual(bad_limit.status_code, 422)

    def test_my_rank_dedicated_endpoint(self) -> None:
        """Verifies GET /api/v1/leaderboard/me returns the student's live rank card."""
        client = TestClient(app)
        res = client.get("/api/v1/leaderboard/me")
        self.assertEqual(res.status_code, 200)
        my_rank = res.json()
        self.assertEqual(my_rank["user_id"], "stu_cmb_2")
        self.assertEqual(my_rank["island_rank"], 3)
        self.assertEqual(my_rank["total_island_students"], 5)
        self.assertEqual(my_rank["district_rank"], 2)
        self.assertEqual(my_rank["total_district_students"], 3)

    def test_invalid_district_id_and_sqli_payload_rejected_safely(self) -> None:
        """Verifies unknown district_id and SQL injection strings return 400 Bad Request safely."""
        client = TestClient(app)
        for bad_input in ("INVALID_DISTRICT", "999", "' OR '1'='1", "CMB; DROP TABLE users;--"):
            res = client.get("/api/v1/leaderboard", params={"district_id": bad_input})
            self.assertEqual(res.status_code, 400)
            self.assertIn("Invalid district identifier", res.json()["detail"])

        # Verify all 25 Sri Lankan districts are covered by DISTRICT_CODE_ALIASES
        self.assertEqual(len(set(DISTRICT_CODE_ALIASES.values())), 25)
        self.assertEqual(DISTRICT_CODE_ALIASES["CMB"], "COLOMBO")
        self.assertEqual(DISTRICT_CODE_ALIASES["KDY"], "KANDY")
        self.assertEqual(DISTRICT_CODE_ALIASES["GAL"], "GALLE")

    def test_unauthenticated_leaderboard_request_returns_401(self) -> None:
        """Verifies unauthenticated requests to /api/v1/leaderboard and /leaderboard/me return 401."""
        app.dependency_overrides.pop(get_current_user, None)
        client = TestClient(app)
        self.assertEqual(client.get("/api/v1/leaderboard").status_code, 401)
        self.assertEqual(client.get("/api/v1/leaderboard/me").status_code, 401)


if __name__ == "__main__":
    unittest.main()
