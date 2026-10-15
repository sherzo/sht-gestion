"""Cola de salida: idempotencia por el id de la operación y rechazos guardados (ADR-0003/
FR-017, FR-002; SC-004). Usa manejadores de prueba registrados en `HANDLERS`."""

import threading
import time
import uuid
from collections.abc import Callable
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.errors import validation_error
from app.domain.roles import Role
from app.main import app
from app.services import sync as sync_service
from tests.conftest import device_headers, operation

pytestmark = pytest.mark.db

URL = "/api/v1/sync/operations"


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Registra manejadores de prueba que anotan cada ejecución."""
    executed: list[str] = []
    lock = threading.Lock()

    def ok(db, device, user, op) -> dict:
        time.sleep(0.05)  # ensancha la ventana para que los envíos simultáneos se crucen
        with lock:
            executed.append(str(op.id))
            return {"ok": True, "count": len(executed)}

    def rejected(db, device, user, op) -> dict:
        with lock:
            executed.append(str(op.id))
        raise validation_error({"payload": "No sirve"})

    def transient(db, device, user, op) -> dict:
        with lock:
            executed.append(str(op.id))
        raise RuntimeError("se cayó la base")

    monkeypatch.setitem(sync_service.HANDLERS, "test.ok", ok)
    monkeypatch.setitem(sync_service.HANDLERS, "test.rejected", rejected)
    monkeypatch.setitem(sync_service.HANDLERS, "test.transient", transient)
    return executed


@pytest.fixture
def seller_headers(make_user, auth_headers, make_device) -> Callable[..., dict[str, str]]:
    seller = make_user(Role.SELLER)
    headers = auth_headers(seller)
    _, token = make_device()
    return device_headers(headers, token)


def test_reenvio_devuelve_lo_mismo_sin_volver_a_ejecutar(
    client: TestClient, calls: list[str], seller_headers: dict[str, str]
) -> None:
    body = operation("test.ok", {"a": 1})
    first = client.post(URL, json=body, headers=seller_headers)
    second = client.post(URL, json=body, headers=seller_headers)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {"ok": True, "count": 1}
    assert calls == [body["id"]]


def test_diez_envios_simultaneos_ejecutan_una_vez(
    calls: list[str], seller_headers: dict[str, str]
) -> None:
    """SC-004: 10 envíos simultáneos de la misma operación dejan una sola ejecución."""
    body = operation("test.ok", {"a": 1})
    results: list[tuple[int, dict]] = []
    lock = threading.Lock()

    def send() -> None:
        with TestClient(app) as own_client:
            response = own_client.post(URL, json=body, headers=seller_headers)
        with lock:
            results.append((response.status_code, response.json()))

    threads = [threading.Thread(target=send) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(calls) == 1
    assert results == [(200, {"ok": True, "count": 1})] * 10


def test_rechazo_permanente_se_guarda_y_se_repite(
    client: TestClient, calls: list[str], seller_headers: dict[str, str]
) -> None:
    body = operation("test.rejected", {})
    first = client.post(URL, json=body, headers=seller_headers)
    second = client.post(URL, json=body, headers=seller_headers)
    assert first.status_code == second.status_code == 422
    assert first.json() == second.json()
    assert first.json()["detail"]["code"] == "validation_error"
    assert len(calls) == 1


def test_error_transitorio_no_se_guarda_y_se_reintenta(
    calls: list[str], seller_headers: dict[str, str]
) -> None:
    body = operation("test.transient", {})
    with TestClient(app, raise_server_exceptions=False) as own_client:
        assert own_client.post(URL, json=body, headers=seller_headers).status_code == 500
        assert own_client.post(URL, json=body, headers=seller_headers).status_code == 500
    assert len(calls) == 2


def test_tipo_desconocido(client: TestClient, calls: list[str], seller_headers) -> None:
    response = client.post(URL, json=operation("otra.cosa", {}), headers=seller_headers)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "operation_type_unknown"


def test_sin_token_de_equipo(client: TestClient, make_user, auth_headers, calls) -> None:
    headers = auth_headers(make_user(Role.SELLER))
    response = client.post(URL, json=operation("test.ok", {}), headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "device_required"
    response = client.post(
        URL, json=operation("test.ok", {}), headers={**headers, "X-Device-Token": "no-existe"}
    )
    assert response.json()["detail"]["code"] == "device_required"
    assert calls == []


def test_equipo_revocado_acepta_lo_anterior_y_rechaza_lo_posterior(
    client: TestClient, calls: list[str], make_user, auth_headers, make_device, db
) -> None:
    """FR-002: las operaciones creadas antes de la revocación se aceptan."""
    from app.services.devices import revoke_device

    seller = make_user(Role.SELLER)
    device, token = make_device()
    headers = device_headers(auth_headers(seller), token)
    before = operation("test.ok", {})
    admin = make_user(Role.ADMIN)
    revoke_device(db, actor=admin, device_id=device.id)
    db.commit()
    after = operation("test.ok", {})
    after["created_at"] = (device.revoked_at + timedelta(seconds=1)).isoformat()

    accepted = client.post(URL, json=before, headers=headers)
    assert accepted.status_code == 200
    rejected = client.post(URL, json=after, headers=headers)
    assert rejected.status_code == 403
    assert rejected.json()["detail"]["code"] == "device_revoked"
    # El rechazo queda guardado y se repite al reenviar.
    assert client.post(URL, json=after, headers=headers).json() == rejected.json()
    assert calls == [before["id"]]


def test_almacen_no_envia_operaciones(
    client: TestClient, make_user, auth_headers, make_device
) -> None:
    _, token = make_device()
    headers = device_headers(auth_headers(make_user(Role.WAREHOUSE)), token)
    response = client.post(URL, json=operation("test.ok", {}), headers=headers)
    assert response.status_code == 403


def test_id_invalido_o_version_desconocida(client: TestClient, seller_headers) -> None:
    body = operation("test.ok", {})
    body["schema_version"] = 2
    assert client.post(URL, json=body, headers=seller_headers).status_code == 422
    body = operation("test.ok", {}, op_id="no-es-un-uuid")
    assert client.post(URL, json=body, headers=seller_headers).status_code == 422
    assert uuid.UUID(operation("test.ok", {})["id"]).version == 7


def test_error_de_datos_se_guarda_como_rechazo(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, seller_headers: dict[str, str]
) -> None:
    """Hallazgo del code review: un desborde numérico no traba la cola con un 500 eterno;
    se guarda como rechazo 422 y se repite igual."""
    from sqlalchemy import text as sql

    def overflow(db, device, user, op) -> dict:
        db.execute(sql("SELECT CAST(1e20 AS numeric(14, 2))"))
        return {}

    monkeypatch.setitem(sync_service.HANDLERS, "test.overflow", overflow)
    body = operation("test.overflow", {})
    first = client.post(URL, json=body, headers=seller_headers)
    assert first.status_code == 422
    assert first.json()["detail"]["code"] == "validation_error"
    assert client.post(URL, json=body, headers=seller_headers).json() == first.json()
