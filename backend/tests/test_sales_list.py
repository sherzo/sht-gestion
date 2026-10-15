"""Consulta de ventas: filtros del Admin con costo y margen, el Vendedor solo sus ventas de
hoy (hora de Caracas) y enlaces desde el kardex (FR-045 a FR-049; research R12)."""

from datetime import timedelta

import pytest

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db

URL = "/api/v1/sales"


@pytest.fixture
def scenario(
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    give_stock,
    make_sale,
):
    today = business_date(clock.utcnow())
    make_rate(today - timedelta(days=1), "36.00")
    make_rate(today, "36.50")
    admin_headers = auth_headers(make_user(Role.ADMIN))
    one = make_user(Role.SELLER, full_name="Vendedora Una")
    two = make_user(Role.SELLER, full_name="Vendedor Dos")
    one_headers, two_headers = auth_headers(one), auth_headers(two)
    _, token = make_device()
    session = open_cash_session(one_headers, token)
    product = make_product("CON", sale_price="10.00", avg_cost="6.000000")
    uncosted = make_product("FRT", sale_price="3.00")
    give_stock(product, "100")
    give_stock(uncosted, "100")
    yesterday_sale = make_sale(
        one_headers,
        token,
        session["id"],
        [(product, "1")],
        rate=("36.00000000", today - timedelta(days=1)),
    )
    return {
        "admin": admin_headers,
        "one": one_headers,
        "two": two_headers,
        "one_id": one.id,
        "token": token,
        "session": session["id"],
        "product": product,
        "uncosted": uncosted,
        "today": today,
        "make_sale": make_sale,
        "yesterday_sale": yesterday_sale,
    }


def numbers(response) -> list[str]:
    return [item["number"] for item in response.json()["items"]]


def test_vendedor_solo_ve_sus_ventas_de_hoy(client, scenario, advance_clock, db) -> None:
    make_sale = scenario["make_sale"]
    # La venta de "ayer" se registró con hora de ayer en Caracas.
    from sqlalchemy import text

    # Se simula una venta de ayer sin pasar por las reglas de inmutabilidad, solo aquí.
    db.execute(text("SET LOCAL session_replication_role = replica"))
    db.execute(
        text(
            "UPDATE sale SET business_date = business_date - 1, "
            "occurred_at = occurred_at - interval '1 day' WHERE number = :n"
        ),
        {"n": scenario["yesterday_sale"]["number"]},
    )
    db.commit()
    mine = make_sale(
        scenario["one"], scenario["token"], scenario["session"], [(scenario["product"], "1")]
    )
    other = make_sale(
        scenario["two"], scenario["token"], scenario["session"], [(scenario["product"], "1")]
    )

    seen = client.get(
        URL,
        headers=scenario["one"],
        params={"from": "2000-01-01", "seller_id": str(other["seller"]["id"])},
    )
    assert numbers(seen) == [mine["number"]]
    assert client.get(f"{URL}/{mine['id']}", headers=scenario["one"]).status_code == 200
    assert client.get(f"{URL}/{other['id']}", headers=scenario["one"]).status_code == 404
    assert (
        client.get(f"{URL}/{scenario['yesterday_sale']['id']}", headers=scenario["one"]).status_code
        == 404
    )
    _ = advance_clock


def test_admin_filtra(client, scenario) -> None:
    make_sale = scenario["make_sale"]
    first = make_sale(
        scenario["one"], scenario["token"], scenario["session"], [(scenario["product"], "1")]
    )
    second = make_sale(
        scenario["two"], scenario["token"], scenario["session"], [(scenario["product"], "2")]
    )
    every = client.get(URL, headers=scenario["admin"])
    assert numbers(every)[:2] == [second["number"], first["number"]]
    by_seller = client.get(
        URL, headers=scenario["admin"], params={"seller_id": str(scenario["one_id"])}
    )
    assert second["number"] not in numbers(by_seller)
    by_number = client.get(URL, headers=scenario["admin"], params={"q": second["number"]})
    assert numbers(by_number) == [second["number"]]
    by_date = client.get(
        URL,
        headers=scenario["admin"],
        params={"from": scenario["today"].isoformat(), "to": scenario["today"].isoformat()},
    )
    assert first["number"] in numbers(by_date)
    page = client.get(URL, headers=scenario["admin"], params={"page_size": 1}).json()
    assert page["total"] >= 3 and len(page["items"]) == 1


def test_estados(client, scenario) -> None:
    make_sale = scenario["make_sale"]
    sale = make_sale(
        scenario["one"], scenario["token"], scenario["session"], [(scenario["product"], "1")]
    )
    client.post(
        f"{URL}/{sale['id']}/void", json={"reason": "Prueba de estados"}, headers=scenario["admin"]
    )
    voided = client.get(URL, headers=scenario["admin"], params={"status": "voided"})
    assert numbers(voided) == [sale["number"]]
    assert voided.json()["items"][0]["status"] == "voided"
    registered = client.get(URL, headers=scenario["admin"], params={"status": "registered"})
    assert sale["number"] not in numbers(registered)
    discount = {"type": "amount", "value": "1.00", "authorization_id": None}
    review = make_sale(
        scenario["one"],
        scenario["token"],
        scenario["session"],
        [(scenario["product"], "1", "unit", discount)],
    )
    flagged = client.get(URL, headers=scenario["admin"], params={"status": "needs_review"})
    assert numbers(flagged) == [review["number"]]


def test_costo_y_margen_solo_para_el_admin(client, scenario) -> None:
    make_sale = scenario["make_sale"]
    sale = make_sale(
        scenario["one"],
        scenario["token"],
        scenario["session"],
        [(scenario["product"], "2"), (scenario["uncosted"], "1")],
    )
    detail = client.get(f"{URL}/{sale['id']}", headers=scenario["admin"]).json()
    assert detail["items"][0]["unit_cost_usd"] == "6.000000"
    assert detail["items"][0]["margin_usd"] == "8.00"
    assert detail["items"][1]["margin_usd"] is None
    assert detail["margin_usd"] is None  # una línea sin costo deja el margen total sin calcular
    seller_view = client.get(f"{URL}/{sale['id']}", headers=scenario["one"]).json()
    assert "cost" not in str(seller_view) and "margin" not in str(seller_view)


def test_almacen_sin_acceso(client, scenario, make_user, auth_headers) -> None:
    warehouse = auth_headers(make_user(Role.WAREHOUSE))
    assert client.get(URL, headers=warehouse).status_code == 403


def test_kardex_enlaza_con_la_venta(client, scenario) -> None:
    make_sale = scenario["make_sale"]
    sale = make_sale(
        scenario["one"], scenario["token"], scenario["session"], [(scenario["product"], "1")]
    )
    client.post(
        f"{URL}/{sale['id']}/void", json={"reason": "Prueba del kardex"}, headers=scenario["admin"]
    )
    movements = client.get(
        f"/api/v1/products/{scenario['product'].id}/movements", headers=scenario["admin"]
    ).json()["items"]
    linked = [
        movement
        for movement in movements
        if movement["type"] in ("sale", "sale_void") and movement.get("sale")
    ]
    assert {movement["type"] for movement in linked} == {"sale", "sale_void"}
    assert all(movement["sale"]["number"] for movement in linked)
    assert sale["number"] in {movement["sale"]["number"] for movement in linked}
