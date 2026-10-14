"""Compras en borrador: crear, guardar entero, recalcular, avisos y descartar
(RF-14, RF-15/FR-004 a FR-007, FR-012, FR-029 a FR-031; RN-20; research R4)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core import clock
from app.db.models import StockMovement
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db

URL = "/api/v1/purchases"


def today() -> date:
    return business_date(clock.utcnow())


@pytest.fixture
def warehouse(make_user, auth_headers) -> dict[str, str]:
    return auth_headers(make_user(Role.WAREHOUSE, username="almacen"))


@pytest.fixture
def supplier(make_supplier):
    return make_supplier("Hidráulica Aragua")


def body(supplier, items, **extra) -> dict:
    data = {
        "supplier_id": str(supplier.id),
        "purchase_date": today().isoformat(),
        "currency": "USD",
        "items": [
            {"product_id": str(product.id), "quantity": quantity, "unit_cost": cost}
            for product, quantity, cost in items
        ],
        "charges": [],
    }
    data.update(extra)
    return data


def test_crear_borrador_en_usd(client, warehouse, supplier, make_product, db) -> None:
    hose, fitting = make_product("MAN"), make_product("CON")
    response = client.post(
        URL, json=body(supplier, [(hose, "30", "3.00"), (fitting, "20", "1.25")]), headers=warehouse
    )
    assert response.status_code == 201, response.text
    purchase = response.json()
    assert purchase["status"] == "draft"
    assert purchase["number"] is None
    assert [item["line_total_usd"] for item in purchase["items"]] == ["90.00", "25.00"]
    assert purchase["merchandise_total_usd"] == "115.00"
    assert purchase["charges_total_usd"] == "0.00"
    assert purchase["total_usd"] == "115.00"
    assert [item["landed_unit_cost_usd"] for item in purchase["items"]] == ["3.000000", "1.250000"]
    assert purchase["items"][0]["quantity"] == "30.00"
    assert db.scalar(select(func.count()).select_from(StockMovement)) == 0


def test_guardar_reemplaza_las_lineas(client, warehouse, supplier, make_product) -> None:
    a, b, c = make_product("FRT"), make_product("FRT"), make_product("FRT")
    created = client.post(
        URL, json=body(supplier, [(a, "1", "1"), (b, "2", "2")]), headers=warehouse
    )
    purchase = created.json()
    response = client.put(
        f"{URL}/{purchase['id']}",
        json=body(supplier, [(a, "5", "1"), (c, "1", "10")], updated_at=purchase["updated_at"]),
        headers=warehouse,
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    assert [item["product"]["id"] for item in saved["items"]] == [str(a.id), str(c.id)]
    assert saved["merchandise_total_usd"] == "15.00"
    assert saved["warnings"] == []


def test_guardar_con_datos_viejos_avisa(client, warehouse, supplier, make_product) -> None:
    product = make_product("FRT")
    purchase = client.post(
        URL, json=body(supplier, [(product, "1", "1")]), headers=warehouse
    ).json()
    stale = purchase["updated_at"]
    client.put(
        f"{URL}/{purchase['id']}", json=body(supplier, [(product, "2", "1")]), headers=warehouse
    )
    response = client.put(
        f"{URL}/{purchase['id']}",
        json=body(supplier, [(product, "3", "1")], updated_at=stale),
        headers=warehouse,
    )
    assert response.status_code == 200
    assert [w["code"] for w in response.json()["warnings"]] == ["stale_data"]
    assert response.json()["items"][0]["quantity"] == "3"


@pytest.mark.parametrize(
    ("category", "quantity", "cost"),
    [
        ("FRT", "1.5", "1"),
        ("MAN", "0.305", "1"),
        ("FRT", "0", "1"),
        ("FRT", "1", "0"),
        ("FRT", "1", "1.0000001"),
    ],
)
def test_cantidades_y_costos_invalidos(
    client, warehouse, supplier, make_product, category, quantity, cost
) -> None:
    product = make_product(category)
    response = client.post(URL, json=body(supplier, [(product, quantity, cost)]), headers=warehouse)
    assert response.status_code == 422, response.text


def test_producto_repetido_e_inactivo(client, warehouse, supplier, make_product) -> None:
    product = make_product("FRT")
    repeated = client.post(
        URL, json=body(supplier, [(product, "1", "1"), (product, "2", "1")]), headers=warehouse
    )
    assert repeated.status_code == 422
    assert "items.1.product_id" in repeated.json()["detail"]["fields"]
    inactive = make_product("FRT", is_active=False)
    assert (
        client.post(URL, json=body(supplier, [(inactive, "1", "1")]), headers=warehouse).status_code
        == 422
    )


def test_proveedor_inactivo(client, warehouse, make_supplier, make_product) -> None:
    supplier = make_supplier("Viejo", is_active=False)
    response = client.post(
        URL, json=body(supplier, [(make_product("FRT"), "1", "1")]), headers=warehouse
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "inactive_supplier"


def test_fecha_futura(client, warehouse, supplier, make_product) -> None:
    future = (today() + timedelta(days=1)).isoformat()
    response = client.post(
        URL,
        json=body(supplier, [(make_product("FRT"), "1", "1")], purchase_date=future),
        headers=warehouse,
    )
    assert response.status_code == 422


def test_mas_de_500_lineas(client, warehouse, supplier, make_product) -> None:
    product = make_product("FRT")
    data = body(supplier, [(product, "1", "1")] * 501)
    assert client.post(URL, json=data, headers=warehouse).status_code == 422


def test_factura_duplicada_avisa(client, warehouse, supplier, make_product) -> None:
    product = make_product("FRT")
    client.post(
        URL,
        json=body(supplier, [(product, "1", "1")], supplier_invoice_number="F-100"),
        headers=warehouse,
    )
    response = client.post(
        URL,
        json=body(supplier, [(product, "1", "1")], supplier_invoice_number="f-100"),
        headers=warehouse,
    )
    assert response.status_code == 201
    assert [w["code"] for w in response.json()["warnings"]] == ["duplicate_invoice"]


def test_descartar_borrador(client, warehouse, supplier, make_product, db) -> None:
    purchase = client.post(
        URL, json=body(supplier, [(make_product("FRT"), "1", "1")]), headers=warehouse
    ).json()
    assert client.delete(f"{URL}/{purchase['id']}", headers=warehouse).status_code == 204
    assert client.get(f"{URL}/{purchase['id']}", headers=warehouse).status_code == 404
    assert db.scalar(select(func.count()).select_from(StockMovement)) == 0


def test_no_se_edita_ni_descarta_una_confirmada(
    client, warehouse, supplier, make_product, make_purchase
) -> None:
    product = make_product("FRT")
    purchase = make_purchase(warehouse, supplier, [(product, "1", "1")], confirm=True)
    url = f"{URL}/{purchase['id']}"
    assert (
        client.put(url, json=body(supplier, [(product, "2", "1")]), headers=warehouse).status_code
        == 409
    )
    response = client.delete(url, headers=warehouse)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_state"


# --- Compras en Bs (US3) ---------------------------------------------------------------


def test_compra_en_bs_convierte_con_la_tasa(
    client, warehouse, supplier, make_product, make_rate
) -> None:
    make_rate(today(), "36.50")
    product = make_product("FRT")
    response = client.post(
        URL, json=body(supplier, [(product, "7", "100.00")], currency="VES"), headers=warehouse
    )
    assert response.status_code == 201, response.text
    purchase = response.json()
    item = purchase["items"][0]
    assert item["unit_cost_ves"] == "100.00"
    assert item["unit_cost_usd"] == "2.739726"
    assert item["line_total_ves"] == "700.00"
    assert item["line_total_usd"] == "19.18"
    assert purchase["merchandise_total_ves"] == "700.00"
    assert purchase["exchange_rate"] == "36.50000000"
    assert purchase["exchange_rate_date"] == today().isoformat()


def test_bs_usa_la_ultima_tasa_anterior(
    client, warehouse, supplier, make_product, make_rate
) -> None:
    make_rate(today() - timedelta(days=3), "36.20")
    make_rate(today(), "36.50")
    product = make_product("FRT")
    purchase_date = (today() - timedelta(days=2)).isoformat()
    purchase = client.post(
        URL,
        json=body(
            supplier, [(product, "10", "100.00")], currency="VES", purchase_date=purchase_date
        ),
        headers=warehouse,
    ).json()
    assert purchase["exchange_rate"] == "36.20000000"
    assert purchase["exchange_rate_date"] == (today() - timedelta(days=3)).isoformat()


def test_bs_sin_tasa_y_usd_sin_tasa(client, warehouse, supplier, make_product) -> None:
    product = make_product("FRT")
    response = client.post(
        URL, json=body(supplier, [(product, "1", "100.00")], currency="VES"), headers=warehouse
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "exchange_rate_missing"
    usd = client.post(URL, json=body(supplier, [(product, "1", "1")]), headers=warehouse)
    assert usd.status_code == 201
    assert usd.json()["exchange_rate"] is None


def test_costo_en_bs_con_tres_decimales(
    client, warehouse, supplier, make_product, make_rate
) -> None:
    make_rate(today(), "40")
    product = make_product("FRT")
    response = client.post(
        URL, json=body(supplier, [(product, "1", "100.001")], currency="VES"), headers=warehouse
    )
    assert response.status_code == 422


def test_borrador_en_bs_toma_la_tasa_corregida(
    client, warehouse, supplier, make_product, make_rate, db
) -> None:
    rate = make_rate(today(), "40")
    product = make_product("FRT")
    purchase = client.post(
        URL, json=body(supplier, [(product, "10", "100.00")], currency="VES"), headers=warehouse
    ).json()
    assert purchase["items"][0]["unit_cost_usd"] == "2.500000"
    rate.rate = Decimal("50")
    db.commit()
    saved = client.put(
        f"{URL}/{purchase['id']}",
        json=body(supplier, [(product, "10", "100.00")], currency="VES"),
        headers=warehouse,
    ).json()
    assert saved["items"][0]["unit_cost_usd"] == "2.000000"


# --- Gastos de la compra (US7) ---------------------------------------------------------


def import_charges() -> list[dict]:
    return [
        {"description": "Comisión de compra", "charge_type": "percent", "percent": "10"},
        {
            "description": "Envío China–Venezuela",
            "charge_type": "fixed",
            "amount": "250.00",
            "currency": "USD",
        },
        {
            "description": "Entrega al local",
            "charge_type": "fixed",
            "amount": "3650.00",
            "currency": "VES",
        },
    ]


def test_gastos_de_importacion(client, warehouse, supplier, make_product, make_rate) -> None:
    make_rate(today(), "36.50")
    a, b = make_product("CON"), make_product("CON")
    response = client.post(
        URL,
        json=body(supplier, [(a, "60", "10.00"), (b, "40", "10.00")], charges=import_charges()),
        headers=warehouse,
    )
    assert response.status_code == 201, response.text
    purchase = response.json()
    assert [c["amount_usd"] for c in purchase["charges"]] == ["100.00", "250.00", "100.00"]
    assert purchase["charges_total_usd"] == "450.00"
    assert purchase["total_usd"] == "1450.00"
    assert [i["allocated_charges_usd"] for i in purchase["items"]] == ["270.00", "180.00"]
    assert [i["landed_unit_cost_usd"] for i in purchase["items"]] == ["14.500000", "14.500000"]


def test_reparto_con_residuo(client, warehouse, supplier, make_product) -> None:
    products = [make_product("FRT") for _ in range(3)]
    charges = [
        {"description": "Flete", "charge_type": "fixed", "amount": "100.00", "currency": "USD"}
    ]
    purchase = client.post(
        URL,
        json=body(supplier, [(p, "1", "100") for p in products], charges=charges),
        headers=warehouse,
    ).json()
    assert [i["allocated_charges_usd"] for i in purchase["items"]] == ["33.34", "33.33", "33.33"]


@pytest.mark.parametrize(
    "charge",
    [
        {"description": "X", "charge_type": "percent", "percent": "0"},
        {"description": "X", "charge_type": "percent", "percent": "100.01"},
        {"description": "X", "charge_type": "percent", "percent": "1.001"},
        {"description": "X", "charge_type": "fixed", "amount": "10"},
        {
            "description": "X",
            "charge_type": "fixed",
            "amount": "10",
            "currency": "USD",
            "percent": "5",
        },
        {"description": "X", "charge_type": "percent", "percent": "5", "currency": "USD"},
        {"description": "", "charge_type": "percent", "percent": "5"},
    ],
)
def test_gastos_invalidos(client, warehouse, supplier, make_product, charge) -> None:
    data = body(supplier, [(make_product("FRT"), "1", "1")], charges=[charge])
    assert client.post(URL, json=data, headers=warehouse).status_code == 422


def test_gasto_en_bs_sin_tasa(client, warehouse, supplier, make_product) -> None:
    charges = [
        {"description": "Entrega", "charge_type": "fixed", "amount": "100", "currency": "VES"}
    ]
    response = client.post(
        URL,
        json=body(supplier, [(make_product("FRT"), "1", "1")], charges=charges),
        headers=warehouse,
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "exchange_rate_missing"


def test_gastos_mayores_que_la_factura_avisan(client, warehouse, supplier, make_product) -> None:
    charges = [{"description": "Envío", "charge_type": "fixed", "amount": "20", "currency": "USD"}]
    response = client.post(
        URL,
        json=body(supplier, [(make_product("FRT"), "1", "10")], charges=charges),
        headers=warehouse,
    )
    assert [w["code"] for w in response.json()["warnings"]] == ["charges_over_100_percent"]


def test_cambiar_lineas_recalcula_porcentajes(client, warehouse, supplier, make_product) -> None:
    product = make_product("FRT")
    charges = [{"description": "Comisión", "charge_type": "percent", "percent": "10"}]
    purchase = client.post(
        URL, json=body(supplier, [(product, "1", "100")], charges=charges), headers=warehouse
    ).json()
    assert purchase["charges"][0]["amount_usd"] == "10.00"
    saved = client.put(
        f"{URL}/{purchase['id']}",
        json=body(supplier, [(product, "2", "100")], charges=charges),
        headers=warehouse,
    ).json()
    assert saved["charges"][0]["amount_usd"] == "20.00"
    assert saved["items"][0]["landed_unit_cost_usd"] == "110.000000"


def test_mas_de_20_gastos(client, warehouse, supplier, make_product) -> None:
    charges = [
        {"description": f"G{i}", "charge_type": "percent", "percent": "1"} for i in range(21)
    ]
    data = body(supplier, [(make_product("FRT"), "1", "1")], charges=charges)
    assert client.post(URL, json=data, headers=warehouse).status_code == 422
