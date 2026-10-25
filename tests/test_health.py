"""
Unit tests verifying FastAPI application wiring, OpenAPI routes, and health probes.
"""

import unittest
from fastapi.testclient import TestClient

from app.main import app


class TestBackendHealthAndRoutes(unittest.TestCase):
    """Verifies core endpoints and ensures zero mock/seed endpoints remain."""

    def setUp(self) -> None:
        self.client = TestClient(app)

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


if __name__ == "__main__":
    unittest.main()
