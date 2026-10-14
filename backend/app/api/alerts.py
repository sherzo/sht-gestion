"""Endpoints de alertas para el Admin (RN-14/FR-018, research R8).

Contrato: specs/003-proveedores-compras/contracts/api.md.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, require_roles
from app.api.product_schemas import UserRef, user_ref
from app.db.models import Alert
from app.domain.roles import Role
from app.services import alerts as alerts_service
from app.services.users import users_by_id

router = APIRouter(prefix="/alerts", tags=["alerts"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]


class AlertOut(BaseModel):
    id: uuid.UUID
    type: str
    entity_type: str
    entity_id: uuid.UUID
    details: dict[str, Any]
    created_at: datetime
    resolved_at: datetime | None
    resolved_by: UserRef | None


class AlertPage(BaseModel):
    items: list[AlertOut]
    total: int
    page: int
    page_size: int


def alerts_out(db: DbSession, rows: list[Alert]) -> list[AlertOut]:
    users = users_by_id(db, {row.resolved_by for row in rows})
    return [
        AlertOut(
            id=row.id,
            type=row.type,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            details=row.details,
            created_at=row.created_at,
            resolved_at=row.resolved_at,
            resolved_by=user_ref(users.get(row.resolved_by)) if row.resolved_by else None,
        )
        for row in rows
    ]


@router.get("")
def list_alerts(
    current: Admin,
    db: DbSession,
    status: Literal["open", "resolved"] = "open",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AlertPage:
    rows, total = alerts_service.list_alerts(db, status=status, page=page, page_size=page_size)
    return AlertPage(items=alerts_out(db, rows), total=total, page=page, page_size=page_size)


@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id: uuid.UUID, current: Admin, db: DbSession) -> AlertOut:
    alert = alerts_service.resolve_alert(db, actor=current.user, alert_id=alert_id)
    return alerts_out(db, [alert])[0]
