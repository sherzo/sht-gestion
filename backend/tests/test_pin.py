"""PIN del admin para autorizaciones (RF-44, RN-07/FR-026 a FR-029; SC-006)."""

from datetime import timedelta

import pytest

from app.domain.roles import Role
from tests.conftest import DEFAULT_PASSWORD
from tests.helpers import audit_entries

pytestmark = pytest.mark.db


def _set_pin(client, headers, pin, password=DEFAULT_PASSWORD):
    return client.put(
        "/api/v1/auth/pin", json={"current_password": password, "pin": pin}, headers=headers
    )


def _verify(client, headers, admin_username, pin):
    return client.post(
        "/api/v1/auth/pin/verify",
        json={"admin_username": admin_username, "pin": pin},
        headers=headers,
    )


def test_definir_y_cambiar_el_pin(client, make_user, auth_headers, db) -> None:
    admin = make_user(Role.ADMIN, username="dueno")
    headers = auth_headers(admin)

    assert _set_pin(client, headers, "1234").status_code == 204
    assert _set_pin(client, headers, "567890").status_code == 204

    entries = audit_entries(db, "auth.pin_set")
    assert [entry.details for entry in entries] == [{"first_time": True}, {"first_time": False}]
    assert "1234" not in str([entry.details for entry in entries])

    seller = make_user(Role.SELLER)
    seller_headers = auth_headers(seller)
    assert _verify(client, seller_headers, "dueno", "1234").status_code == 403
    assert _verify(client, seller_headers, "dueno", "567890").status_code == 200


def test_definir_el_pin_exige_la_contrasena(client, make_user, auth_headers) -> None:
    headers = auth_headers(make_user(Role.ADMIN))

    response = _set_pin(client, headers, "1234", password="incorrecta")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_current_password"


@pytest.mark.parametrize("pin", ["123", "1234567", "12a4", ""])
def test_pin_de_4_a_6_digitos(client, make_user, auth_headers, pin) -> None:
    headers = auth_headers(make_user(Role.ADMIN))

    response = _set_pin(client, headers, pin)

    assert response.status_code == 422
    assert "pin" in response.json()["detail"]["fields"]


def test_solo_los_admin_tienen_pin(client, make_user, auth_headers) -> None:
    headers = auth_headers(make_user(Role.SELLER))

    response = _set_pin(client, headers, "1234")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "forbidden"


def test_verificacion_correcta_registra_quien_autorizo(client, make_user, auth_headers, db) -> None:
    admin = make_user(Role.ADMIN, username="dueno", full_name="Dueño", pin="2468")
    seller = make_user(Role.SELLER, username="maria")

    response = _verify(client, auth_headers(seller), "DUENO", "2468")

    assert response.status_code == 200
    assert response.json() == {"authorized_by": {"id": str(admin.id), "full_name": "Dueño"}}
    [entry] = audit_entries(db, "auth.pin_verified")
    assert entry.user_id == seller.id
    assert entry.entity_id == admin.id
    assert entry.details == {"authorized_by": str(admin.id), "admin_username": "dueno"}


def test_pin_invalido_no_revela_la_causa(client, make_user, auth_headers, db) -> None:
    make_user(Role.ADMIN, username="dueno", pin="2468")
    make_user(Role.ADMIN, username="inactivo", pin="2468", is_active=False)
    make_user(Role.ADMIN, username="sinpin")
    make_user(Role.SELLER, username="vendedor")
    headers = auth_headers(make_user(Role.SELLER, username="maria"))

    responses = [
        _verify(client, headers, "dueno", "0000"),
        _verify(client, headers, "nadie", "2468"),
        _verify(client, headers, "inactivo", "2468"),
        _verify(client, headers, "sinpin", "2468"),
        _verify(client, headers, "vendedor", "2468"),
    ]

    assert {r.status_code for r in responses} == {403}
    assert {r.json()["detail"]["code"] for r in responses} == {"pin_invalid"}
    assert len({r.json()["detail"]["message"] for r in responses}) == 1
    assert len(audit_entries(db, "auth.pin_failed")) == 5


def test_cinco_fallos_bloquean_el_pin_15_minutos(
    client, make_user, auth_headers, advance_clock, db
) -> None:
    make_user(Role.ADMIN, username="dueno", pin="2468")
    seller = make_user(Role.SELLER)
    headers = auth_headers(seller)
    for _ in range(5):
        assert _verify(client, headers, "dueno", "0000").status_code == 403

    locked = _verify(client, headers, "dueno", "2468")
    assert locked.status_code == 423
    assert locked.json()["detail"]["code"] == "pin_locked"
    assert "locked_until" in locked.json()["detail"]
    assert len(audit_entries(db, "auth.pin_locked")) == 1

    advance_clock(timedelta(minutes=15, seconds=1))
    # El token de acceso también venció: se vuelve a entrar.
    assert _verify(client, auth_headers(seller), "dueno", "2468").status_code == 200


def test_un_acierto_reinicia_el_contador_del_pin(client, make_user, auth_headers) -> None:
    make_user(Role.ADMIN, username="dueno", pin="2468")
    headers = auth_headers(make_user(Role.SELLER))
    for _ in range(4):
        _verify(client, headers, "dueno", "0000")
    assert _verify(client, headers, "dueno", "2468").status_code == 200
    for _ in range(4):
        _verify(client, headers, "dueno", "0000")

    assert _verify(client, headers, "dueno", "2468").status_code == 200


def test_al_vencer_el_bloqueo_del_pin_la_cuenta_vuelve_a_cero(
    client, make_user, auth_headers, advance_clock
) -> None:
    """RN-07/FR-028: tras el bloqueo, un solo error no vuelve a bloquear el PIN."""
    make_user(Role.ADMIN, username="dueno", pin="2468")
    seller = make_user(Role.SELLER)
    headers = auth_headers(seller)
    for _ in range(5):
        _verify(client, headers, "dueno", "0000")
    advance_clock(timedelta(minutes=15, seconds=1))
    headers = auth_headers(seller)

    assert _verify(client, headers, "dueno", "0000").status_code == 403
    assert _verify(client, headers, "dueno", "2468").status_code == 200


def test_definir_el_pin_cuenta_los_fallos_de_contrasena(client, make_user, auth_headers) -> None:
    """RF-44: la contraseña actual no se puede adivinar desde una sesión abierta."""
    headers = auth_headers(make_user(Role.ADMIN))
    for _ in range(4):
        assert _set_pin(client, headers, "1234", password="incorrecta").status_code == 400

    fifth = _set_pin(client, headers, "1234", password="incorrecta")
    assert fifth.status_code == 401
    assert fifth.json()["detail"]["code"] == "session_ended"
