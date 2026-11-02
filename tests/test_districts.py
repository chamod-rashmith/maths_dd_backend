"""
Unit tests for Sri Lankan Administrative Districts repository, caching, and API endpoint.
Verifies persistent Redis/memory caching, zero-DB-overhead lookup, and data schema.
"""

from typing import Any, List
import unittest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.core.cache import districts_cache
from app.main import app
from app.models.district import District
from app.repositories.district_repository import DISTRICTS_CACHE_KEY, DistrictRepository
from app.schemas.district import DistrictResponse


class TestDistricts(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        districts_cache.clear()
        self.mock_districts: List[District] = [
            District(
                id="COLOMBO",
                name_en="Colombo",
                name_si="කොළඹ",
                name_ta="கொழும்பு",
                province="WESTERN",
                display_order=1,
            ),
            District(
                id="KANDY",
                name_en="Kandy",
                name_si="මහනුවර",
                name_ta="கண்டி",
                province="CENTRAL",
                display_order=4,
            ),
            District(
                id="GALLE",
                name_en="Galle",
                name_si="ගාල්ල",
                name_ta="காலி",
                province="SOUTHERN",
                display_order=7,
            ),
        ]

    def tearDown(self) -> None:
        districts_cache.clear()

    async def test_repository_get_all_caches_persistently_with_zero_ttl(self) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = self.mock_districts
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = DistrictRepository(mock_session)

        # 1. First call: Cache miss -> executes database query
        districts = await repo.get_all()
        self.assertEqual(len(districts), 3)
        self.assertEqual(districts[0]["id"], "COLOMBO")
        self.assertEqual(districts[0]["name_si"], "කොළඹ")
        self.assertEqual(districts[0]["province"], "WESTERN")
        self.assertEqual(mock_session.execute.call_count, 1)

        # Verify cached in memory with infinite TTL
        cached_entry = districts_cache._memory_fallback._store.get(DISTRICTS_CACHE_KEY)
        self.assertIsNotNone(cached_entry)
        expires_at, cached_value = cached_entry
        self.assertEqual(expires_at, float("inf"))
        self.assertEqual(len(cached_value), 3)

        # 2. Second call: Cache hit -> zero DB queries!
        cached_districts = await repo.get_all()
        self.assertEqual(len(cached_districts), 3)
        self.assertEqual(mock_session.execute.call_count, 1)  # Still 1!

    async def test_repository_get_by_id(self) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = self.mock_districts
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = DistrictRepository(mock_session)

        colombo = await repo.get_by_id("colombo")
        self.assertIsNotNone(colombo)
        self.assertEqual(colombo["name_en"], "Colombo")
        self.assertEqual(colombo["name_ta"], "கொழும்பு")

        invalid = await repo.get_by_id("ATLANTIS")
        self.assertIsNone(invalid)

    async def test_repository_cache_invalidation(self) -> None:
        districts_cache.set(DISTRICTS_CACHE_KEY, [{"id": "COLOMBO"}], ttl_seconds=0)
        self.assertIsNotNone(districts_cache.get(DISTRICTS_CACHE_KEY))

        DistrictRepository.invalidate_cache()
        self.assertIsNone(districts_cache.get(DISTRICTS_CACHE_KEY))

    def test_districts_api_endpoint(self) -> None:
        # Pre-seed cache with sample data for API test
        districts_cache.set(
            DISTRICTS_CACHE_KEY,
            [
                {
                    "id": "COLOMBO",
                    "name_en": "Colombo",
                    "name_si": "කොළඹ",
                    "name_ta": "கொழும்பு",
                    "province": "WESTERN",
                    "display_order": 1,
                },
                {
                    "id": "GAMPAHA",
                    "name_en": "Gampaha",
                    "name_si": "ගම්පහ",
                    "name_ta": "கம்பஹா",
                    "province": "WESTERN",
                    "display_order": 2,
                },
            ],
            ttl_seconds=0,
        )

        client = TestClient(app)
        response = client.get("/api/v1/districts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], "COLOMBO")
        self.assertEqual(data[0]["name_en"], "Colombo")
        self.assertEqual(data[0]["name_si"], "කොළඹ")
        self.assertEqual(data[0]["name_ta"], "கொழும்பு")
        self.assertEqual(data[0]["province"], "WESTERN")
        self.assertEqual(data[1]["id"], "GAMPAHA")

        # Validate with Pydantic
        dtos = [DistrictResponse.model_validate(item) for item in data]
        self.assertEqual(len(dtos), 2)
