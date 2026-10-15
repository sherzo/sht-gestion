"""Pagos mixtos y vuelto (RF-23 a RF-25; RN-04, RN-06; FR-033 a FR-039; research R1)."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core import clock
from app.db.models import Payment
from app.domain.business_time import business_date
from app.domain.roles import Role

pytestmark = pytest.mark.db


@pytest.fixture
def counter(make_user, auth_headers, make_device, make_rate, open_cash_session):
    make_rate(business_date(clock.utcnow()), "36.50")
    headers = auth_headers(make_user(Role.SELLER))
    _, token = make_device()
    session = open_cash_session(headers, token)
    return headers, token, session["id"]


@pytest.fixture
def product(make_product, give_stock):
    def factory(price: str):
        item = make_product("CON", sale_price=price)
        give_stock(item, "100")
        return item

    return factory


def sell(make_sale, counter, items, **kwargs):
    headers, token, session_id = counter
    return make_sale(headers, token, session_id, items, **kwargs)


def test_pago_mixto_de_la_us3(make_sale, counter, product, db) -> None:
    sale = sell(
        make_sale,
        counter,
        [(product("50.00"), "1")],
        payments=[
            ("cash_usd", "20.00", None),
            ("mobile_payment", "730.00", "004512"),
            ("zelle", "10.00", "ZL-77"),
        ],
    )
    assert sale["paid_usd"] == "50.00"
    assert [payment["amount_usd"] for payment in sale["payments"]] == ["20.00", "20.00", "10.00"]
    assert [payment["currency"] for payment in sale["payments"]] == ["USD", "VES", "USD"]
    db.expire_all()
    rows = db.scalars(select(Payment).order_by(Payment.line_number)).all()
    assert all(row.exchange_rate == Decimal("36.50000000") for row in rows)
    assert all(str(row.cash_session_id) == counter[2] for row in rows)


def test_usdt_cubre_uno_a_uno(make_sale, counter, product) -> None:
    sale = sell(
        make_sale, counter, [(product("15.00"), "1")], payments=[("binance_usdt", "15.00", "TX1")]
    )
    assert sale["payments"][0]["currency"] == "USDT"
    assert sale["payments"][0]["amount_usd"] == "15.00"


@pytest.mark.parametrize("method", ["mobile_payment", "pos_card", "zelle", "binance_usdt"])
def test_referencia_obligatoria(make_sale, counter, product, method) -> None:
    amount = "365.00" if method in ("mobile_payment", "pos_card") else "10.00"
    body = sell(
        make_sale, counter, [(product("10.00"), "1")], payments=[(method, amount, None)], expect=422
    )
    assert "payload.payments.0.reference" in body["detail"]["fields"]


def test_efectivo_sin_referencia(make_sale, counter, product) -> None:
    sale = sell(
        make_sale, counter, [(product("10.00"), "1")], payments=[("cash_ves", "365.00", None)]
    )
    assert sale["payments"][0]["reference"] is None


def test_referencia_demasiado_larga(make_sale, counter, product) -> None:
    body = sell(
        make_sale,
        counter,
        [(product("10.00"), "1")],
        payments=[("zelle", "10.00", "x" * 61)],
        expect=422,
    )
    assert body["detail"]["code"] == "validation_error"


def test_vuelto_en_bs(make_sale, counter, product) -> None:
    sale = sell(
        make_sale,
        counter,
        [(product("7.70"), "1")],
        payments=[("cash_usd", "10.00", None)],
        change=[("cash_ves", "83.95", None)],
    )
    assert sale["change_usd"] == "2.30"
    assert sale["overpaid_usd"] == "0.00"
    change = [payment for payment in sale["payments"] if payment["kind"] == "change"]
    assert change == [
        {
            "kind": "change",
            "method": "cash_ves",
            "currency": "VES",
            "amount": "83.95",
            "amount_usd": "2.30",
            "reference": None,
        }
    ]


def test_vuelto_en_dos_metodos(make_sale, counter, product) -> None:
    sale = sell(
        make_sale,
        counter,
        [(product("7.70"), "1")],
        payments=[("cash_usd", "10.00", None)],
        change=[("cash_usd", "1.00", None), ("cash_ves", "47.45", None)],
    )
    assert sale["change_usd"] == "2.30"


def test_vuelto_mayor_que_el_excedente(make_sale, counter, product) -> None:
    body = sell(
        make_sale,
        counter,
        [(product("7.70"), "1")],
        payments=[("cash_usd", "10.00", None)],
        change=[("cash_usd", "3.00", None)],
        expect=422,
    )
    assert "payload.change" in body["detail"]["fields"]


def test_vuelto_menor_deja_sobrepago(make_sale, counter, product) -> None:
    """Aclaración del dueño: sin sencillo, la diferencia queda como sobrepago (FR-038)."""
    sale = sell(
        make_sale,
        counter,
        [(product("7.70"), "1")],
        payments=[("cash_usd", "10.00", None)],
        change=[("cash_usd", "2.00", None)],
    )
    assert sale["overpaid_usd"] == "0.30"


def test_pagar_el_saldo_exacto_en_bs(make_sale, counter, product, make_rate) -> None:
    today = business_date(clock.utcnow())
    sale = sell(
        make_sale,
        counter,
        [(product("12.34"), "1")],
        payments=[("mobile_payment", "450.41", "REF-9")],
        rate=("36.50000000", today),
    )
    assert sale["paid_usd"] == "12.34"


def test_limites_de_pagos_y_vueltos(make_sale, counter, product) -> None:
    item = product("100.00")
    body = sell(
        make_sale, counter, [(item, "1")], payments=[("cash_usd", "10.00", None)] * 11, expect=422
    )
    assert body["detail"]["code"] == "validation_error"
    body = sell(
        make_sale,
        counter,
        [(item, "1")],
        payments=[("cash_usd", "110.00", None)],
        change=[("cash_usd", "1.00", None)] * 6,
        expect=422,
    )
    assert body["detail"]["code"] == "validation_error"


def test_pago_en_cero(make_sale, counter, product) -> None:
    body = sell(
        make_sale,
        counter,
        [(product("10.00"), "1")],
        payments=[("cash_usd", "0.00", None), ("cash_usd", "10.00", None)],
        expect=422,
    )
    assert "payload.payments.0.amount" in body["detail"]["fields"]
