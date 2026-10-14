"""Proveedores (RF-13/FR-001 a FR-003, research R5).

Admin y Almacén los registran. Nunca se borran: se desactivan para que no se ofrezcan
en compras nuevas, y las compras pasadas siguen mostrando de quién fueron.
"""

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import AppUser, Supplier
from app.domain.rif import normalize_rif
from app.domain.search import normalize_text
from app.services.audit import record_audit

# Letras con acento que se igualan a su versión sin acento al buscar (sin extensiones de
# Postgres, como la búsqueda de productos).
_ACCENTS = ("áéíóúüñ", "aeiouun")


def _snapshot(supplier: Supplier) -> dict[str, Any]:
    return {
        "name": supplier.name,
        "rif": supplier.rif,
        "phone": supplier.phone,
        "notes": supplier.notes,
        "is_active": supplier.is_active,
    }


def _rif(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    try:
        return normalize_rif(value)
    except ValueError as exc:
        raise validation_error({"rif": str(exc)}) from exc


def _check_rif_free(db: Session, rif: str | None, own_id: uuid.UUID | None = None) -> None:
    if rif is None:
        return
    other = db.scalar(select(Supplier).where(Supplier.rif == rif))
    if other is not None and other.id != own_id:
        raise ApiError(
            409,
            "rif_in_use",
            f"Ese RIF ya pertenece a {other.name}",
            supplier_name=other.name,
        )


def _commit(db: Session, rif: str | None) -> None:
    try:
        db.commit()
    except IntegrityError:  # el mismo RIF guardado al mismo tiempo por otra persona
        db.rollback()
        _check_rif_free(db, rif)
        raise


def not_found() -> ApiError:
    return ApiError(404, "not_found", "El proveedor no existe")


def create_supplier(
    db: Session,
    *,
    actor: AppUser,
    name: str,
    rif: str | None,
    phone: str | None,
    notes: str | None,
) -> Supplier:
    normalized = _rif(rif)
    _check_rif_free(db, normalized)
    now = utcnow()
    supplier = Supplier(
        id=uuid.uuid7(),
        name=name,
        rif=normalized,
        phone=phone or None,
        notes=notes or None,
        is_active=True,
        created_by=actor.id,
        created_at=now,
        updated_at=now,
    )
    db.add(supplier)
    record_audit(
        db,
        action="supplier.created",
        user_id=actor.id,
        entity_type="supplier",
        entity_id=supplier.id,
        after=_snapshot(supplier),
    )
    _commit(db, normalized)
    return supplier


def get_supplier(db: Session, supplier_id: uuid.UUID) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise not_found()
    return supplier


def update_supplier(
    db: Session, *, actor: AppUser, supplier_id: uuid.UUID, changes: dict[str, Any]
) -> Supplier:
    supplier = db.get(Supplier, supplier_id, with_for_update=True)
    if supplier is None:
        raise not_found()
    before = _snapshot(supplier)
    if "rif" in changes:
        changes["rif"] = _rif(changes["rif"])
        _check_rif_free(db, changes["rif"], supplier.id)
    for field in ("phone", "notes"):
        if field in changes:
            changes[field] = changes[field] or None
    for field, value in changes.items():
        setattr(supplier, field, value)
    after = _snapshot(supplier)
    if after != before:
        supplier.updated_at = utcnow()
        record_audit(
            db,
            action="supplier.updated",
            user_id=actor.id,
            entity_type="supplier",
            entity_id=supplier.id,
            before=before,
            after=after,
        )
    _commit(db, supplier.rif)
    return supplier


def list_suppliers(
    db: Session, *, q: str | None, is_active: bool | None, page: int, page_size: int
) -> tuple[list[Supplier], int]:
    """Por nombre (sin acentos ni mayúsculas) o por RIF, ordenados por nombre."""
    query = select(Supplier)
    if is_active is not None:
        query = query.where(Supplier.is_active.is_(is_active))
    if q and q.strip():
        pattern = f"%{normalize_text(q)}%"
        conditions = [func.translate(func.lower(Supplier.name), *_ACCENTS).like(pattern)]
        compact = "".join(ch for ch in q.upper() if ch.isalnum())
        if compact:
            conditions.append(func.replace(Supplier.rif, "-", "").like(f"%{compact}%"))
        query = query.where(or_(*conditions))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(func.lower(Supplier.name), Supplier.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total
