"""Numeración entre equipos: dos equipos que venden a la vez no repiten números (RN-11/
SC-005; ADR-0003, research R5)."""

import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import clock
from app.db.models import Sale
from app.domain.business_time import business_date
from app.domain.roles import Role
from app.main import app

pytestmark = pytest.mark.db

SALES_PER_DEVICE = 50


def test_dos_equipos_en_paralelo_sin_numeros_repetidos(
    make_user,
    auth_headers,
    make_device,
    make_rate,
    open_cash_session,
    make_product,
    give_stock,
    make_sale,
    db,
) -> None:
    make_rate(business_date(clock.utcnow()), "36.50")
    product = make_product("CON", sale_price="1.00")
    give_stock(product, "1000")
    counters = []
    for name in ("Mostrador", "Tablet"):
        seller = make_user(Role.SELLER)
        headers = auth_headers(seller)
        _, token = make_device(name)
        session = open_cash_session(headers, token)
        counters.append((headers, token, session["id"]))

    errors: list[str] = []

    def sell(headers: dict[str, str], token: str, session_id: str) -> None:
        # Cada hilo con su cliente: las ventas de los dos equipos se cruzan en el servidor.
        local = TestClient(app)
        for number in range(1, SALES_PER_DEVICE + 1):
            try:
                make_sale_with(local, headers, token, session_id, number)
            except AssertionError as exc:  # pragma: no cover - se informa abajo
                errors.append(str(exc))

    def make_sale_with(local, headers, token, session_id, number) -> None:
        # make_sale usa el cliente de la prueba; aquí se arma igual pero con el del hilo.
        import uuid

        from tests.conftest import device_headers, operation

        payload = {
            "id": str(uuid.uuid7()),
            "sequence_number": number,
            "cash_session_id": session_id,
            "seller_id": local.get("/api/v1/auth/me", headers=headers).json()["user"]["id"],
            "occurred_at": clock.utcnow().isoformat(),
            "exchange_rate": "36.50000000",
            "exchange_rate_date": business_date(clock.utcnow()).isoformat(),
            "customer": None,
            "customer_id": None,
            "items": [
                {
                    "id": str(uuid.uuid7()),
                    "product_id": str(product.id),
                    "quantity": "1",
                    "entered_unit": "unit",
                    "unit_price_usd": "1.00",
                    "discount": None,
                }
            ],
            "discount": None,
            "payments": [{"method": "cash_usd", "amount": "1.00", "reference": None}],
            "change": [],
            "device_total_usd": "1.00",
        }
        response = local.post(
            "/api/v1/sync/operations",
            json=operation("sale.create", payload),
            headers=device_headers(headers, token),
        )
        assert response.status_code == 200, response.text

    threads = [threading.Thread(target=sell, args=counter) for counter in counters]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    db.expire_all()
    numbers = db.scalars(select(Sale.number)).all()
    assert len(numbers) == len(set(numbers)) == 2 * SALES_PER_DEVICE
    assert db.scalar(select(func.count()).select_from(Sale).where(Sale.series == "A")) == 50
    assert db.scalar(select(func.count()).select_from(Sale).where(Sale.series == "B")) == 50
    _ = make_sale
