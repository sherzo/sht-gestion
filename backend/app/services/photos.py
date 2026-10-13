"""Fotos de productos: validar, normalizar, ordenar y quitar (FR-008, research R9).

Toda foto se normaliza en el servidor a WebP de lado mayor 1.200 px, orientada según su
EXIF y sin metadatos, para que pese ~100–200 KB y quepa en el plan gratuito de Storage
(RNF-03) aunque el navegador no sepa codificar WebP.
"""

import io
import uuid
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.models import AppUser, Product, ProductPhoto
from app.services.audit import record_audit
from app.services.inventory import lock_product
from app.services.photo_storage import get_photo_storage

MAX_PHOTOS = 5
MAX_SIDE = 1200
WEBP_QUALITY = 80
ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP"}
# Fotos de teléfono de hasta ~50 megapíxeles; más que eso se rechaza antes de decodificar.
MAX_PIXELS = 50_000_000


def _unsupported() -> ApiError:
    return ApiError(415, "photo_unsupported", "La foto debe ser una imagen JPG, PNG o WebP válida")


def too_large(max_bytes: int) -> ApiError:
    megabytes = max_bytes // (1024 * 1024)
    return ApiError(
        413, "photo_too_large", f"La foto pesa más de {megabytes} MB", max_bytes=max_bytes
    )


def normalize_image(data: bytes) -> tuple[bytes, int, int]:
    """Devuelve el WebP normalizado y su tamaño, o lanza 415 si no es una imagen admitida."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in ACCEPTED_FORMATS:
                    raise _unsupported()
                if source.width * source.height > MAX_PIXELS:
                    raise _unsupported()
                image = ImageOps.exif_transpose(source)
                has_alpha = image.mode in ("RGBA", "LA") or (
                    image.mode == "P" and "transparency" in image.info
                )
                image = image.convert("RGBA" if has_alpha else "RGB")
                image.thumbnail((MAX_SIDE, MAX_SIDE))
                output = io.BytesIO()
                # Sin `exif` ni `icc_profile`: el WebP no lleva metadatos.
                image.save(output, format="WEBP", quality=WEBP_QUALITY)
                return output.getvalue(), image.width, image.height
    except ApiError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise _unsupported() from exc
    except Image.DecompressionBombWarning as exc:
        raise _unsupported() from exc


def _active(db: Session, product_id: uuid.UUID) -> list[ProductPhoto]:
    return list(
        db.scalars(
            select(ProductPhoto)
            .where(ProductPhoto.product_id == product_id, ProductPhoto.removed_at.is_(None))
            .order_by(ProductPhoto.sort_order, ProductPhoto.created_at)
        )
    )


def add_photo(db: Session, *, actor: AppUser, product_id: uuid.UUID, data: bytes) -> Product:
    max_bytes = get_settings().photo_max_upload_bytes
    if len(data) > max_bytes:
        raise too_large(max_bytes)
    product = lock_product(db, product_id)
    count = db.scalar(
        select(func.count())
        .select_from(ProductPhoto)
        .where(ProductPhoto.product_id == product.id, ProductPhoto.removed_at.is_(None))
    )
    if count >= MAX_PHOTOS:
        raise ApiError(
            409, "max_photos", f"Cada producto admite hasta {MAX_PHOTOS} fotos", max=MAX_PHOTOS
        )
    webp, width, height = normalize_image(data)
    next_order = db.scalar(
        select(func.coalesce(func.max(ProductPhoto.sort_order) + 1, 0)).where(
            ProductPhoto.product_id == product.id, ProductPhoto.removed_at.is_(None)
        )
    )
    photo = ProductPhoto(
        id=uuid.uuid7(),
        product_id=product.id,
        width=width,
        height=height,
        size_bytes=len(webp),
        sort_order=next_order,
        created_by=actor.id,
    )
    photo.storage_path = f"products/{product.id}/{photo.id}.webp"
    storage = get_photo_storage()
    storage.save(photo.storage_path, webp, "image/webp")
    try:
        db.add(photo)
        record_audit(
            db,
            action="product.photo_added",
            user_id=actor.id,
            entity_type="product",
            entity_id=product.id,
            details={"sku": product.sku, "photo_id": str(photo.id), "size_bytes": len(webp)},
        )
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(photo.storage_path)
        raise
    return product


def remove_photo(
    db: Session, *, actor: AppUser, product_id: uuid.UUID, photo_id: uuid.UUID
) -> None:
    product = lock_product(db, product_id)
    photo = db.get(ProductPhoto, photo_id)
    if photo is None or photo.product_id != product.id or photo.removed_at is not None:
        raise ApiError(404, "not_found", "La foto no existe")
    photo.removed_at = utcnow()
    photo.removed_by = actor.id
    record_audit(
        db,
        action="product.photo_removed",
        user_id=actor.id,
        entity_type="product",
        entity_id=product.id,
        details={"sku": product.sku, "photo_id": str(photo.id)},
    )
    db.commit()
    # Después de confirmar: si borrar el objeto falla, solo queda un archivo huérfano.
    get_photo_storage().delete(photo.storage_path)


def reorder_photos(
    db: Session, *, actor: AppUser, product_id: uuid.UUID, photo_ids: list[uuid.UUID]
) -> Product:
    product = lock_product(db, product_id)
    photos = {photo.id: photo for photo in _active(db, product.id)}
    if len(photo_ids) != len(set(photo_ids)) or set(photo_ids) != set(photos):
        raise ApiError(
            422,
            "validation_error",
            "Hay datos inválidos",
            fields={"photo_ids": "Incluye todas las fotos del producto, una vez cada una"},
        )
    for order, photo_id in enumerate(photo_ids):
        photos[photo_id].sort_order = order
    record_audit(
        db,
        action="product.photos_reordered",
        user_id=actor.id,
        entity_type="product",
        entity_id=product.id,
        details={"sku": product.sku, "photo_ids": [str(photo_id) for photo_id in photo_ids]},
    )
    db.commit()
    return product
