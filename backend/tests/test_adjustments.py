"""Ajustes de inventario con motivo y aprobación de las salidas del Almacén (RF-08 a RF-10;
RN-19; FR-019, FR-019a, FR-019b, FR-020; SC-005a, SC-007; research R7)."""

from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db.models import AdjustmentRequest, Product, StockMovement
from app.domain.roles import Role
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

ADJUSTMENTS = "/api/v1/inventory/adjustments"
REQUESTS = "/api/v1/inventory/adjustment-requests"


@pytest.fixture
def actors(make_user, auth_headers):
    users = {
        "admin": make_user(Role.ADMIN, username="dueno"),
        "seller": make_user(Role.SELLER, username="vendedor"),
        "warehouse": make_user(Role.WAREHOUSE, username="almacen"),
        "warehouse2": make_user(Role.WAREHOUSE, username="almacen2"),
    }
    return {name: (user, auth_headers(user)) for name, user in users.items()}


@pytest.fixture
def stocked(make_product, give_stock):
    """Una conexión (unidades) con stock 10."""
    product = make_product("CON")
    give_stock(product, "10")
    return product


def _adjust(client, headers, product, delta: str, reason="damage", note=None):
    body = {"product_id": str(product.id), "quantity_delta": delta, "reason": reason}
    if note is not None:
        body["note"] = note
    return client.post(ADJUSTMENTS, json=body, headers=headers)


def _stock(db, product) -> Decimal:
    db.expire_all()
    return db.scalar(select(Product.stock).where(Product.id == product.id))


def test_ajuste_del_admin_se_aplica(client, actors, stocked, db) -> None:
    """US2 escenario 1: el ajuste del Admin genera el movimiento con su saldo."""
    response = _adjust(client, actors["admin"][1], stocked, "-2", "damage", "Se rompió la rosca")
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "applied"
    movement = data["movement"]
    assert movement["quantity_delta"] == "-2"
    assert movement["balance_after"] == "8"
    assert movement["adjustment_reason"] == "damage"
    assert movement["note"] == "Se rompió la rosca"
    assert movement["created_by"]["full_name"] == actors["admin"][0].full_name
    assert _stock(db, stocked) == Decimal("8")
    [entry] = audit_entries(db, "inventory.adjustment_applied")
    assert entry.before == {"stock": "10"}
    assert entry.after == {"stock": "8"}
    assert entry.details["quantity_delta"] == "-2"
    assert entry.details["reason"] == "damage"


def test_entrada_del_almacen_se_aplica(client, actors, stocked, db) -> None:
    """US2 escenario 4: los ajustes positivos del Almacén se aplican de inmediato."""
    response = _adjust(client, actors["warehouse"][1], stocked, "3", "correction")
    assert response.status_code == 201
    assert response.json()["status"] == "applied"
    assert _stock(db, stocked) == Decimal("13")


def test_salida_del_almacen_queda_pendiente_y_el_admin_la_aprueba(
    client, actors, stocked, db
) -> None:
    """US2 escenarios 2 y 3, SC-005a: la salida del Almacén no cambia el stock hasta que
    el Admin la aprueba; el movimiento guarda quién solicitó y quién aprobó."""
    warehouse, warehouse_headers = actors["warehouse"]
    admin, admin_headers = actors["admin"]
    response = _adjust(client, warehouse_headers, stocked, "-2", "loss")
    assert response.status_code == 202
    request = response.json()["request"]
    assert request["status"] == "pending"
    assert _stock(db, stocked) == Decimal("10")
    assert db.scalar(select(StockMovement.id).where(StockMovement.quantity_delta < 0)) is None

    pending = client.get(REQUESTS, params={"status": "pending"}, headers=admin_headers).json()
    assert [item["id"] for item in pending["items"]] == [request["id"]]

    approved = client.post(f"{REQUESTS}/{request['id']}/approve", headers=admin_headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert _stock(db, stocked) == Decimal("8")
    saved = db.get(AdjustmentRequest, approved.json()["id"])
    movement = db.get(StockMovement, saved.stock_movement_id)
    assert movement.created_by == admin.id
    assert saved.requested_by == warehouse.id
    assert movement.reference_type == "adjustment_request"
    assert movement.reference_id == saved.id

    assert len(audit_entries(db, "inventory.adjustment_requested")) == 1
    [entry] = audit_entries(db, "inventory.adjustment_approved")
    assert entry.before == {"stock": "10"} and entry.after == {"stock": "8"}


def test_aprobar_revalida_el_stock_del_momento(client, actors, stocked, give_stock, db) -> None:
    """Caso borde: si el stock bajó mientras esperaba, el Admin no puede aprobarla."""
    request = _adjust(client, actors["warehouse"][1], stocked, "-8", "loss").json()["request"]
    give_stock(stocked, "-5")
    response = client.post(f"{REQUESTS}/{request['id']}/approve", headers=actors["admin"][1])
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "negative_stock"
    assert _stock(db, stocked) == Decimal("5")


def test_rechazar_exige_motivo(client, actors, stocked, db) -> None:
    """US2 escenario 3: rechazar sin motivo no se permite; con motivo no hay movimiento y
    el Almacén ve el motivo."""
    headers = actors["admin"][1]
    request = _adjust(client, actors["warehouse"][1], stocked, "-2").json()["request"]
    empty = client.post(f"{REQUESTS}/{request['id']}/reject", json={}, headers=headers)
    assert empty.status_code == 422
    missing = client.post(
        f"{REQUESTS}/{request['id']}/reject", json={"reason": " "}, headers=headers
    )
    assert missing.status_code == 422
    rejected = client.post(
        f"{REQUESTS}/{request['id']}/reject",
        json={"reason": "No coincide con el conteo"},
        headers=headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    mine = client.get(REQUESTS, headers=actors["warehouse"][1]).json()["items"]
    assert mine[0]["rejection_reason"] == "No coincide con el conteo"
    assert _stock(db, stocked) == Decimal("10")
    [entry] = audit_entries(db, "inventory.adjustment_rejected")
    assert entry.reason == "No coincide con el conteo"


def test_retirar_solo_la_propia(client, actors, stocked, db) -> None:
    """FR-019a: el Almacén retira su solicitud pendiente; no la de otro."""
    request = _adjust(client, actors["warehouse"][1], stocked, "-2").json()["request"]
    other = client.post(f"{REQUESTS}/{request['id']}/withdraw", headers=actors["warehouse2"][1])
    assert other.status_code == 403
    own = client.post(f"{REQUESTS}/{request['id']}/withdraw", headers=actors["warehouse"][1])
    assert own.status_code == 200
    assert own.json()["status"] == "withdrawn"
    assert len(audit_entries(db, "inventory.adjustment_withdrawn")) == 1


def test_decidir_una_solicitud_ya_decidida(client, actors, stocked) -> None:
    headers = actors["admin"][1]
    request = _adjust(client, actors["warehouse"][1], stocked, "-2").json()["request"]
    client.post(f"{REQUESTS}/{request['id']}/approve", headers=headers)
    again = client.post(f"{REQUESTS}/{request['id']}/reject", json={"reason": "x"}, headers=headers)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "invalid_state"


def test_una_solicitud_decidida_no_se_modifica_en_la_base(client, actors, stocked, db) -> None:
    """R7: el trigger impide volver una solicitud a pendiente o editarla."""
    request = _adjust(client, actors["warehouse"][1], stocked, "-2").json()["request"]
    client.post(f"{REQUESTS}/{request['id']}/approve", headers=actors["admin"][1])
    with pytest.raises(DBAPIError, match="pendiente a un estado final"):
        db.execute(
            text(
                "UPDATE adjustment_request SET status = 'rejected', rejection_reason = 'x' "
                "WHERE id = :id"
            ),
            {"id": request["id"]},
        )
    db.rollback()


@pytest.mark.parametrize(
    ("category", "delta", "reason", "field"),
    [
        ("CON", "0", "damage", "quantity_delta"),
        ("CON", "1.5", "damage", "quantity_delta"),
        ("MAN", "0.305", "correction", "quantity_delta"),
        ("CON", "2", "otro", "reason"),
    ],
)
def test_validaciones_del_ajuste(
    client, actors, make_product, category, delta, reason, field
) -> None:
    """RF-10/FR-019, FR-020, US2 escenarios 5 a 7: motivo obligatorio, sin cero y con los
    decimales de la unidad."""
    product = make_product(category)
    response = _adjust(client, actors["admin"][1], product, delta, reason)
    assert response.status_code == 422
    assert field in response.json()["detail"]["fields"]


def test_sin_motivo(client, actors, stocked) -> None:
    body = {"product_id": str(stocked.id), "quantity_delta": "1"}
    response = client.post(ADJUSTMENTS, json=body, headers=actors["admin"][1])
    assert response.status_code == 422
    assert "reason" in response.json()["detail"]["fields"]


def test_ajuste_que_deja_stock_negativo(client, actors, make_product, give_stock) -> None:
    """US2 escenario 8: un ajuste manual no deja el stock negativo (Admin y Almacén)."""
    product = make_product("CON")
    give_stock(product, "3")
    for name in ("admin", "warehouse"):
        response = _adjust(client, actors[name][1], product, "-5")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "negative_stock"


def test_metro_admite_centimetros(client, actors, make_product, db) -> None:
    """RF-05: +0,50 m en una manguera."""
    product = make_product("MAN")
    response = _adjust(client, actors["admin"][1], product, "0.50", "correction")
    assert response.status_code == 201
    assert response.json()["movement"]["balance_after"] == "0.50"


def test_cada_almacen_ve_solo_sus_solicitudes(client, actors, stocked) -> None:
    """FR-019b: el Almacén ve el estado de sus solicitudes; el Admin, todas."""
    _adjust(client, actors["warehouse"][1], stocked, "-1")
    _adjust(client, actors["warehouse2"][1], stocked, "-2")
    mine = client.get(REQUESTS, headers=actors["warehouse"][1]).json()
    assert [item["quantity_delta"] for item in mine["items"]] == ["-1"]
    everything = client.get(REQUESTS, headers=actors["admin"][1]).json()
    assert everything["total"] == 2


def test_vendedor_no_ajusta_y_almacen_no_decide(client, actors, stocked) -> None:
    """US2 escenario 10."""
    assert _adjust(client, actors["seller"][1], stocked, "1").status_code == 403
    request = _adjust(client, actors["warehouse"][1], stocked, "-1").json()["request"]
    for action in ("approve", "reject"):
        response = client.post(
            f"{REQUESTS}/{request['id']}/{action}",
            json={"reason": "x"},
            headers=actors["warehouse"][1],
        )
        assert response.status_code == 403
