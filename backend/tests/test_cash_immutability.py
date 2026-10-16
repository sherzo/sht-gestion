"""Cierres, conteos y egresos inmutables también ante SQL directo (RF-33, RN-12/FR-003,
FR-015; SC-005; research R2, R3)."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db

NOTE = "Cierre de prueba de inmutabilidad"


@pytest.fixture
def counter(make_user, auth_headers, make_device, make_rate, open_cash_session):
    make_rate(business_date(clock.utcnow()), "36.50")
    headers = auth_headers(make_user(Role.SELLER))
    _, token = make_device()
    session = open_cash_session(headers, token, "500.00", "20.00")
    return {"headers": headers, "token": token, "session_id": session["id"]}


@pytest.fixture
def closed(counter, close_cash_session) -> dict:
    response = close_cash_session(counter["headers"], counter["token"], counter["session_id"])
    assert response.status_code == 200, response.text
    return counter


def rejects(db: Session, sql: str, match: str | None = None, **params) -> None:
    with pytest.raises(DBAPIError, match=match):
        db.execute(text(sql), params)
        db.commit()
    db.rollback()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE cash_session SET status = 'open' WHERE id = :id",
        "UPDATE cash_session SET closing_note = 'Otra observación' WHERE id = :id",
        "UPDATE cash_session SET opening_float_usd = 0 WHERE id = :id",
        "DELETE FROM cash_session WHERE id = :id",
        "UPDATE cash_count SET counted_amount = 1 WHERE cash_session_id = :id",
        "DELETE FROM cash_count WHERE cash_session_id = :id",
        "INSERT INTO cash_count VALUES (gen_random_uuid(), :id, 'cash_usd', 'USD', 0, 0, 0, 0)",
    ],
)
def test_caja_cerrada_y_conteos_inmutables(db, closed, sql) -> None:
    """RF-33/FR-015: nada de una caja cerrada cambia, ni se agregan conteos."""
    rejects(db, sql, id=closed["session_id"])


def test_apertura_de_una_caja_abierta_no_cambia(db, counter) -> None:
    rejects(
        db,
        "UPDATE cash_session SET opening_float_ves = 1 WHERE id = :id",
        id=counter["session_id"],
    )


def test_conteo_en_caja_abierta_rechazado(db, counter) -> None:
    rejects(
        db,
        "INSERT INTO cash_count VALUES (gen_random_uuid(), :id, 'cash_usd', 'USD', 0, 0, 0, 0)",
        id=counter["session_id"],
    )


def test_caja_cerrada_sin_sus_seis_conteos_no_se_confirma(db, counter, make_user) -> None:
    """RF-31/FR-011: el trigger diferido exige un conteo por método al confirmar."""
    user = make_user(Role.ADMIN, username="cierre_directo")
    rejects(
        db,
        "UPDATE cash_session SET status = 'closed', closed_at = now(), "
        "closed_recorded_at = now(), closed_by = :user, closed_outside_device = true "
        "WHERE id = :id",
        match="un conteo por cada método",
        id=counter["session_id"],
        user=str(user.id),
    )


# --- Egresos (RF-32, RF-33/FR-003) -----------------------------------------------------


@pytest.fixture
def outflow(counter, register_outflow) -> dict:
    response = register_outflow(counter["headers"], counter["token"], counter["session_id"])
    assert response.status_code == 200, response.text
    return {**counter, "outflow_id": response.json()["id"]}


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM cash_outflow WHERE id = :id",
        "UPDATE cash_outflow SET amount = 1 WHERE id = :id",
        "UPDATE cash_outflow SET reason = 'Otro motivo distinto' WHERE id = :id",
        "UPDATE cash_outflow SET reference = 'REF' WHERE id = :id",
        "UPDATE cash_outflow SET payment_method_code = 'cash_ves', currency = 'VES' WHERE id = :id",
    ],
)
def test_egreso_inmutable(db, outflow, sql) -> None:
    rejects(db, sql, id=outflow["outflow_id"])


VOID_SQL = (
    "UPDATE cash_outflow SET voided_at = now(), voided_by = :user, "
    "void_reason = 'Registrado por error' WHERE id = :id"
)


def test_anular_un_egreso_con_la_caja_abierta(db, outflow, make_user) -> None:
    """La única excepción: fijar las tres columnas de anulación, una vez."""
    user = make_user(Role.ADMIN, username="anula")
    db.execute(text(VOID_SQL), {"id": outflow["outflow_id"], "user": str(user.id)})
    db.commit()
    rejects(db, VOID_SQL, id=outflow["outflow_id"], user=str(user.id))


def test_no_se_anula_un_egreso_de_una_caja_cerrada(
    db, outflow, close_cash_session, make_user
) -> None:
    response = close_cash_session(outflow["headers"], outflow["token"], outflow["session_id"])
    assert response.status_code == 200, response.text
    user = make_user(Role.ADMIN, username="anula")
    rejects(db, VOID_SQL, id=outflow["outflow_id"], user=str(user.id))


def test_egreso_electronico_sin_referencia_rechazado(db, counter, make_user) -> None:
    """RF-24, PRD v0.12: un método que exige referencia no se guarda sin ella."""
    user = make_user(Role.SELLER, username="sin_referencia")
    device_id = db.execute(
        text("SELECT device_id FROM cash_session WHERE id = :id"), {"id": counter["session_id"]}
    ).scalar()
    operation_id = uuid.uuid7()
    rejects(
        db,
        "INSERT INTO cash_outflow (id, cash_session_id, device_id, payment_method_code, "
        "currency, amount, reason, created_by, occurred_at, outbox_operation_id) VALUES "
        "(gen_random_uuid(), :session, :device, 'mobile_payment', 'VES', 300, "
        "'Pago de un delivery', :user, now(), :op)",
        match="exige referencia",
        session=counter["session_id"],
        device=str(device_id),
        user=str(user.id),
        op=str(operation_id),
    )
