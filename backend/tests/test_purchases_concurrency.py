"""Confirmaciones simultáneas: mismo resultado que en serie, números sin repetir y sin
bloqueos cruzados; una compra de 200 líneas se confirma rápido (RF-16/FR-014, SC-006;
research R3, R13)."""

import threading
import time
import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import AppUser, Product, Purchase
from app.db.session import get_sessionmaker
from app.domain.costing import weighted_average
from app.domain.roles import Role
from app.services.purchases import confirm_purchase

pytestmark = pytest.mark.db


def run_in_threads(
    jobs: list[tuple[uuid.UUID, datetime]], actor_id: uuid.UUID
) -> list[BaseException]:
    barrier = threading.Barrier(len(jobs), timeout=30)
    errors: list[BaseException] = []

    def worker(purchase_id: uuid.UUID, updated_at: datetime) -> None:
        try:
            # La barrera va antes de la primera consulta: la sesión todavía no tomó una
            # conexión del pool, así no se agota mientras los hilos esperan.
            with get_sessionmaker()() as session:
                barrier.wait()
                actor = session.get(AppUser, actor_id)
                confirm_purchase(
                    session, actor=actor, purchase_id=purchase_id, updated_at=updated_at
                )
        except BaseException as exc:  # noqa: BLE001 - se informan todas al final
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=job) for job in jobs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return errors


def test_veinte_confirmaciones_del_mismo_producto(
    make_user, auth_headers, make_supplier, make_product, make_purchase, db
) -> None:
    user = make_user(Role.WAREHOUSE, username="almacen")
    headers = auth_headers(user)
    supplier = make_supplier()
    product = make_product("FRT")
    drafts = [
        make_purchase(headers, supplier, [(product, "2", str(index + 1))]) for index in range(20)
    ]
    errors = run_in_threads(
        [(uuid.UUID(d["id"]), datetime.fromisoformat(d["updated_at"])) for d in drafts], user.id
    )
    assert not errors, errors

    db.expire_all()
    confirmed = db.scalars(select(Purchase).order_by(Purchase.number)).all()
    assert [p.number for p in confirmed] == [f"C-{n:06d}" for n in range(1, 21)]
    # Aplicar el promedio en el orden de los números da el mismo costo (serializable).
    costs = {d["id"]: Decimal(d["items"][0]["landed_unit_cost_usd"]) for d in drafts}
    stock, cost = Decimal("0"), None
    for purchase in confirmed:
        cost = weighted_average(stock, cost, Decimal("2"), costs[str(purchase.id)])
        stock += 2
    final = db.get(Product, product.id)
    assert final.stock == Decimal("40")
    assert final.avg_cost_usd == cost


def test_dos_compras_con_productos_en_orden_inverso(
    make_user, auth_headers, make_supplier, make_product, make_purchase, db
) -> None:
    user = make_user(Role.WAREHOUSE, username="almacen")
    headers = auth_headers(user)
    supplier = make_supplier()
    a, b = make_product("FRT"), make_product("FRT")
    first = make_purchase(headers, supplier, [(a, "1", "1"), (b, "1", "1")])
    second = make_purchase(headers, supplier, [(b, "1", "2"), (a, "1", "2")])
    jobs = [(uuid.UUID(d["id"]), datetime.fromisoformat(d["updated_at"])) for d in (first, second)]
    assert not run_in_threads(jobs, user.id)
    db.expire_all()
    assert db.get(Product, a.id).stock == Decimal("2")
    assert db.get(Product, b.id).stock == Decimal("2")


def test_doscientas_lineas_en_menos_de_cinco_segundos(
    client, make_user, auth_headers, make_supplier, make_product, make_purchase
) -> None:
    headers = auth_headers(make_user(Role.ADMIN, username="dueno"))
    supplier = make_supplier()
    products = [make_product("FRT") for _ in range(200)]
    purchase = make_purchase(headers, supplier, [(p, "3", "1.50") for p in products])
    start = time.perf_counter()
    response = client.post(
        f"/api/v1/purchases/{purchase['id']}/confirm",
        json={"updated_at": purchase["updated_at"]},
        headers=headers,
    )
    elapsed = time.perf_counter() - start
    assert response.status_code == 200, response.text
    assert elapsed < 5, f"Confirmar 200 líneas tardó {elapsed:.2f} s"
