"""Registro de una venta por la cola de salida (RF-20, RF-21, RF-26, RF-28; RN-02, RN-05,
RN-11; FR-010 a FR-019, FR-033, FR-037; research R4, R5, R11, R17)."""

import uuid
from dataclasses import dataclass
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import clock
from app.db.models import (
    Customer,
    Device,
    OutboxOperation,
    Payment,
    Product,
    Sale,
    SaleItem,
    StockMovement,
)
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db


@dataclass
class Counter:
    headers: dict[str, str]
    token: str
    device: Device
    session_id: str
    seller_id: uuid.UUID


@pytest.fixture
def counter(make_user, auth_headers, make_device, make_rate, open_cash_session) -> Counter:
    make_rate(business_date(clock.utcnow()), "36.50")
    seller = make_user(Role.SELLER)
    headers = auth_headers(seller)
    device, token = make_device("Mostrador principal")
    session = open_cash_session(headers, token)
    return Counter(headers, token, device, session["id"], seller.id)


@pytest.fixture
def products(make_product, give_stock) -> tuple[Product, Product]:
    fitting = make_product("CON", sale_price="3.25", avg_cost="1.500000")
    hose = make_product("MAN", sale_price="4.00", avg_cost="2.000000")
    give_stock(fitting, "10")
    give_stock(hose, "20")
    return fitting, hose


def sale_of(counter: Counter, make_sale, items, **kwargs) -> dict:
    return make_sale(counter.headers, counter.token, counter.session_id, items, **kwargs)


def test_venta_de_la_us2(counter, products, make_sale, db) -> None:
    """2 conexiones a 3,25 y 30 cm de manguera a 4,00/m con tasa 36,50."""
    fitting, hose = products
    sale = sale_of(counter, make_sale, [(fitting, "2"), (hose, "0.30", "cm")])
    assert sale["number"] == "A-000001"
    assert sale["status"] == "registered"
    assert sale["subtotal_usd"] == "7.70"
    assert sale["total_usd"] == "7.70"
    assert sale["total_ves"] == "281.05"
    assert sale["exchange_rate"] == "36.50000000"
    assert sale["seller"]["id"] == str(counter.seller_id)
    assert sale["cash_session_id"] == counter.session_id
    assert [item["line_subtotal_usd"] for item in sale["items"]] == ["6.50", "1.20"]
    assert sale["items"][1]["entered_unit"] == "cm"
    assert sale["items"][1]["quantity"] == "0.30"
    assert sale["payments"] == [
        {
            "kind": "sale_payment",
            "method": "cash_usd",
            "currency": "USD",
            "amount": "7.70",
            "amount_usd": "7.70",
            "reference": None,
        }
    ]

    db.expire_all()
    movements = db.scalars(
        select(StockMovement).where(StockMovement.type == "sale").order_by(StockMovement.product_id)
    ).all()
    deltas = {movement.product_id: movement.quantity_delta for movement in movements}
    assert deltas == {fitting.id: Decimal("-2.00"), hose.id: Decimal("-0.30")}
    assert all(movement.reference_type == "sale_item" for movement in movements)
    assert all(movement.device_id == counter.device.id for movement in movements)
    assert db.get(Product, fitting.id).stock == Decimal("8.00")
    assert db.get(Product, hose.id).stock == Decimal("19.70")
    costs = {item.product_id: item.unit_cost_usd for item in db.scalars(select(SaleItem))}
    assert costs == {fitting.id: Decimal("1.500000"), hose.id: Decimal("2.000000")}
    assert db.get(Device, counter.device.id).last_sequence_number == 1


def test_guarda_la_tasa_enviada_aunque_haya_otra_mas_reciente(
    counter, products, make_sale, make_rate
) -> None:
    """RN-05: la venta conserva la tasa con la que se hizo en el equipo."""
    fitting, _ = products
    today = business_date(clock.utcnow())
    sale = sale_of(counter, make_sale, [(fitting, "1")], rate=("36.40000000", today))
    assert sale["exchange_rate"] == "36.40000000"
    assert sale["exchange_rate_date"] == today.isoformat()


@pytest.mark.parametrize(
    ("product_index", "quantity", "field"),
    [(0, "1.5", "quantity"), (1, "0.305", "quantity"), (0, "0", "quantity")],
)
def test_cantidades_invalidas(counter, products, make_sale, product_index, quantity, field) -> None:
    body = sale_of(
        counter, make_sale, [(products[product_index], quantity)], expect=422, payments=[]
    )
    assert body["detail"]["code"] == "validation_error"
    assert any(key.endswith(field) for key in body["detail"]["fields"])


def test_venta_sin_lineas_y_producto_inexistente(counter, products, make_sale, client) -> None:
    body = sale_of(counter, make_sale, [], expect=422, payments=[])
    assert body["detail"]["code"] == "validation_error"
    ghost = Product(id=uuid.uuid4(), sale_price_usd=Decimal("1.00"), unit_id=products[0].unit_id)
    body = sale_of(counter, make_sale, [(ghost, "1", "unit")], expect=422)
    assert "payload.items.0.product_id" in body["detail"]["fields"]


def test_caja_de_otro_equipo(counter, products, make_sale, make_device, open_cash_session) -> None:
    _, other_token = make_device("Tablet")
    other_session = open_cash_session(counter.headers, other_token)
    body = make_sale(
        counter.headers, counter.token, other_session["id"], [(products[0], "1")], expect=409
    )
    assert body["detail"]["code"] == "cash_session_unavailable"


def test_correlativo_ocupado_por_otra_operacion(counter, products, make_sale) -> None:
    sale_of(counter, make_sale, [(products[0], "1")], sequence_number=5)
    body = sale_of(counter, make_sale, [(products[0], "1")], sequence_number=5, expect=409)
    assert body["detail"]["code"] == "sequence_conflict"


def test_el_correlativo_del_equipo_solo_avanza(counter, products, make_sale, db) -> None:
    sale_of(counter, make_sale, [(products[0], "1")], sequence_number=7)
    sale_of(counter, make_sale, [(products[0], "1")], sequence_number=3)
    db.expire_all()
    assert db.get(Device, counter.device.id).last_sequence_number == 7


def test_reenviar_no_duplica(counter, products, make_sale, client, db) -> None:
    fitting, _ = products
    op_id = str(uuid.uuid7())
    sale_id = str(uuid.uuid7())
    first = sale_of(counter, make_sale, [(fitting, "1")], op_id=op_id, sale_id=sale_id)
    second = sale_of(counter, make_sale, [(fitting, "1")], op_id=op_id, sale_id=sale_id)
    assert first == second
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Sale)) == 1
    assert db.scalar(select(func.count()).select_from(Payment)) == 1
    assert db.get(Product, fitting.id).stock == Decimal("9.00")


def test_vendedor_distinto_del_usuario_de_la_sesion(
    counter, products, make_sale, make_user
) -> None:
    """R17: la venta queda a nombre de quien la envía."""
    other = make_user(Role.SELLER)
    body = sale_of(counter, make_sale, [(products[0], "1")], seller_id=str(other.id), expect=422)
    assert "payload.seller_id" in body["detail"]["fields"]


def test_cliente_nuevo_existente_y_por_documento(counter, products, make_sale, db) -> None:
    """RF-28/FR-019: el cliente es opcional y no se duplica por documento."""
    fitting, _ = products
    customer = {
        "id": str(uuid.uuid7()),
        "name": "Taller El Tornillo",
        "document_id": "j-40123456-7",
        "phone": None,
    }
    first = sale_of(counter, make_sale, [(fitting, "1")], customer=customer)
    assert first["customer"]["document_id"] == "J-40123456-7"

    again = {**customer, "id": str(uuid.uuid7()), "name": "Otro nombre"}
    second = sale_of(counter, make_sale, [(fitting, "1")], customer=again)
    assert second["customer"]["id"] == first["customer"]["id"]

    third = sale_of(counter, make_sale, [(fitting, "1")], customer_id=first["customer"]["id"])
    assert third["customer"]["name"] == "Taller El Tornillo"

    plain = sale_of(counter, make_sale, [(fitting, "1")])
    assert plain["customer"] is None
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Customer)) == 1


def test_documento_de_cliente_invalido(counter, products, make_sale) -> None:
    customer = {
        "id": str(uuid.uuid7()),
        "name": "Cliente",
        "document_id": "V123456789",
        "phone": None,
    }
    body = sale_of(counter, make_sale, [(products[0], "1")], customer=customer, expect=422)
    assert "payload.customer.document_id" in body["detail"]["fields"]


def test_un_pago_que_cubre_y_uno_que_no(counter, products, make_sale) -> None:
    fitting, _ = products
    sale = sale_of(counter, make_sale, [(fitting, "2")], payments=[("cash_usd", "6.50", None)])
    assert sale["paid_usd"] == "6.50"
    body = sale_of(
        counter, make_sale, [(fitting, "2")], payments=[("cash_usd", "6.00", None)], expect=422
    )
    assert body["detail"]["code"] == "validation_error"


def test_fallo_a_mitad_no_deja_nada(counter, products, make_sale, monkeypatch, db, client) -> None:
    """FR-018: venta, pagos, movimientos y operación se guardan juntos o nada."""
    from app.services import sales as sales_service

    original = sales_service.post_movement
    calls = {"n": 0}

    def failing(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("falla simulada")
        return original(*args, **kwargs)

    monkeypatch.setattr(sales_service, "post_movement", failing)
    fitting, hose = products
    with pytest.raises(RuntimeError):
        sale_of(counter, make_sale, [(fitting, "1"), (hose, "1")])
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Sale)) == 0
    assert db.scalar(select(func.count()).select_from(Payment)) == 0
    assert db.scalar(select(func.count()).select_from(OutboxOperation)) == 1  # solo la apertura
    assert db.get(Product, fitting.id).stock == Decimal("10.00")
    _ = client


def test_almacen_no_vende(products, make_user, auth_headers, make_device, client) -> None:
    from tests.conftest import device_headers, operation

    _, token = make_device()
    headers = device_headers(auth_headers(make_user(Role.WAREHOUSE)), token)
    response = client.post(
        "/api/v1/sync/operations", json=operation("sale.create", {}), headers=headers
    )
    assert response.status_code == 403


def test_sin_costos_para_el_vendedor(counter, products, make_sale) -> None:
    """Principio IV: la respuesta al Vendedor no trae costos ni márgenes."""
    sale = sale_of(counter, make_sale, [(products[0], "1")])
    text = str(sale)
    assert "cost" not in text and "margin" not in text


def test_admin_recibe_costo_y_margen(
    make_user, auth_headers, make_device, make_rate, open_cash_session, products, make_sale
) -> None:
    make_rate(business_date(clock.utcnow()), "36.50")
    admin = make_user(Role.ADMIN)
    headers = auth_headers(admin)
    _, token = make_device()
    session = open_cash_session(headers, token)
    sale = make_sale(headers, token, session["id"], [(products[0], "2")])
    assert sale["items"][0]["unit_cost_usd"] == "1.500000"
    assert sale["items"][0]["margin_usd"] == "3.50"
    assert sale["margin_usd"] == "3.50"


_ = TestClient


def test_reenvio_con_otro_rol_no_muestra_costos(
    make_user, auth_headers, make_device, make_rate, open_cash_session, products, make_sale
) -> None:
    """Hallazgo del code review: una venta del Admin reenviada con la sesión de un Vendedor
    se responde con el esquema del Vendedor (principio IV)."""
    make_rate(business_date(clock.utcnow()), "36.50")
    admin_headers = auth_headers(make_user(Role.ADMIN))
    seller_headers = auth_headers(make_user(Role.SELLER))
    _, token = make_device()
    session = open_cash_session(admin_headers, token)
    op_id, sale_id = str(uuid.uuid7()), str(uuid.uuid7())
    first = make_sale(
        admin_headers, token, session["id"], [(products[0], "1")], op_id=op_id, sale_id=sale_id
    )
    assert "margin_usd" in first
    again = make_sale(
        seller_headers,
        token,
        session["id"],
        [(products[0], "1")],
        op_id=op_id,
        sale_id=sale_id,
        seller_id=first["seller"]["id"],
        sequence_number=1,
    )
    assert again["number"] == first["number"]
    assert "cost" not in str(again) and "margin" not in str(again)


def test_unidad_escrita_debe_corresponder_al_producto(counter, products, make_sale) -> None:
    """Hallazgo del code review: `cm` en un producto por unidad, o `unit` en uno por metro,
    se rechaza (RF-21)."""
    fitting, hose = products
    body = sale_of(counter, make_sale, [(fitting, "1", "cm")], expect=422)
    assert "payload.items.0.entered_unit" in body["detail"]["fields"]
    body = sale_of(counter, make_sale, [(hose, "1", "unit")], expect=422)
    assert "payload.items.0.entered_unit" in body["detail"]["fields"]


def test_monto_que_desborda_es_un_rechazo(counter, make_product, make_sale) -> None:
    """Hallazgo del code review: una cantidad absurda no produce un 500 que trabe la cola."""
    product = make_product("CON", sale_price="200.00")
    body = sale_of(
        counter,
        make_sale,
        [(product, "10000000000")],
        payments=[("cash_usd", "1.00", None)],
        device_total_usd="1.00",
        expect=422,
    )
    assert body["detail"]["code"] == "validation_error"


def test_equipo_revocado(client, counter, products, make_sale, make_user, db) -> None:
    """Hallazgo del code review: un equipo revocado no abre caja aunque la operación diga
    ser anterior; sus ventas de una caja abierta antes de revocarlo se aceptan con alerta,
    y las posteriores a la revocación se rechazan."""
    from datetime import timedelta

    from app.db.models import Alert
    from app.services.devices import revoke_device
    from tests.conftest import device_headers, operation

    admin = make_user(Role.ADMIN)
    revoke_device(db, actor=admin, device_id=counter.device.id)
    db.commit()
    revoked_at = db.get(Device, counter.device.id).revoked_at

    early = operation(
        "cash_session.open",
        {"id": str(uuid.uuid7()), "opening_float_ves": "0", "opening_float_usd": "0"},
    )
    early["created_at"] = (revoked_at - timedelta(hours=1)).isoformat()
    response = client.post(
        "/api/v1/sync/operations",
        json=early,
        headers=device_headers(counter.headers, counter.token),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "device_revoked"

    # make_sale fecha la operación con la hora actual (posterior a la revocación): rechazo.
    body = sale_of(counter, make_sale, [(products[0], "1")], expect=403)
    assert body["detail"]["code"] == "device_revoked"

    # Una venta hecha antes de revocar (caja abierta antes) se acepta con alerta.
    from app.core import clock as app_clock

    app_clock.advance(-(app_clock.utcnow() - revoked_at) - timedelta(minutes=1))
    sale = sale_of(counter, make_sale, [(products[0], "1")])
    assert "revoked_device_sync" in sale["alerts_created"]
    db.expire_all()
    assert db.scalars(select(Alert).where(Alert.type == "revoked_device_sync")).one()
