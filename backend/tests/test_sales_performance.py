"""Una venta de 20 líneas con 3 pagos se registra en menos de 1 s (research R16). SC-002
(búsqueda en < 1 s) lo cubre `test_search_performance.py` de la 1.1b."""

import time

import pytest

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db


def test_venta_de_20_lineas_en_menos_de_un_segundo(
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    give_stock,
    make_sale,
) -> None:
    make_rate(business_date(clock.utcnow()), "36.50")
    headers = auth_headers(make_user(Role.SELLER))
    _, token = make_device()
    session = open_cash_session(headers, token)
    products = []
    for _ in range(20):
        product = make_product("CON", sale_price="1.00")
        give_stock(product, "10")
        products.append(product)
    payments = [("cash_usd", "10.00", None), ("zelle", "5.00", "Z-1"), ("cash_ves", "182.50", None)]
    # Calentamiento: la primera petición carga módulos y conexiones.
    make_sale(headers, token, session["id"], [(products[0], "1")])

    started = time.perf_counter()
    sale = make_sale(
        headers, token, session["id"], [(product, "1") for product in products], payments=payments
    )
    elapsed = time.perf_counter() - started
    assert sale["total_usd"] == "20.00"
    assert elapsed < 1.0, f"La venta tardó {elapsed:.2f} s"
