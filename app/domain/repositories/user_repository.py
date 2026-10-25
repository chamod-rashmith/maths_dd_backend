"""
Abstract Repository Contract for User Profile persistence.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class UserRepository(ABC):
    """Domain contract defining user profile persistence operations."""

    @abstractmethod
    async def get_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """Fetches a user profile record by its unique Firebase UID."""
        raise NotImplementedError

    @abstractmethod
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
        """Idempotently creates or updates a user profile upon authentication sync."""
        raise NotImplementedError
