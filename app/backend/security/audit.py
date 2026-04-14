"""Audit logging — every access to financial data is recorded."""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from database import AuditLog


def log(
    db: Session,
    action: str,
    *,
    user_id: Optional[int] = None,
    resource: Optional[str] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        detail=detail,
        timestamp=datetime.utcnow(),
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
