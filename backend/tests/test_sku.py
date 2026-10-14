"""SKU automático por categoría (RF-02/FR-002 a FR-004, SC-006, research R1)."""

import threading
from decimal import Decimal

import pytest

from app.db.models import AppUser
from app.db.session import get_sessionmaker
from app.domain.roles import Role
from app.domain.sku import format_sku


def test_formato_del_sku() -> None:
    """RF-02/FR-002: prefijo y correlativo de al menos 4 dígitos."""
    assert format_sku("MAN", 1) == "MAN-0001"
    assert format_sku("MAN", 9999) == "MAN-9999"
    assert format_sku("MAN", 10000) == "MAN-10000"


def test_el_correlativo_empieza_en_uno() -> None:
    with pytest.raises(ValueError):
        format_sku("MAN", 0)


# --- Con base de datos -------------------------------------------------------------


def _create(client, headers, category_id, **extra):
    body = {"category_id": str(category_id), "name": "Producto", "description": "", **extra}
    return client.post("/api/v1/products", json=body, headers=headers)


@pytest.fixture
def warehouse(make_user, auth_headers):
    user = make_user(Role.WAREHOUSE, username="almacen")
    return user, auth_headers(user)


@pytest.mark.db
def test_primera_manguera_y_primera_conexion(client, warehouse, category_id) -> None:
    """RF-02/FR-002, US1 escenario 1: cada categoría tiene su propio correlativo."""
    _, headers = warehouse
    hose = _create(
        client, headers, category_id("MAN"), attributes={"hose_type": "R2", "diameter": '1/2"'}
    )
    fitting = _create(
        client, headers, category_id("CON"), attributes={"fitting_type": "Recta", "size": '1/2"'}
    )
    assert hose.status_code == 201, hose.text
    assert hose.json()["sku"] == "MAN-0001"
    assert fitting.json()["sku"] == "CON-0001"


@pytest.mark.db
def test_correlativo_sigue_aunque_haya_desactivados(
    client, warehouse, make_product, category_id
) -> None:
    """US1 escenario 2: el SKU no se repite ni se reutiliza."""
    _, headers = warehouse
    for index in range(7):
        make_product("CON", is_active=index % 2 == 0)
    response = _create(
        client, headers, category_id("CON"), attributes={"fitting_type": "Codo", "size": '3/8"'}
    )
    assert response.json()["sku"] == "CON-0008"


@pytest.mark.db
def test_veinte_altas_simultaneas_sin_repetir(make_user, category_id) -> None:
    """SC-006: 20 altas simultáneas en la misma categoría dan 20 SKU distintos y seguidos."""
    from app.services.products import create_product

    actor = make_user(Role.ADMIN, username="dueno")
    target = category_id("FRT")
    barrier = threading.Barrier(20)
    skus: list[str] = []
    errors: list[BaseException] = []

    def worker(index: int) -> None:
        try:
            with get_sessionmaker()() as session:
                barrier.wait()
                product, _ = create_product(
                    session,
                    actor=session.get(AppUser, actor.id),
                    category_id=target,
                    unit_id=None,
                    name=f"Tornillo {index}",
                    description="",
                    attributes={},
                    min_stock=Decimal("0"),
                )
                skus.append(product.sku)
        except BaseException as exc:  # noqa: BLE001 (se reporta abajo)
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert sorted(skus) == [f"FRT-{number:04d}" for number in range(1, 21)]


@pytest.mark.db
def test_cambio_de_categoria_da_sku_nuevo_sin_reutilizar(client, warehouse, category_id) -> None:
    """FR-004: sin movimientos, cambiar de categoría asigna un SKU de la nueva; el
    anterior no se reutiliza."""
    _, headers = warehouse
    created = _create(
        client, headers, category_id("MAN"), attributes={"hose_type": "R1", "diameter": '1/4"'}
    ).json()
    moved = client.patch(
        f"/api/v1/products/{created['id']}",
        json={
            "category_id": str(category_id("FER")),
            "attributes": {"ferrule_type": "Prensable", "size": '1/4"'},
        },
        headers=headers,
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["sku"] == "FER-0001"
    assert moved.json()["unit"]["code"] == "u"
    another = _create(
        client, headers, category_id("MAN"), attributes={"hose_type": "R1", "diameter": '1/4"'}
    )
    assert another.json()["sku"] == "MAN-0002"


@pytest.mark.db
def test_el_sku_no_se_envia(client, warehouse, category_id) -> None:
    """FR-003: el SKU no se edita a mano; enviarlo es un error de validación."""
    _, headers = warehouse
    response = _create(client, headers, category_id("FRT"), sku="FRT-9999")
    assert response.status_code == 422
    assert "sku" in response.json()["detail"]["fields"]
