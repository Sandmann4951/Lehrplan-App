"""Audit-Protokoll. Enthält niemals Passwörter oder Sitzungstoken."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .models import AuditEvent

_FORBIDDEN_KEYS = {"password", "password_hash", "token", "token_hash", "csrf_token", "temporary_password"}


def audit(db: Session, actor_id: str | None, action: str, entity_type: str, entity_id: str | None = None, details: dict | None = None) -> None:
    clean = {k: v for k, v in (details or {}).items() if k not in _FORBIDDEN_KEYS} or None
    db.add(AuditEvent(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=clean))
