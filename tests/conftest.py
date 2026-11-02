"""
Pytest global configuration and fixtures.
Ensures unit tests run in memory without connecting to remote/local PostgreSQL databases or remote Upstash Redis.
"""

import os
from unittest.mock import AsyncMock
import pytest

# Ensure TESTING is set immediately at pytest startup
os.environ["TESTING"] = "1"
os.environ["UPSTASH_REDIS_REST_URL"] = ""
os.environ["UPSTASH_REDIS_REST_TOKEN"] = ""

from app.core.cache import curriculum_cache, districts_cache, study_notes_cache

curriculum_cache._upstash_client = None
districts_cache._upstash_client = None
study_notes_cache._upstash_client = None


@pytest.fixture(autouse=True)
def mock_lifespan_database_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disables database connection pool during test session."""
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setattr("app.main.init_db_pool", AsyncMock())
    monkeypatch.setattr("app.main.close_db_pool", AsyncMock())
