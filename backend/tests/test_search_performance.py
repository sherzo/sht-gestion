"""Búsqueda con 1.000 productos en menos de 200 ms en el servidor (RNF-04, SC-001, R16).

El segundo de SC-001 se mide de punta a punta en el teléfono (quickstart, escenario 10);
aquí se deja margen amplio para la red.
"""

import time

import pytest

from app.cli import seed_demo_products
from app.db.session import get_sessionmaker
from app.domain.roles import Role

pytestmark = pytest.mark.db

QUERIES = [
    {"q": "r2 1/2"},
    {"q": "conexion"},
    {"q": "MAN-0500"},
    {"q": "manguera 3/4"},
    {"q": "ferrule prensable"},
    {"q": "jic"},
    {"attr.hose_type": "R2"},
    {"low_stock": "true"},
    {"q": "tornillo", "is_active": "true"},
    {"q": "inexistente xyz"},
]


def test_busqueda_con_mil_productos(client, make_user, auth_headers) -> None:
    with get_sessionmaker()() as db:
        assert seed_demo_products(db, 1000) == 1000
    headers = auth_headers(make_user(Role.SELLER, username="vendedor"))
    client.get("/api/v1/products", params={"q": "calentar"}, headers=headers)

    slowest = 0.0
    for params in QUERIES:
        start = time.perf_counter()
        response = client.get("/api/v1/products", params=params, headers=headers)
        elapsed = time.perf_counter() - start
        assert response.status_code == 200, response.text
        slowest = max(slowest, elapsed)
    assert slowest < 0.2, f"La búsqueda más lenta tardó {slowest * 1000:.0f} ms"
