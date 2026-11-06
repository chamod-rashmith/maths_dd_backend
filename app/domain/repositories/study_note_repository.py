"""
Abstract Repository Contract for Study Notes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StudyNoteRepository(ABC):
    """Domain contract defining study notes persistence."""

    @abstractmethod
    async def list_notes(
        self,
        subject_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Lists study notes with filtered items and a total count."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single study note by its unique ID."""
        raise NotImplementedError

    @abstractmethod
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
        """Creates or updates a study note."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, note_id: str) -> Dict[str, Any]:
        """Deletes a study note by its unique ID."""
        raise NotImplementedError
