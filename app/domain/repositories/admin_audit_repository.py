"""
Abstract Domain Repository interface for Immutable Admin Audit Logs (`admin_audit_logs` - Ring 4).
"""

from abc import ABC, abstractmethod
from typing import Any


class AdminAuditRepository(ABC):
    """Append-only repository contract for recording and querying immutable admin audit logs."""

    @abstractmethod
    async def create_log(
        self,
        actor_uid: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor_email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_method: str | None = None,
        request_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Appends a new immutable audit log record to `admin_audit_logs`."""

    @abstractmethod
    async def list_logs(
        self,
        actor_uid: str | None = None,
        actor_role: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Queries immutable audit logs in reverse-chronological order with optional filters."""
