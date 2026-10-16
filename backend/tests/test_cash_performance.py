"""El detalle de una caja con 100 ventas responde en menos de 1 s (research R14; SC-001)."""

import statistics
import time

import pytest

from app.core import clock
from app.domain.business_time import business_date
from app.domain.roles import Role
from tests.conftest import device_headers

pytestmark = pytest.mark.db


def test_detalle_de_caja_con_100_ventas(
    client,
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    give_stock,
    make_sale,
    register_outflow,
) -> None:
    make_rate(business_date(clock.utcnow()), "36.50")
    headers = auth_headers(make_user(Role.SELLER))
    _, token = make_device()
    session = open_cash_session(headers, token, "1000.00", "100.00")
    product = make_product("CON", sale_price="12.00")
    give_stock(product, "500")
    for index in range(100):
        if index % 2:
            payments = [("cash_usd", "15.00", None)]
            change = [("cash_usd", "3.00", None)]
        else:
            payments = [("mobile_payment", "438.00", f"REF{index}")]
            change = []
        make_sale(headers, token, session["id"], [(product, "1")], payments=payments, change=change)
    for _ in range(5):
        assert register_outflow(headers, token, session["id"], amount="1.00").status_code == 200

    request_headers = device_headers(headers, token)
    timings = []
    for _ in range(5):
        start = time.perf_counter()
        response = client.get(f"/api/v1/cash-sessions/{session['id']}", headers=request_headers)
        timings.append(time.perf_counter() - start)
        assert response.status_code == 200
    assert len(response.json()["movements"]) == 150
    assert statistics.median(timings) < 1.0, timings
