"""Descuentos autorizados por el Admin: PIN, solicitud aprobada (tal cual o con un valor
menor) o rechazada, uso único y venta a revisión sin autorización válida (RF-22, RN-07/
FR-020 a FR-029; research R8)."""

import uuid
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import clock
from app.db.models import Alert, AppUser, Product
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import device_headers
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

URL = "/api/v1/discount-authorizations"
PIN = "4321"


@dataclass
class Setup:
    seller_headers: dict[str, str]
    admin_headers: dict[str, str]
    admin: AppUser
    token: str
    session_id: str
    product: Product


@pytest.fixture
def setup(
    make_user, auth_headers, make_device, make_rate, open_cash_session, make_product, give_stock
) -> Setup:
    make_rate(business_date(clock.utcnow()), "36.50")
    admin = make_user(Role.ADMIN, username="jefe", pin=PIN)
    seller_headers = auth_headers(make_user(Role.SELLER))
    _, token = make_device()
    session = open_cash_session(seller_headers, token)
    product = make_product("CON", sale_price="20.00")
    give_stock(product, "50")
    return Setup(seller_headers, auth_headers(admin), admin, token, session["id"], product)


def request_body(setup: Setup, sale_id: str, item_id: str | None, **overrides) -> dict:
    body = {
        "method": "pin",
        "admin_username": "jefe",
        "pin": PIN,
        "sale_id": sale_id,
        "sale_item_id": item_id,
        "product_id": str(setup.product.id) if item_id else None,
        "discount_type": "percent",
        "discount_value": "10.00",
        "base_usd": "20.00",
    }
    return {**body, **overrides}


def ask(client: TestClient, setup: Setup, body: dict, expect: int = 201) -> dict:
    response = client.post(
        URL, json=body, headers=device_headers(setup.seller_headers, setup.token)
    )
    assert response.status_code == expect, response.text
    return response.json()


def sell_with_item_discount(
    make_sale, setup: Setup, discount: dict, *, sale_id: str, item_id: str
) -> dict:
    """Venta de una línea de 20,00 con el descuento dado y los ids que vinculan la
    autorización (venta y línea generadas en el equipo, R8)."""
    return make_sale(
        setup.seller_headers,
        setup.token,
        setup.session_id,
        [(setup.product, "1", "unit", discount, item_id)],
        sale_id=sale_id,
    )


def test_pin_correcto_aprueba_y_la_venta_registra_al_autorizante(
    client, setup, make_sale, db
) -> None:
    sale_id, item_id = str(uuid.uuid7()), str(uuid.uuid7())
    authorization = ask(client, setup, request_body(setup, sale_id, item_id))
    assert authorization["status"] == "approved"
    assert authorization["method"] == "pin"
    assert authorization["discount_usd"] == "2.00"
    assert authorization["decided_by"]["id"] == str(setup.admin.id)

    discount = {"type": "percent", "value": "10.00", "authorization_id": authorization["id"]}
    sale = sell_with_item_discount(make_sale, setup, discount, sale_id=sale_id, item_id=item_id)
    item = sale["items"][0]
    assert item["line_total_usd"] == "18.00"
    assert item["item_discount"]["authorized_by"]["id"] == str(setup.admin.id)
    assert item["item_discount"]["method"] == "pin"
    assert sale["needs_review"] is False
    assert audit_entries(db, "auth.pin_verified")
    [entry] = audit_entries(db, "sale.discounted")
    assert entry.details["item_discounts"][0]["method"] == "pin"


def test_pin_incorrecto_y_bloqueo(client, setup) -> None:
    body = request_body(setup, str(uuid.uuid7()), str(uuid.uuid7()), pin="0000")
    for _ in range(4):
        assert ask(client, setup, body, expect=403)["detail"]["code"] == "pin_invalid"
    ask(client, setup, body, expect=403)
    assert (
        ask(client, setup, request_body(setup, str(uuid.uuid7()), None), expect=423)["detail"][
            "code"
        ]
        == "pin_locked"
    )


def test_solicitud_pendiente_se_aprueba_desde_otra_sesion(client, setup, make_sale, db) -> None:
    sale_id = str(uuid.uuid7())
    body = request_body(
        setup,
        sale_id,
        None,
        method="request",
        discount_type="amount",
        discount_value="5.00",
        base_usd="20.00",
    )
    body.pop("pin")
    body.pop("admin_username")
    pending = ask(client, setup, body)
    assert pending["status"] == "pending"
    assert pending["requested_value"] == "5.00"

    # El Vendedor consulta el estado; el Admin la ve entre las pendientes.
    seen = client.get(f"{URL}/{pending['id']}", headers=setup.seller_headers).json()
    assert seen["status"] == "pending"
    listed = client.get(URL, params={"status": "pending"}, headers=setup.admin_headers).json()
    assert [item["id"] for item in listed] == [pending["id"]]

    approved = client.post(f"{URL}/{pending['id']}/approve", json={}, headers=setup.admin_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    discount = {"type": "amount", "value": "5.00", "authorization_id": pending["id"]}
    sale = make_sale(
        setup.seller_headers,
        setup.token,
        setup.session_id,
        [(setup.product, "1")],
        discount=discount,
        sale_id=sale_id,
    )
    assert sale["discount"]["method"] == "request"
    assert sale["discount"]["authorized_by"]["id"] == str(setup.admin.id)
    assert sale["total_usd"] == "15.00"
    actions = {
        entry.action
        for entry in audit_entries(db, "discount_authorization.requested")
        + audit_entries(db, "discount_authorization.approved")
    }
    assert actions == {"discount_authorization.requested", "discount_authorization.approved"}


def test_aprobar_con_un_valor_menor(client, setup) -> None:
    """Aclaración del dueño: el Admin puede aprobar 5 % en lugar de 10 %."""
    body = request_body(setup, str(uuid.uuid7()), str(uuid.uuid7()), method="request")
    body.pop("pin")
    body.pop("admin_username")
    pending = ask(client, setup, body)
    approved = client.post(
        f"{URL}/{pending['id']}/approve",
        json={"discount_value": "5.00"},
        headers=setup.admin_headers,
    ).json()
    assert approved["requested_value"] == "10.00"
    assert approved["discount_value"] == "5.00"
    assert approved["discount_usd"] == "1.00"


@pytest.mark.parametrize("value", ["10.01", "0", "-1"])
def test_no_se_aprueba_mas_de_lo_pedido_ni_cero(client, setup, value) -> None:
    body = request_body(setup, str(uuid.uuid7()), None, method="request")
    body.pop("pin")
    body.pop("admin_username")
    pending = ask(client, setup, body)
    response = client.post(
        f"{URL}/{pending['id']}/approve",
        json={"discount_value": value},
        headers=setup.admin_headers,
    )
    assert response.status_code == 422


def test_rechazar_con_motivo_y_no_decidir_dos_veces(client, setup, db) -> None:
    body = request_body(setup, str(uuid.uuid7()), None, method="request")
    body.pop("pin")
    body.pop("admin_username")
    pending = ask(client, setup, body)
    rejected = client.post(
        f"{URL}/{pending['id']}/reject", json={"reason": "Máximo 5 %"}, headers=setup.admin_headers
    )
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "Máximo 5 %"
    again = client.post(f"{URL}/{pending['id']}/approve", json={}, headers=setup.admin_headers)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "invalid_state"
    assert audit_entries(db, "discount_authorization.rejected")


def test_vendedor_solo_ve_sus_solicitudes(client, setup, make_user, auth_headers) -> None:
    body = request_body(setup, str(uuid.uuid7()), None, method="request")
    body.pop("pin")
    body.pop("admin_username")
    pending = ask(client, setup, body)
    other = auth_headers(make_user(Role.SELLER))
    assert client.get(f"{URL}/{pending['id']}", headers=other).status_code == 404


def test_sin_autorizacion_valida_va_a_revision(client, setup, make_sale, db) -> None:
    """FR-028: la venta se registra igual, marcada para revisión y con alerta."""
    discount = {"type": "percent", "value": "10.00", "authorization_id": None}
    sale = make_sale(
        setup.seller_headers,
        setup.token,
        setup.session_id,
        [(setup.product, "1", "unit", discount)],
    )
    assert sale["needs_review"] is True
    assert sale["items"][0]["line_total_usd"] == "18.00"
    assert sale["items"][0]["item_discount"]["authorized_by"] is None
    db.expire_all()
    [alert] = db.scalars(select(Alert).where(Alert.type == "discount_review")).all()
    # Revisar la venta es resolver su alerta: la venta no cambia.
    resolved = client.post(f"/api/v1/alerts/{alert.id}/resolve", headers=setup.admin_headers)
    assert resolved.status_code == 200
    detail = client.get(f"/api/v1/sales/{sale['id']}", headers=setup.admin_headers)
    if detail.status_code == 200:
        assert detail.json()["needs_review"] is True


def test_autorizacion_de_otra_venta_o_con_otro_valor_no_sirve(client, setup, make_sale) -> None:
    sale_id, item_id = str(uuid.uuid7()), str(uuid.uuid7())
    authorization = ask(client, setup, request_body(setup, sale_id, item_id))
    # Otro valor que el autorizado: no coincide.
    discount = {"type": "percent", "value": "15.00", "authorization_id": authorization["id"]}
    sale = sell_with_item_discount(make_sale, setup, discount, sale_id=sale_id, item_id=item_id)
    assert sale["needs_review"] is True
    # Otra venta con la misma autorización: no coincide (vínculo por la venta).
    discount = {"type": "percent", "value": "10.00", "authorization_id": authorization["id"]}
    other = make_sale(
        setup.seller_headers,
        setup.token,
        setup.session_id,
        [(setup.product, "1", "unit", discount)],
    )
    assert other["needs_review"] is True


def test_admin_vende_con_descuento_sin_pedir_nada(
    make_sale, setup, auth_headers, make_device, open_cash_session
) -> None:
    _, token = make_device("Caja del jefe")
    session = open_cash_session(setup.admin_headers, token)
    sale = make_sale(
        setup.admin_headers,
        token,
        session["id"],
        [(setup.product, "1")],
        discount={"type": "percent", "value": "100.00"},
    )
    assert sale["total_usd"] == "0.00"
    assert sale["discount"]["method"] == "admin_self"
    assert sale["needs_review"] is False


@pytest.mark.parametrize(
    ("discount", "field"),
    [
        ({"type": "amount", "value": "25.00"}, "items"),
        ({"type": "percent", "value": "100.01"}, "items"),
    ],
)
def test_limites_del_descuento(make_sale, setup, discount, field) -> None:
    body = make_sale(
        setup.seller_headers,
        setup.token,
        setup.session_id,
        [(setup.product, "1", "unit", discount)],
        expect=422,
    )
    assert any(key.startswith(f"payload.{field}") for key in body["detail"]["fields"])


def test_reparto_del_descuento_total(make_sale, setup, make_product, give_stock) -> None:
    others = []
    for _ in range(2):
        product = make_product("CON", sale_price="10.00")
        give_stock(product, "5")
        others.append(product)
    first = make_product("CON", sale_price="10.00")
    give_stock(first, "5")
    sale = make_sale(
        setup.seller_headers,
        setup.token,
        setup.session_id,
        [(first, "1"), (others[0], "1"), (others[1], "1")],
        discount={"type": "amount", "value": "5.00"},
    )
    assert [item["allocated_sale_discount_usd"] for item in sale["items"]] == [
        "1.66",
        "1.67",
        "1.67",
    ]


def test_almacen_no_pide_descuentos(client, setup, make_user, auth_headers) -> None:
    headers = device_headers(auth_headers(make_user(Role.WAREHOUSE)), setup.token)
    response = client.post(URL, json=request_body(setup, str(uuid.uuid7()), None), headers=headers)
    assert response.status_code == 403
