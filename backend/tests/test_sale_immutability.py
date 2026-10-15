"""Ventas, líneas, pagos y operaciones de la cola son inmutables también en la base; los
equipos y clientes no se borran; un pago sin la referencia que exige su método no se
guarda (RN-12/FR-044, SC-010; RF-24; research R9)."""

import uuid

import pytest
from sqlalchemy import text

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db


@pytest.fixture
def sale(
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    give_stock,
    make_sale,
) -> dict:
    make_rate(business_date(clock.utcnow()), "36.50")
    headers = auth_headers(make_user(Role.SELLER))
    _, token = make_device()
    session = open_cash_session(headers, token)
    product = make_product("CON", sale_price="2.00")
    give_stock(product, "5")
    customer = {"id": str(uuid.uuid7()), "name": "Cliente", "document_id": None, "phone": None}
    return make_sale(headers, token, session["id"], [(product, "1")], customer=customer)


def rejects(db, sql: str, params: dict, match: str) -> None:
    with pytest.raises(Exception, match=match):
        db.execute(text(sql), params)
    db.rollback()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE sale SET total_usd = 0 WHERE id = :id",
        "DELETE FROM sale WHERE id = :id",
        "UPDATE sale_item SET quantity = 5 WHERE sale_id = :id",
        "DELETE FROM sale_item WHERE sale_id = :id",
        "UPDATE payment SET amount = 1 WHERE sale_id = :id",
        "DELETE FROM payment WHERE sale_id = :id",
        "UPDATE outbox_operation SET status = 'rejected' WHERE id = "
        "(SELECT outbox_operation_id FROM sale WHERE id = :id)",
    ],
)
def test_solo_insercion(db, sale, sql: str) -> None:
    rejects(db, sql, {"id": sale["id"]}, "solo inserción")


def test_cliente_y_equipo_no_se_borran(db, sale) -> None:
    rejects(
        db, "DELETE FROM customer WHERE id = :id", {"id": sale["customer"]["id"]}, "no se borra"
    )
    rejects(db, "DELETE FROM device WHERE id = :id", {"id": sale["device"]["id"]}, "no se borra")


def test_pago_sin_referencia_exigida(db, sale) -> None:
    sql = """
        INSERT INTO payment (id, sale_id, line_number, cash_session_id, kind,
            payment_method_code, currency, amount, exchange_rate, amount_usd)
        VALUES (:pid, :id, 9, :session, 'sale_payment', 'zelle', 'USD', 1, 36.5, 1)
    """
    params = {"pid": str(uuid.uuid4()), "id": sale["id"], "session": sale["cash_session_id"]}
    rejects(db, sql, params, "exige referencia")


def test_equipo_solo_se_revoca_una_vez_y_su_correlativo_avanza(db, sale) -> None:
    device_id = sale["device"]["id"]
    rejects(
        db,
        "UPDATE device SET last_sequence_number = 0 WHERE id = :id",
        {"id": device_id},
        "solo avanza",
    )
    rejects(db, "UPDATE device SET name = 'Otro' WHERE id = :id", {"id": device_id}, "no cambia")
