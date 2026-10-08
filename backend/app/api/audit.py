"""Consulta de la auditoría, solo para el admin (RF-46/FR-025).

Contrato: specs/001-usuarios-autenticacion-permisos/contracts/api.md.
"""

import uuid
from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, require_roles
from app.domain.roles import Role
from app.services.audit import query_audit

router = APIRouter(prefix="/audit-log", tags=["audit"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]


class AuditUser(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str


class AuditEntry(BaseModel):
    id: uuid.UUID
    occurred_at: datetime
    user: AuditUser | None
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    details: dict[str, Any] | None


class AuditPage(BaseModel):
    items: list[AuditEntry]
    total: int
    page: int
    page_size: int


@router.get("")
def list_audit(
    current: Admin,
    db: DbSession,
    user_id: uuid.UUID | None = None,
    action: Annotated[str | None, Query(max_length=500)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AuditPage:
    rows, total = query_audit(
        db,
        user_id=user_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    items = [
        AuditEntry(
            id=entry.id,
            occurred_at=entry.occurred_at,
            user=AuditUser(id=user.id, username=user.username, full_name=user.full_name)
            if user
            else None,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            before=entry.before,
            after=entry.after,
            reason=entry.reason,
            details=entry.details,
        )
        for entry, user in rows
    ]
    return AuditPage(items=items, total=total, page=page, page_size=page_size)
