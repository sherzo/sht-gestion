"""Conteo físico: el Almacén anota a ciegas y solo el Admin aplica (RF-12, RN-19; FR-024 a
FR-027, FR-025a, FR-034; SC-005, SC-007; research R8)."""

import threading
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db.models import Product, StockMovement
from app.domain.roles import Role
from tests.helpers import audit_entries

pytestmark = pytest.mark.db

COUNTS = "/api/v1/stock-counts"


@pytest.fixture
def actors(make_user, auth_headers):
    admin = make_user(Role.ADMIN, username="dueno")
    warehouse = make_user(Role.WAREHOUSE, username="almacen")
    seller = make_user(Role.SELLER, username="vendedor")
    return {
        "admin": auth_headers(admin),
        "warehouse": auth_headers(warehouse),
        "seller": auth_headers(seller),
    }


@pytest.fixture
def ferrules(make_product, give_stock):
    """Tres ferrules con stock 10, 5 y 8."""
    products = []
    for stock in ("10", "5", "8"):
        product = make_product("FER")
        give_stock(product, stock)
        products.append(product)
    return products


def _open(client, headers, scope, notes=None):
    body = {"scope": scope}
    if notes:
        body["notes"] = notes
    return client.post(COUNTS, json=body, headers=headers)


def _lines(count) -> dict[str, dict]:
    return {line["product"]["sku"]: line for line in count["lines"]}


def _record(client, headers, count_id, line_id, quantity):
    return client.put(
        f"{COUNTS}/{count_id}/lines/{line_id}", json={"counted_quantity": quantity}, headers=headers
    )


def _stock(db, product) -> Decimal:
    db.expire_all()
    return db.scalar(select(Product.stock).where(Product.id == product.id))


def test_alcances_del_conteo(
    client, actors, ferrules, make_product, give_stock, category_id
) -> None:
    """FR-024, FR-007: por categoría y de todo entran los activos y los inactivos con
    stock; por productos, los elegidos aunque estén inactivos."""
    inactive_with_stock = make_product("FER", is_active=False)
    give_stock(inactive_with_stock, "2")
    inactive_empty = make_product("FER", is_active=False)
    headers = actors["warehouse"]

    by_category = _open(
        client, headers, {"type": "categories", "ids": [str(category_id("FER"))]}
    ).json()
    skus = set(_lines(by_category))
    assert {product.sku for product in ferrules} | {inactive_with_stock.sku} == skus
    assert inactive_empty.sku not in skus
    client.post(f"{COUNTS}/{by_category['id']}/cancel", json={"reason": "Prueba"}, headers=headers)

    chosen = _open(client, headers, {"type": "products", "ids": [str(inactive_empty.id)]})
    assert chosen.status_code == 201
    assert set(_lines(chosen.json())) == {inactive_empty.sku}
    client.post(f"{COUNTS}/{chosen.json()['id']}/cancel", json={"reason": "x"}, headers=headers)

    everything = _open(client, headers, {"type": "all"}).json()
    assert inactive_with_stock.sku in _lines(everything)
    assert inactive_empty.sku not in _lines(everything)


def test_un_producto_en_dos_conteos_abiertos(client, actors, ferrules, category_id) -> None:
    """US5 escenario 7: no se abre otro conteo que incluya un producto ya en conteo."""
    headers = actors["warehouse"]
    _open(client, headers, {"type": "products", "ids": [str(ferrules[0].id)]})
    response = _open(client, headers, {"type": "categories", "ids": [str(category_id("FER"))]})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "product_in_open_count"
    assert response.json()["detail"]["skus"] == [ferrules[0].sku]


def test_aperturas_simultaneas(client, make_user, auth_headers, ferrules, category_id) -> None:
    """FR-024: con dos aperturas a la vez sobre los mismos productos, solo una gana."""
    users = [make_user(Role.WAREHOUSE, username=f"almacen{index}") for index in range(2)]
    headers = [auth_headers(user) for user in users]
    scope = {"type": "categories", "ids": [str(category_id("FER"))]}
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def worker(index: int) -> None:
        barrier.wait()
        statuses.append(_open(client, headers[index], scope).status_code)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(statuses) == [201, 409]


def test_conteo_a_ciegas_y_aplicado_por_el_admin(client, actors, ferrules, db) -> None:
    """US5 escenarios 1 a 3, 8; SC-005: el Almacén anota sin ver el stock, marca listo y no
    puede aplicar; el Admin ve las diferencias y aplica un ajuste por diferencia."""
    warehouse, admin = actors["warehouse"], actors["admin"]
    count = _open(
        client, warehouse, {"type": "products", "ids": [str(p.id) for p in ferrules]}
    ).json()
    lines = _lines(count)
    for line in count["lines"]:
        assert "expected_quantity" not in line and "difference" not in line
    first, second, third = ferrules
    _record(client, warehouse, count["id"], lines[first.sku]["id"], "12")
    _record(client, warehouse, count["id"], lines[second.sku]["id"], "4")
    blind = _record(client, warehouse, count["id"], lines[third.sku]["id"], "8")
    assert blind.status_code == 200
    assert "expected_quantity" not in blind.json() and "difference" not in blind.json()
    detail = client.get(f"{COUNTS}/{count['id']}", headers=warehouse).json()
    assert "lines_with_difference" not in detail
    assert all("expected_quantity" not in line for line in detail["lines"])

    assert client.post(f"{COUNTS}/{count['id']}/ready", headers=warehouse).status_code == 200
    assert (
        client.post(f"{COUNTS}/{count['id']}/apply", json={}, headers=warehouse).status_code == 403
    )
    late = _record(client, warehouse, count["id"], lines[first.sku]["id"], "13")
    assert late.status_code == 409

    review = client.get(f"{COUNTS}/{count['id']}", headers=admin).json()
    reviewed = _lines(review)
    assert reviewed[first.sku]["expected_quantity"] == "10"
    assert reviewed[first.sku]["difference"] == "2"
    assert reviewed[second.sku]["difference"] == "-1"
    assert reviewed[third.sku]["difference"] == "0"
    assert review["lines_with_difference"] == 2

    applied = client.post(f"{COUNTS}/{count['id']}/apply", json={}, headers=admin)
    assert applied.status_code == 200, applied.text
    assert applied.json()["adjustments"] == 2
    assert applied.json()["count"]["status"] == "applied"
    assert _stock(db, first) == Decimal("12")
    assert _stock(db, second) == Decimal("4")
    movements = list(
        db.scalars(select(StockMovement).where(StockMovement.reference_type == "stock_count_line"))
    )
    assert len(movements) == 2
    assert {movement.adjustment_reason for movement in movements} == {"physical_count"}

    # Cada ajuste del conteo queda auditado con el stock antes y después (SC-007).
    adjustments = audit_entries(db, "inventory.adjustment_applied")
    by_sku = {entry.details["sku"]: entry for entry in adjustments}
    assert by_sku[first.sku].before == {"stock": "10"} and by_sku[first.sku].after == {
        "stock": "12"
    }
    assert by_sku[first.sku].details["stock_count_id"] == count["id"]
    [summary] = audit_entries(db, "stock_count.applied")
    assert summary.details["adjustments"] == 2


def test_diferencia_contra_el_stock_al_anotar(client, actors, ferrules, give_stock, db) -> None:
    """US5 escenario 5, FR-025: un movimiento entre la anotación y la aplicación se
    conserva; se aplica la diferencia calculada al anotar."""
    product = ferrules[0]
    count = _open(client, actors["warehouse"], {"type": "products", "ids": [str(product.id)]})
    count = count.json()
    _record(client, actors["warehouse"], count["id"], count["lines"][0]["id"], "9")
    give_stock(product, "3")  # entra mercancía después de contar: stock 13
    client.post(f"{COUNTS}/{count['id']}/apply", json={}, headers=actors["admin"])
    assert _stock(db, product) == Decimal("12")


def test_anotar_de_nuevo_toma_el_stock_del_momento(client, actors, ferrules, give_stock) -> None:
    product = ferrules[1]
    count = _open(client, actors["warehouse"], {"type": "products", "ids": [str(product.id)]})
    count = count.json()
    line_id = count["lines"][0]["id"]
    _record(client, actors["warehouse"], count["id"], line_id, "5")
    give_stock(product, "2")
    _record(client, actors["warehouse"], count["id"], line_id, "7")
    [line] = client.get(f"{COUNTS}/{count['id']}", headers=actors["admin"]).json()["lines"]
    assert line["expected_quantity"] == "7"
    assert line["difference"] == "0"


def test_decimales_segun_la_unidad(client, actors, make_product) -> None:
    hose = make_product("MAN")
    piece = make_product("CON")
    count = _open(
        client, actors["warehouse"], {"type": "products", "ids": [str(hose.id), str(piece.id)]}
    ).json()
    lines = _lines(count)
    assert (
        _record(
            client, actors["warehouse"], count["id"], lines[hose.sku]["id"], "3.305"
        ).status_code
        == 422
    )
    assert (
        _record(client, actors["warehouse"], count["id"], lines[piece.sku]["id"], "1.5").status_code
        == 422
    )
    assert (
        _record(client, actors["warehouse"], count["id"], lines[piece.sku]["id"], "-1").status_code
        == 422
    )
    ok = _record(client, actors["warehouse"], count["id"], lines[hose.sku]["id"], "3.30")
    assert ok.json()["counted_quantity"] == "3.30"


def test_productos_sin_anotar(client, actors, ferrules, db) -> None:
    """US5 escenario 6: se advierte cuántos quedan sin contar y no se ajustan."""
    count = _open(
        client, actors["warehouse"], {"type": "products", "ids": [str(p.id) for p in ferrules]}
    ).json()
    line = _lines(count)[ferrules[0].sku]
    _record(client, actors["warehouse"], count["id"], line["id"], "1")
    warned = client.post(f"{COUNTS}/{count['id']}/apply", json={}, headers=actors["admin"])
    assert warned.status_code == 409
    assert warned.json()["detail"]["code"] == "uncounted_lines"
    assert warned.json()["detail"]["uncounted"] == 2
    applied = client.post(
        f"{COUNTS}/{count['id']}/apply",
        json={"acknowledge_uncounted": True},
        headers=actors["admin"],
    )
    assert applied.json()["adjustments"] == 1
    assert _stock(db, ferrules[1]) == Decimal("5")


def test_saldo_negativo_se_permite_e_informa(client, actors, ferrules, give_stock, db) -> None:
    """FR-026: el ajuste por conteo se aplica aunque quede negativo por salidas
    posteriores a la anotación, y se informa."""
    product = ferrules[1]  # stock 5
    count = _open(client, actors["warehouse"], {"type": "products", "ids": [str(product.id)]})
    count = count.json()
    _record(client, actors["warehouse"], count["id"], count["lines"][0]["id"], "1")  # dif −4
    give_stock(product, "-3")  # salida posterior: stock 2
    applied = client.post(f"{COUNTS}/{count['id']}/apply", json={}, headers=actors["admin"]).json()
    assert _stock(db, product) == Decimal("-2")
    assert [item["sku"] for item in applied["negative_products"]] == [product.sku]


def test_devolver_y_cancelar(client, actors, ferrules, db) -> None:
    """FR-025a, US5 escenario 4: el Admin devuelve a abierto; cancelar exige motivo, no
    genera movimientos y libera los productos para otro conteo."""
    warehouse, admin = actors["warehouse"], actors["admin"]
    scope = {"type": "products", "ids": [str(ferrules[0].id)]}
    count = _open(client, warehouse, scope).json()
    client.post(f"{COUNTS}/{count['id']}/ready", headers=warehouse)
    assert client.post(f"{COUNTS}/{count['id']}/reopen", headers=warehouse).status_code == 403
    # El Almacén no cancela un conteo listo para revisión: lo decide el Admin.
    blocked = client.post(f"{COUNTS}/{count['id']}/cancel", json={"reason": "x"}, headers=warehouse)
    assert blocked.status_code == 403
    reopened = client.post(f"{COUNTS}/{count['id']}/reopen", headers=admin)
    assert reopened.json()["status"] == "open"

    no_reason = client.post(f"{COUNTS}/{count['id']}/cancel", json={}, headers=warehouse)
    assert no_reason.status_code == 422
    cancelled = client.post(
        f"{COUNTS}/{count['id']}/cancel", json={"reason": "Se contó mal"}, headers=warehouse
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert (
        db.scalar(select(StockMovement.id).where(StockMovement.reference_type.isnot(None))) is None
    )
    assert _open(client, warehouse, scope).status_code == 201

    [entry] = audit_entries(db, "stock_count.cancelled")
    assert entry.reason == "Se contó mal"
    assert len(audit_entries(db, "stock_count.returned")) == 1


def test_cerrado_no_se_modifica(client, actors, ferrules, db) -> None:
    """FR-027: un conteo aplicado o cancelado no cambia, ni por la API ni en la base."""
    admin = actors["admin"]
    count = _open(client, admin, {"type": "products", "ids": [str(ferrules[0].id)]}).json()
    line_id = count["lines"][0]["id"]
    _record(client, admin, count["id"], line_id, "10")
    client.post(f"{COUNTS}/{count['id']}/apply", json={}, headers=admin)
    assert _record(client, admin, count["id"], line_id, "11").status_code == 409
    assert (
        client.post(
            f"{COUNTS}/{count['id']}/cancel", json={"reason": "x"}, headers=admin
        ).status_code
        == 409
    )
    with pytest.raises(DBAPIError, match="no se modifica"):
        db.execute(text("UPDATE stock_count SET notes = 'x' WHERE id = :id"), {"id": count["id"]})
    db.rollback()
    with pytest.raises(DBAPIError, match="no se modifica"):
        db.execute(
            text("UPDATE stock_count_line SET counted_quantity = 1 WHERE id = :id"),
            {"id": line_id},
        )
    db.rollback()


def test_no_se_anota_en_la_base_con_el_conteo_en_revision(client, actors, ferrules, db) -> None:
    """R8: el trigger solo deja anotar con el conteo abierto."""
    warehouse = actors["warehouse"]
    count = _open(client, warehouse, {"type": "products", "ids": [str(ferrules[0].id)]}).json()
    client.post(f"{COUNTS}/{count['id']}/ready", headers=warehouse)
    with pytest.raises(DBAPIError, match="Solo se anota con el conteo abierto"):
        db.execute(
            text("UPDATE stock_count_line SET counted_quantity = 3 WHERE id = :id"),
            {"id": count["lines"][0]["id"]},
        )
    db.rollback()


def test_auditoria_y_lista(client, actors, ferrules, db) -> None:
    """FR-034: apertura, paso a revisión y aplicación quedan auditados; la lista muestra el
    avance."""
    admin = actors["admin"]
    count = _open(client, actors["warehouse"], {"type": "all"}, notes="Inventario inicial").json()
    _record(client, actors["warehouse"], count["id"], count["lines"][0]["id"], "1")
    client.post(f"{COUNTS}/{count['id']}/ready", headers=actors["warehouse"])
    [item] = client.get(COUNTS, headers=admin).json()
    assert item["lines_total"] == 3 and item["lines_counted"] == 1
    assert item["notes"] == "Inventario inicial"
    assert len(audit_entries(db, "stock_count.opened")) == 1
    assert len(audit_entries(db, "stock_count.ready")) == 1


def test_vendedor_sin_acceso(client, actors) -> None:
    assert client.get(COUNTS, headers=actors["seller"]).status_code == 403
    assert _open(client, actors["seller"], {"type": "all"}).status_code == 403
