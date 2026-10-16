"""Anulación de egresos de caja por el Admin (RF-32, RF-33; FR-003; research R3 de la
etapa 1.4).

Contrato: specs/005-cierre-caja/contracts/api.md. Los egresos se crean por la cola de
salida (`cash_outflow.create`) y se consultan en el detalle de la caja.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.cash_schemas import CashOutflowOut, outflows_out
from app.api.deps import CurrentUser, DbSession, require_roles
from app.domain.roles import Role
from app.services import cash_outflows as outflows_service

router = APIRouter(prefix="/cash-outflows", tags=["cash-outflows"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]


class OutflowVoidIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=5, max_length=200)


@router.post("/{outflow_id}/void")
def void_outflow(
    outflow_id: uuid.UUID, body: OutflowVoidIn, current: Admin, db: DbSession
) -> CashOutflowOut:
    outflow = outflows_service.void_outflow(
        db, actor=current.user, outflow_id=outflow_id, reason=body.reason
    )
    db.commit()
    db.expire_all()
    return outflows_out(db, [outflow])[0]
