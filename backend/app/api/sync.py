"""Cola de salida del mostrador (FR-017, FR-018; ADR-0003, research R4).

Contrato: specs/004-ventas-multimoneda/contracts/api.md. Una operación por petición,
idempotente por su `id`: reenviarla devuelve la misma respuesta, también si se rechazó.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.api.deps import CurrentDevice, CurrentUser, DbSession, require_roles
from app.domain.roles import Role
from app.services import sync as sync_service

router = APIRouter(prefix="/sync", tags=["sync"])

AdminOrSeller = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.SELLER))]


class OutboxOperationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    operation_type: str = Field(min_length=1, max_length=60)
    schema_version: Literal[1]
    created_at: AwareDatetime
    payload: dict[str, Any]


@router.post("/operations", response_model=None)
def post_operation(
    body: OutboxOperationIn, current: AdminOrSeller, device: CurrentDevice, db: DbSession
) -> JSONResponse:
    """Procesa una operación del mostrador. 200 con el resultado; los rechazos
    permanentes (403 `device_revoked`, 409, 422) llevan el formato de error común."""
    created_at: datetime = body.created_at
    http_status, content = sync_service.process_operation(
        db,
        device=device,
        user=current.user,
        operation=sync_service.Operation(
            id=body.id,
            operation_type=body.operation_type,
            schema_version=body.schema_version,
            created_at=created_at,
            payload=body.payload,
        ),
    )
    db.commit()
    if http_status == 200:
        return JSONResponse(status_code=200, content=content)
    return JSONResponse(status_code=http_status, content={"detail": content})
