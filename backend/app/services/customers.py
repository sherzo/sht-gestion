"""Clientes de las ventas (RF-28/FR-019; research R11).

El cliente es opcional. La venta trae uno conocido (`customer_id`) o los datos de uno con
id del equipo; si su documento ya pertenece a otro cliente, la venta se liga a ese en
lugar de crear un duplicado. La edición de clientes llega con el crédito (Fase 2).
"""

import contextlib
import uuid
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import validation_error
from app.db.models import AppUser, Customer
from app.domain.customer_document import normalize_document
from app.domain.search import normalize_text

MAX_RESULTS = 20


@dataclass(frozen=True)
class CustomerData:
    id: uuid.UUID
    name: str
    document_id: str | None
    phone: str | None


def search_customers(db: Session, q: str, limit: int = MAX_RESULTS) -> list[Customer]:
    """Por documento exacto (normalizado) o por nombre que contiene el texto, sin acentos."""
    text = q.strip()
    if not text:
        return []
    # Sin la extensión unaccent: se quitan los acentos del español con translate().
    plain_name = func.translate(func.lower(Customer.name), "áéíóúüñ", "aeiouun")
    conditions = [plain_name.contains(normalize_text(text), autoescape=True)]
    with contextlib.suppress(ValueError):
        conditions.append(Customer.document_id == normalize_document(text))
    return list(
        db.scalars(select(Customer).where(or_(*conditions)).order_by(Customer.name).limit(limit))
    )


def resolve_customer(
    db: Session,
    *,
    actor: AppUser,
    data: CustomerData | None,
    customer_id: uuid.UUID | None,
) -> Customer | None:
    """Cliente de la venta: el indicado, el que ya tiene ese documento o uno nuevo."""
    if customer_id is not None:
        customer = db.get(Customer, customer_id)
        if customer is None:
            raise validation_error({"payload.customer_id": "El cliente no existe"})
        return customer
    if data is None:
        return None
    existing = db.get(Customer, data.id)
    if existing is not None:
        return existing
    document = None
    if data.document_id and data.document_id.strip():
        try:
            document = normalize_document(data.document_id)
        except ValueError as exc:
            raise validation_error({"payload.customer.document_id": str(exc)}) from exc
        same_document = db.scalar(select(Customer).where(Customer.document_id == document))
        if same_document is not None:
            return same_document
    customer = Customer(
        id=data.id,
        name=data.name.strip(),
        document_id=document,
        phone=(data.phone or "").strip() or None,
        created_at=utcnow(),
        created_by=actor.id,
    )
    db.add(customer)
    db.flush()
    return customer
