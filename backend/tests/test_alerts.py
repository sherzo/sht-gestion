"""Alertas para el Admin (RN-14/FR-018; research R8)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.domain.roles import Role

pytestmark = pytest.mark.db

URL = "/api/v1/alerts"


@pytest.fixture
def admin(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.ADMIN, username="dueno"))


@pytest.fixture
def alert_id(client, admin, make_supplier, make_product, give_stock, make_purchase) -> str:
    """Una anulación que no puede recalcular el costo deja una alerta abierta."""
    product = make_product("FRT", avg_cost="1")
    purchase = make_purchase(admin, make_supplier(), [(product, "5", "2")], confirm=True)
    give_stock(product, "-5")
    client.post(
        f"/api/v1/purchases/{purchase['id']}/void",
        json={"reason": "Factura duplicada"},
        headers=admin,
    )
    return client.get(URL, headers=admin).json()["items"][0]["id"]


def test_listar_y_resolver(client, admin, alert_id) -> None:
    summary = client.get("/api/v1/inventory/summary", headers=admin).json()
    assert summary["open_alerts"] == 1
    response = client.post(f"{URL}/{alert_id}/resolve", headers=admin)
    assert response.status_code == 200
    assert response.json()["resolved_by"] is not None
    assert client.get(URL, headers=admin).json()["total"] == 0
    assert client.get(URL, params={"status": "resolved"}, headers=admin).json()["total"] == 1
    again = client.post(f"{URL}/{alert_id}/resolve", headers=admin)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "invalid_state"


def test_la_alerta_no_se_edita_ni_se_borra(db, alert_id) -> None:
    for statement in (
        "UPDATE alert SET details = '{}' WHERE id = :id",
        "DELETE FROM alert WHERE id = :id",
    ):
        with pytest.raises(DBAPIError):
            db.execute(text(statement), {"id": alert_id})
        db.rollback()
