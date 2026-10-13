"""Fotos de productos: normalización, límites, quitar y ordenar (FR-008, research R9)."""

import io

import pytest
from PIL import Image

from app.domain.roles import Role
from tests.helpers import audit_entries

pytestmark = pytest.mark.db


def _image(size=(64, 48), fmt="JPEG", *, orientation: int | None = None, mode="RGB") -> bytes:
    buffer = io.BytesIO()
    # En RGBA, el fondo es semitransparente.
    color = (10, 120, 200, 128) if mode == "RGBA" else (10, 120, 200)
    image = Image.new(mode, size, color)
    kwargs = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = orientation
        kwargs["exif"] = exif.tobytes()
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


@pytest.fixture
def warehouse_headers(make_user, auth_headers):
    return auth_headers(make_user(Role.WAREHOUSE, username="almacen"))


def _upload(client, headers, product_id, data: bytes, name="foto.jpg", content_type="image/jpeg"):
    return client.post(
        f"/api/v1/products/{product_id}/photos",
        files={"file": (name, data, content_type)},
        headers=headers,
    )


def test_foto_normalizada_a_webp(client, warehouse_headers, make_product, photo_dir) -> None:
    """R9: WebP de lado mayor 1.200 px, orientado según EXIF y sin metadatos."""
    product = make_product("FRT")
    # Orientación 6: la cámara la tomó girada; la imagen real es vertical.
    response = _upload(client, warehouse_headers, product.id, _image((3000, 2000), orientation=6))
    assert response.status_code == 201, response.text
    [photo] = response.json()["photos"]
    assert (photo["width"], photo["height"]) == (800, 1200)
    stored = next(photo_dir.rglob("*.webp"))
    with Image.open(stored) as image:
        assert image.format == "WEBP"
        assert image.size == (800, 1200)
        assert not image.getexif()
    assert photo["url"].endswith(f"{photo['id']}.webp")


def test_png_con_transparencia(client, warehouse_headers, make_product, photo_dir) -> None:
    """R9: la transparencia de un PNG se conserva en el WebP."""
    product = make_product("FRT")
    response = _upload(
        client, warehouse_headers, product.id, _image(fmt="PNG", mode="RGBA"), "a.png", "image/png"
    )
    assert response.status_code == 201
    with Image.open(next(photo_dir.rglob("*.webp"))) as image:
        assert image.mode == "RGBA"


def test_maximo_cinco_fotos_y_la_primera_es_la_principal(
    client, warehouse_headers, make_product, photo_dir
) -> None:
    """FR-008: hasta 5 fotos activas; la primera es la principal."""
    product = make_product("FRT")
    ids = []
    for _ in range(5):
        ids.append(_upload(client, warehouse_headers, product.id, _image()).json()["photos"][-1])
    assert [photo["sort_order"] for photo in ids] == [0, 1, 2, 3, 4]
    sixth = _upload(client, warehouse_headers, product.id, _image())
    assert sixth.status_code == 409
    assert sixth.json()["detail"]["code"] == "max_photos"


def test_foto_demasiado_pesada(client, warehouse_headers, make_product, photo_dir) -> None:
    product = make_product("FRT")
    data = _image() + b"0" * (5 * 1024 * 1024)
    response = _upload(client, warehouse_headers, product.id, data)
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "photo_too_large"


@pytest.mark.parametrize(
    ("data", "name", "content_type"),
    [
        (b"%PDF-1.4 documento", "doc.pdf", "application/pdf"),
        (b"no soy una imagen", "falsa.jpg", "image/jpeg"),
        (_image(fmt="GIF"), "animada.gif", "image/gif"),
    ],
)
def test_formato_no_admitido(
    client, warehouse_headers, make_product, photo_dir, data, name, content_type
) -> None:
    product = make_product("FRT")
    response = _upload(client, warehouse_headers, product.id, data, name, content_type)
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "photo_unsupported"


def test_quitar_y_reordenar(client, warehouse_headers, make_product, photo_dir, db) -> None:
    """FR-008: quitar marca la foto y borra el archivo; reordenar exige todas las fotos."""
    product = make_product("FRT")
    for _ in range(3):
        _upload(client, warehouse_headers, product.id, _image())
    photos = client.get(f"/api/v1/products/{product.id}", headers=warehouse_headers).json()[
        "photos"
    ]
    first, second, third = (photo["id"] for photo in photos)

    removed = client.delete(
        f"/api/v1/products/{product.id}/photos/{first}", headers=warehouse_headers
    )
    assert removed.status_code == 204
    assert len(list(photo_dir.rglob("*.webp"))) == 2

    incomplete = client.put(
        f"/api/v1/products/{product.id}/photos/order",
        json={"photo_ids": [third]},
        headers=warehouse_headers,
    )
    assert incomplete.status_code == 422

    reordered = client.put(
        f"/api/v1/products/{product.id}/photos/order",
        json={"photo_ids": [third, second]},
        headers=warehouse_headers,
    )
    assert reordered.status_code == 200
    assert [photo["id"] for photo in reordered.json()["photos"]] == [third, second]

    assert len(audit_entries(db, "product.photo_added")) == 3
    assert len(audit_entries(db, "product.photo_removed")) == 1


def test_vendedor_no_sube_fotos(client, make_user, auth_headers, make_product, photo_dir) -> None:
    product = make_product("FRT")
    headers = auth_headers(make_user(Role.SELLER, username="vendedor"))
    assert _upload(client, headers, product.id, _image()).status_code == 403
