"""Consulta de compras y enlace desde el kardex (RF-08/FR-020, FR-021)."""

from datetime import timedelta

import pytest

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db

URL = "/api/v1/purchases"


@pytest.fixture
def setup(client, make_user, auth_headers, make_supplier, make_product, make_purchase):
    admin = auth_headers(make_user(Role.ADMIN, username="dueno"))
    today = business_date(clock.utcnow())
    aragua, china = make_supplier("Hidráulica Aragua"), make_supplier("Proveedor China")
    hose, fitting = make_product("MAN"), make_product("CON")
    old = make_purchase(
        admin, aragua, [(hose, "10", "2")], purchase_date=today - timedelta(days=10), confirm=True
    )
    recent = make_purchase(
        admin, china, [(fitting, "5", "3")], supplier_invoice_number="PI-118", confirm=True
    )
    draft = make_purchase(admin, aragua, [(fitting, "1", "1")])
    client.post(f"{URL}/{old['id']}/void", json={"reason": "Precio equivocado"}, headers=admin)
    return {
        "admin": admin,
        "today": today,
        "aragua": aragua,
        "hose": hose,
        "fitting": fitting,
        "old": old,
        "recent": recent,
        "draft": draft,
    }


def numbers(client, headers, **params) -> list:
    data = client.get(URL, params=params, headers=headers).json()
    return [item["number"] for item in data["items"]]


def test_filtros(client, setup) -> None:
    admin = setup["admin"]
    assert numbers(client, admin, supplier_id=str(setup["aragua"].id)) == [None, "C-000001"]
    assert numbers(client, admin, status="voided") == ["C-000001"]
    assert numbers(client, admin, status="draft") == [None]
    since = (setup["today"] - timedelta(days=2)).isoformat()
    assert numbers(client, admin, **{"from": since, "status": "confirmed"}) == ["C-000002"]
    assert numbers(client, admin, product_id=str(setup["fitting"].id), status="confirmed") == [
        "C-000002"
    ]
    assert numbers(client, admin, q="pi-118") == ["C-000002"]
    assert numbers(client, admin, q="c-000001") == ["C-000001"]
    page = client.get(URL, params={"page_size": 101}, headers=admin)
    assert page.status_code == 422


def test_resumen_de_la_lista(client, setup) -> None:
    item = client.get(URL, params={"status": "confirmed"}, headers=setup["admin"]).json()["items"][
        0
    ]
    assert item["supplier"]["name"] == "Proveedor China"
    assert item["items_count"] == 1
    assert item["total_usd"] == "15.00"


def test_el_kardex_enlaza_la_compra(client, setup) -> None:
    movements = client.get(
        f"/api/v1/products/{setup['hose'].id}/movements", headers=setup["admin"]
    ).json()["items"]
    linked = {(m["type"], m["purchase"]["number"]) for m in movements}
    assert linked == {("purchase", "C-000001"), ("purchase_void", "C-000001")}
