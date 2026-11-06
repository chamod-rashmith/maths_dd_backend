"""
Application Service for Immutable Admin Audit Logging (Ring 4 of PROTECT_ADMIN.md).
Extracts actor identity, role, IP address (`X-Forwarded-For` / `X-Real-IP` / `client.host`),
User-Agent, and HTTP request context, and appends an immutable record to `admin_audit_logs`.
"""

from typing import Any
from fastapi import Request

from app.domain.repositories.admin_audit_repository import AdminAuditRepository


def extract_client_ip(request: Request | None) -> str | None:
    """Extracts the originating client IP address from reverse-proxy headers or socket connection."""
    if request is None:
        return None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first_ip = xff.split(",")[0].strip()
        if first_ip:
            return first_ip[:64]
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip and x_real_ip.strip():
        return x_real_ip.strip()[:64]
    if request.client and request.client.host:
        return str(request.client.host)[:64]
    return None


class AdminAuditService:
    """Service for recording and querying immutable administrative audit logs."""

    def __init__(self, repo: AdminAuditRepository) -> None:
        self._repo = repo

    async def record_action(
        self,
        actor: dict[str, Any],
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        request: Request | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Records an immutable audit log entry for an ADMIN, EDITOR, or ACCOUNT_AUDIT operation."""
        actor_uid = str(actor.get("uid") or "unknown")
        actor_email = actor.get("email")
        actor_role = str(actor.get("role") or "ADMIN").upper()
        ip_address = extract_client_ip(request)
        user_agent = request.headers.get("user-agent") if request is not None else None
        request_method = request.method if request is not None else None
        request_path = request.url.path if request is not None else None

        return await self._repo.create_log(
            actor_uid=actor_uid,
            actor_email=str(actor_email) if actor_email else None,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            details=details,
        )

    async def list_audit_logs(
        self,
        actor_uid: str | None = None,
        actor_role: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Returns paginated immutable audit logs matching the given filter criteria."""
        return await self._repo.list_logs(
            actor_uid=actor_uid,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
            offset=offset,
        )
