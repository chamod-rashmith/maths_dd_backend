"""
SQLAlchemy 2.0 ORM model for Immutable Admin Audit Logs (`admin_audit_logs` - Ring 4 of PROTECT_ADMIN.md).
Records every privileged action performed by ADMIN, EDITOR, or ACCOUNT_AUDIT staff
(e.g., Bank Slip approvals/rejections, Question/Study Note/Curriculum mutations, TOTP Sudo elevations)
with actor identity, role, timestamp, client IP address, user-agent, and structured context.

Immutability Guarantees (100% Pure SQLAlchemy 2.0 ORM - Zero Raw SQL):
1. Unit-of-Work Layer: SQLAlchemy `before_update` and `before_delete` mapper event listeners
   strictly block any in-place attribute mutation or `session.delete(entry)`.
2. Statement Execution Layer: SQLAlchemy `do_orm_execute` session event listener intercepts
   and blocks any `update(AdminAuditLog)` or `delete(AdminAuditLog)` Core/ORM query.
"""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from sqlalchemy import DateTime, Index, String, Text, event, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base
from app.domain.exceptions import PermissionDeniedError


class AdminAuditLog(Base):
    """
    Append-only, immutable audit log entry for privileged administrative operations (Ring 4).
    Once inserted, rows in `admin_audit_logs` can never be updated or deleted.
    """

    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        Index("idx_admin_audit_logs_actor_created", "actor_uid", "created_at"),
        Index("idx_admin_audit_logs_action_created", "action", "created_at"),
        Index("idx_admin_audit_logs_resource", "resource_type", "resource_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="අනන්‍ය විගණන සටහන් හැඳුනුම් අංකය (UUIDv4)",
    )

    actor_uid: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="ක්‍රියාව සිදු කළ Admin / Editor / Account Auditor ගේ UID",
    )

    actor_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="ක්‍රියාව සිදු කළ නිලධාරියාගේ Email ලිපිනය",
    )

    actor_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="ක්‍රියාව සිදු කරන විට පැවති Role එක (ADMIN, EDITOR, ACCOUNT_AUDIT)",
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="සිදු කළ ක්‍රියාව (උදා: BANK_SLIP_APPROVED, BANK_SLIP_REJECTED, QUESTION_DELETED, STUDY_NOTE_DELETED)",
    )

    resource_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="ඉලක්කගත දත්ත වර්ගය (SUBSCRIPTION, QUESTION, STUDY_NOTE, SUBJECT, LESSON, ADMIN_TOTP)",
    )

    resource_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="ඉලක්කගත දත්තයේ ID අගය",
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="ක්‍රියාව සිදු කළ Client IP ලිපිනය",
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Client User-Agent විස්තරය",
    )

    request_method: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="HTTP Method (POST, DELETE, PUT)",
    )

    request_path: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="HTTP Endpoint Path",
    )

    details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded audit metadata (e.g. duration_days, rejection_reason, title)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="ක්‍රියාව සිදු වූ නිශ්චිත UTC වේලාව (Immutable Timestamp)",
    )

    def __repr__(self) -> str:
        return (
            f"<AdminAuditLog(id='{self.id}', actor='{self.actor_uid}', role='{self.actor_role}', "
            f"action='{self.action}', resource='{self.resource_type}:{self.resource_id}', ip='{self.ip_address}')>"
        )


@event.listens_for(AdminAuditLog, "before_update")
def _prevent_admin_audit_log_update(mapper: Any, connection: Any, target: AdminAuditLog) -> None:
    """Strictly prohibits ORM-level updates to existing AdminAuditLog records."""
    raise PermissionDeniedError(
        "admin_audit_logs is an immutable append-only ledger (Ring 4). Updating audit records is strictly prohibited."
    )


@event.listens_for(AdminAuditLog, "before_delete")
def _prevent_admin_audit_log_delete(mapper: Any, connection: Any, target: AdminAuditLog) -> None:
    """Strictly prohibits ORM-level deletions of existing AdminAuditLog records."""
    raise PermissionDeniedError(
        "admin_audit_logs is an immutable append-only ledger (Ring 4). Deleting audit records is strictly prohibited."
    )


@event.listens_for(Session, "do_orm_execute")
def _prevent_bulk_mutation_on_admin_audit_logs(orm_execute_state: Any) -> None:
    """
    Intercepts SQLAlchemy 2.0 `session.execute(update(AdminAuditLog)...)` and
    `session.execute(delete(AdminAuditLog)...)` statements and blocks them before execution.
    """
    if orm_execute_state.is_update or orm_execute_state.is_delete:
        stmt = orm_execute_state.statement
        table = getattr(stmt, "table", None)
        table_name = getattr(table, "name", None)
        if table_name == AdminAuditLog.__tablename__:
            op_type = "UPDATE" if orm_execute_state.is_update else "DELETE"
            raise PermissionDeniedError(
                f"admin_audit_logs is an immutable append-only ledger (Ring 4). {op_type} operations are strictly prohibited."
            )
