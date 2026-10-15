"""Equipos de mostrador (FR-001 a FR-004; RN-11, research R3).

Contrato: specs/004-ventas-multimoneda/contracts/api.md. El Admin registra el equipo desde
su navegador y recibe el token una sola vez.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import ActiveDevice, CurrentUser, DbSession, require_roles
from app.api.sale_schemas import DeviceCreate, DeviceOut, DeviceRegistered, devices_out
from app.domain.roles import Role
from app.services import devices as devices_service

router = APIRouter(prefix="/devices", tags=["devices"])

Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]
AdminOrSeller = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.SELLER))]


@router.post("", status_code=status.HTTP_201_CREATED)
def register_device(body: DeviceCreate, current: Admin, db: DbSession) -> DeviceRegistered:
    device, token = devices_service.register_device(db, actor=current.user, name=body.name)
    db.commit()
    return DeviceRegistered(**devices_out(db, [device])[0].model_dump(), token=token)


@router.get("")
def list_devices(current: Admin, db: DbSession) -> list[DeviceOut]:
    return devices_out(db, devices_service.list_devices(db))


@router.post("/{device_id}/revoke")
def revoke_device(device_id: uuid.UUID, current: Admin, db: DbSession) -> DeviceOut:
    device = devices_service.revoke_device(db, actor=current.user, device_id=device_id)
    db.commit()
    return devices_out(db, [device])[0]


@router.get("/current")
def current_device(current: AdminOrSeller, device: ActiveDevice, db: DbSession) -> DeviceOut:
    """El equipo del token, con su caja abierta y el último correlativo registrado."""
    return devices_out(db, [device])[0]
