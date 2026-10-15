"""Esquemas de equipos, caja y ventas (contrato: specs/004-ventas-multimoneda/contracts/
api.md). Decimales como cadenas (ADR-0004); fechas ISO."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.product_schemas import UserRef, user_ref
from app.db.models import CashSession, Device
from app.services.devices import open_cash_session
from app.services.users import users_by_id


class CashSessionOut(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    business_date: date
    opened_by: UserRef
    opened_at: datetime
    opening_float_ves: str
    opening_float_usd: str
    status: str


class OpenCashSessionRef(BaseModel):
    id: uuid.UUID
    opened_by: UserRef
    opened_at: datetime
    business_date: date


class DeviceOut(BaseModel):
    id: uuid.UUID
    name: str
    series: str
    last_sequence_number: int
    registered_by: UserRef
    registered_at: datetime
    revoked_at: datetime | None
    open_cash_session: OpenCashSessionRef | None


class DeviceRegistered(DeviceOut):
    """Respuesta del registro: única vez que se entrega el token (research R3)."""

    token: str


class DeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=60)


def cash_session_out(db: Session, session: CashSession) -> CashSessionOut:
    opener = users_by_id(db, {session.opened_by})[session.opened_by]
    return CashSessionOut(
        id=session.id,
        device_id=session.device_id,
        business_date=session.business_date,
        opened_by=user_ref(opener),
        opened_at=session.opened_at,
        opening_float_ves=str(session.opening_float_ves),
        opening_float_usd=str(session.opening_float_usd),
        status=session.status,
    )


def devices_out(db: Session, devices: list[Device]) -> list[DeviceOut]:
    sessions = {device.id: open_cash_session(db, device.id) for device in devices}
    users = users_by_id(
        db,
        {device.registered_by for device in devices}
        | {session.opened_by for session in sessions.values() if session is not None},
    )
    result = []
    for device in devices:
        session = sessions[device.id]
        result.append(
            DeviceOut(
                id=device.id,
                name=device.name,
                series=device.series,
                last_sequence_number=device.last_sequence_number,
                registered_by=user_ref(users[device.registered_by]),
                registered_at=device.registered_at,
                revoked_at=device.revoked_at,
                open_cash_session=None
                if session is None
                else OpenCashSessionRef(
                    id=session.id,
                    opened_by=user_ref(users[session.opened_by]),
                    opened_at=session.opened_at,
                    business_date=session.business_date,
                ),
            )
        )
    return result
