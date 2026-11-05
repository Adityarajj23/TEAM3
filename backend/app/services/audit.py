"""Audit logging — every state-changing operation records an entry."""
from __future__ import annotations

import contextvars
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog

current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)


def record(db: Session, actor_id: int | None, action: str, entity_type: str, entity_id: int | None = None,
           entity_key: str | None = None, project_id: int | None = None, details: dict[str, Any] | None = None,
           source: str = "platform", created_at=None) -> AuditLog:
    entry = AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id,
                     entity_key=entity_key, project_id=project_id, details=details or {}, source=source,
                     trace_id=current_trace_id.get())
    if created_at is not None:
        entry.created_at = created_at
    db.add(entry)
    return entry
