"""Compras: borrador, confirmación, anulación y consulta (RF-14 a RF-16, RN-05, RN-09,
RN-14, RN-20; FR-004 a FR-021, FR-029 a FR-031; research R2 a R4 y R10).

- El borrador se guarda entero y el servidor recalcula todo con `domain/costing`: los
  totales que envíe el cliente no existen (R4).
- Confirmar es una sola transacción: bloquea la compra y los productos en orden de id
  (sin bloqueos cruzados), genera las entradas del kardex con el costo antes y después,
  actualiza el costo promedio con el costo final, bloquea el costo inicial y toma el
  número del correlativo al final, sin huecos (R3).
- Anular genera los reversos y deshace el costo; si el resultado no es válido conserva
  el costo y crea una alerta (R10). La base rechaza cualquier otro cambio (R2).
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import (
    AppUser,
    Product,
    Purchase,
    PurchaseCharge,
    PurchaseItem,
    PurchaseVoid,
    SequenceCounter,
    StockMovement,
    Supplier,
    Unit,
)
from app.domain.business_time import business_date
from app.domain.costing import (
    ChargeInput,
    allocate_by_value,
    charge_amount_usd,
    landed_unit_cost,
    undo_purchase,
    weighted_average,
)
from app.domain.money import (
    round_usd,
    validate_percent,
    validate_purchase_cost,
    validate_usd_amount,
    validate_ves,
    ves_to_usd_cost,
)
from app.domain.units import format_quantity, validate_quantity
from app.services.alerts import create_alert
from app.services.audit import record_audit
from app.services.exchange_rates import applicable_rate, exchange_rate_missing
from app.services.inventory import lock_product, post_movement

MAX_ITEMS = 500
MAX_CHARGES = 20
ZERO = Decimal("0")


# --- Entradas -------------------------------------------------------------------------


@dataclass(frozen=True)
class ItemData:
    product_id: uuid.UUID
    quantity: Decimal
    unit_cost: Decimal  # en la moneda de la compra


@dataclass(frozen=True)
class ChargeData:
    description: str
    charge_type: str
    percent: Decimal | None = None
    amount: Decimal | None = None
    currency: str | None = None
    charge_template_id: uuid.UUID | None = None


@dataclass(frozen=True)
class PurchaseData:
    supplier_id: uuid.UUID
    purchase_date: date
    currency: str
    items: list[ItemData]
    charges: list[ChargeData] = field(default_factory=list)
    supplier_invoice_number: str | None = None
    notes: str | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class CostChange:
    product_id: uuid.UUID
    sku: str
    cost_before_usd: Decimal | None
    cost_after_usd: Decimal | None


@dataclass(frozen=True)
class VoidPreviewLine:
    product_id: uuid.UUID
    sku: str
    unit_decimals: int
    stock_before: Decimal
    stock_after: Decimal
    cost_before_usd: Decimal | None
    cost_after_usd: Decimal | None
    keeps_cost: bool


# --- Errores --------------------------------------------------------------------------


def not_found() -> ApiError:
    return ApiError(404, "not_found", "La compra no existe")


def invalid_state(message: str) -> ApiError:
    return ApiError(409, "invalid_state", message)


def inactive_supplier(supplier: Supplier) -> ApiError:
    return ApiError(
        409,
        "inactive_supplier",
        f"El proveedor {supplier.name} está inactivo: reactívalo o elige otro",
    )


# --- Validación y cálculo del borrador -------------------------------------------------


def _supplier(db: Session, supplier_id: uuid.UUID) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise validation_error({"supplier_id": "El proveedor no existe"})
    if not supplier.is_active:
        raise inactive_supplier(supplier)
    return supplier


def _validated_items(
    db: Session, data: PurchaseData
) -> tuple[list[ItemData], dict[uuid.UUID, Product], dict[uuid.UUID, Unit]]:
    if not data.items:
        raise validation_error({"items": "La compra necesita al menos un producto"})
    if len(data.items) > MAX_ITEMS:
        raise validation_error({"items": f"Una compra admite como máximo {MAX_ITEMS} líneas"})
    ids = [item.product_id for item in data.items]
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(set(ids))))}
    units = _units(db)
    errors: dict[str, str] = {}
    seen: set[uuid.UUID] = set()
    clean: list[ItemData] = []
    for index, item in enumerate(data.items):
        product = products.get(item.product_id)
        key = f"items.{index}"
        if product is None:
            errors[f"{key}.product_id"] = "El producto no existe"
            continue
        if item.product_id in seen:
            errors[f"{key}.product_id"] = (
                f"{product.sku} ya está en la compra: corrige la cantidad de esa línea"
            )
            continue
        seen.add(item.product_id)
        if not product.is_active:
            errors[f"{key}.product_id"] = f"{product.sku} está inactivo"
        try:
            quantity = validate_quantity(
                item.quantity,
                units[product.unit_id].decimals,
                allow_zero=False,
                allow_negative=False,
            )
        except ValueError as exc:
            errors[f"{key}.quantity"] = str(exc)
            quantity = item.quantity
        try:
            cost = (
                validate_ves(item.unit_cost)
                if data.currency == "VES"
                else validate_purchase_cost(item.unit_cost)
            )
        except ValueError as exc:
            errors[f"{key}.unit_cost"] = str(exc)
            cost = item.unit_cost
        clean.append(ItemData(item.product_id, quantity, cost))
    if errors:
        raise validation_error(errors)
    return clean, products, units


def _validated_charges(charges: list[ChargeData]) -> list[ChargeData]:
    if len(charges) > MAX_CHARGES:
        raise validation_error({"charges": f"Una compra admite como máximo {MAX_CHARGES} gastos"})
    errors: dict[str, str] = {}
    clean: list[ChargeData] = []
    for index, charge in enumerate(charges):
        key = f"charges.{index}"
        try:
            if charge.charge_type == "percent":
                if charge.amount is not None or charge.currency is not None:
                    raise ValueError("Un gasto por porcentaje no lleva monto ni moneda")
                if charge.percent is None:
                    raise ValueError("Indica el porcentaje")
                clean.append(
                    ChargeData(
                        charge.description,
                        "percent",
                        percent=validate_percent(charge.percent),
                        charge_template_id=charge.charge_template_id,
                    )
                )
            else:
                if charge.percent is not None:
                    raise ValueError("Un gasto por monto no lleva porcentaje")
                if charge.amount is None or charge.currency is None:
                    raise ValueError("Indica el monto y su moneda")
                amount = (
                    validate_ves(charge.amount)
                    if charge.currency == "VES"
                    else validate_usd_amount(charge.amount)
                )
                clean.append(
                    ChargeData(
                        charge.description,
                        "fixed",
                        amount=amount,
                        currency=charge.currency,
                        charge_template_id=charge.charge_template_id,
                    )
                )
        except ValueError as exc:
            errors[key] = str(exc)
    if errors:
        raise validation_error(errors)
    return clean


def _check_date(on_date: date) -> None:
    if on_date > business_date(utcnow()):
        raise validation_error({"purchase_date": "La fecha de la compra no puede ser futura"})


def _recalculate(
    db: Session,
    purchase: Purchase,
    items: list[PurchaseItem],
    charges: list[PurchaseCharge],
) -> None:
    """Recalcula tasa, totales, gastos, reparto y costo final desde las entradas (R1, R4).

    La compra en Bs, o con gastos en Bs, necesita tasa; las demás la guardan si existe,
    solo como referencia (FR-012, FR-013).
    """
    rate = applicable_rate(db, purchase.purchase_date)
    needs_rate = purchase.currency == "VES" or any(c.currency == "VES" for c in charges)
    if needs_rate and rate is None:
        raise exchange_rate_missing(purchase.purchase_date)
    purchase.exchange_rate = rate.rate if rate else None
    purchase.exchange_rate_date = rate.business_date if rate else None

    ordered = sorted(items, key=lambda item: item.line_number)
    for index, item in enumerate(ordered):
        if purchase.currency == "VES":
            item.unit_cost_usd = ves_to_usd_cost(item.unit_cost_ves, rate.rate)
            if item.unit_cost_usd <= 0:
                raise validation_error(
                    {
                        f"items.{index}.unit_cost": "El costo en Bs es tan pequeño que en USD "
                        "queda en cero con esta tasa"
                    }
                )
            item.line_total_ves = round_usd(item.quantity * item.unit_cost_ves)
        else:
            item.unit_cost_ves = None
            item.line_total_ves = None
        item.line_total_usd = round_usd(item.quantity * item.unit_cost_usd)
    merchandise = sum((item.line_total_usd for item in ordered), ZERO)
    purchase.merchandise_total_usd = merchandise
    purchase.merchandise_total_ves = (
        sum((item.line_total_ves for item in ordered), ZERO) if purchase.currency == "VES" else None
    )

    for charge in charges:
        charge.amount_usd = charge_amount_usd(
            ChargeInput(charge.charge_type, charge.percent, charge.amount, charge.currency),
            merchandise,
            rate.rate if rate else None,
        )
    charges_total = sum((charge.amount_usd for charge in charges), ZERO)
    shares = allocate_by_value([item.line_total_usd for item in ordered], charges_total)
    for item, share in zip(ordered, shares, strict=True):
        item.allocated_charges_usd = share
        item.landed_unit_cost_usd = landed_unit_cost(item.unit_cost_usd, share, item.quantity)
    purchase.charges_total_usd = charges_total
    purchase.total_usd = merchandise + charges_total


def _replace_lines(
    db: Session,
    purchase: Purchase,
    items: list[ItemData],
    charges: list[ChargeData],
    *,
    is_new: bool = False,
) -> tuple[list[PurchaseItem], list[PurchaseCharge]]:
    if not is_new:
        db.execute(delete(PurchaseCharge).where(PurchaseCharge.purchase_id == purchase.id))
        db.execute(delete(PurchaseItem).where(PurchaseItem.purchase_id == purchase.id))
    new_items = [
        PurchaseItem(
            id=uuid.uuid7(),
            purchase_id=purchase.id,
            product_id=item.product_id,
            line_number=index + 1,
            quantity=item.quantity,
            unit_cost_ves=item.unit_cost if purchase.currency == "VES" else None,
            unit_cost_usd=item.unit_cost if purchase.currency == "USD" else ZERO,
            line_total_usd=ZERO,
            allocated_charges_usd=ZERO,
            landed_unit_cost_usd=ZERO,
        )
        for index, item in enumerate(items)
    ]
    new_charges = [
        PurchaseCharge(
            id=uuid.uuid7(),
            purchase_id=purchase.id,
            line_number=index + 1,
            description=charge.description,
            charge_type=charge.charge_type,
            percent=charge.percent,
            amount=charge.amount,
            currency=charge.currency,
            amount_usd=ZERO,
            allocation_method="value",
            charge_template_id=charge.charge_template_id,
        )
        for index, charge in enumerate(charges)
    ]
    _recalculate(db, purchase, new_items, new_charges)
    if is_new:
        db.add(purchase)
    db.add_all(new_items)
    db.add_all(new_charges)
    return new_items, new_charges


def _warnings(db: Session, purchase: Purchase, *, stale: bool) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if stale:
        warnings.append(
            {
                "code": "stale_data",
                "message": "Otra persona cambió esta compra desde que la abriste; se guardó "
                "tu versión: revísala",
            }
        )
    if purchase.supplier_invoice_number:
        other = db.execute(
            select(Purchase.number)
            .where(
                Purchase.id != purchase.id,
                Purchase.supplier_id == purchase.supplier_id,
                func.lower(Purchase.supplier_invoice_number)
                == purchase.supplier_invoice_number.lower(),
                Purchase.status != "voided",
            )
            .limit(1)
        ).first()
        if other is not None:
            warnings.append(
                {
                    "code": "duplicate_invoice",
                    "message": "Ya hay otra compra de este proveedor con el mismo número de "
                    "factura",
                    "purchase_number": other.number,
                }
            )
    if purchase.charges_total_usd > purchase.merchandise_total_usd:
        warnings.append(
            {
                "code": "charges_over_100_percent",
                "message": "Los gastos superan el total de la factura: revisa que estén bien "
                "escritos",
            }
        )
    return warnings


@dataclass
class SavedPurchase:
    purchase: Purchase
    warnings: list[dict[str, Any]]


def create_purchase(db: Session, *, actor: AppUser, data: PurchaseData) -> SavedPurchase:
    """Crea una compra en borrador: no toca stock ni costo (FR-004, FR-005)."""
    _check_date(data.purchase_date)
    _supplier(db, data.supplier_id)
    items, _, _ = _validated_items(db, data)
    charges = _validated_charges(data.charges)
    now = utcnow()
    purchase = Purchase(
        id=uuid.uuid7(),
        supplier_id=data.supplier_id,
        purchase_date=data.purchase_date,
        supplier_invoice_number=data.supplier_invoice_number or None,
        currency=data.currency,
        notes=data.notes or None,
        status="draft",
        created_by=actor.id,
        created_at=now,
        updated_at=now,
    )
    _replace_lines(db, purchase, items, charges, is_new=True)
    db.flush()
    warnings = _warnings(db, purchase, stale=False)
    db.commit()
    return SavedPurchase(purchase, warnings)


def _locked_draft(db: Session, purchase_id: uuid.UUID, action: str) -> Purchase:
    purchase = db.get(Purchase, purchase_id, with_for_update=True, populate_existing=True)
    if purchase is None:
        raise not_found()
    if purchase.status != "draft":
        raise invalid_state(f"Solo se puede {action} una compra en borrador")
    return purchase


def save_purchase(
    db: Session, *, actor: AppUser, purchase_id: uuid.UUID, data: PurchaseData
) -> SavedPurchase:
    """Reemplaza el borrador completo y recalcula (R4). Un `updated_at` viejo se guarda
    igual, con el aviso `stale_data`."""
    purchase = _locked_draft(db, purchase_id, "editar")
    stale = data.updated_at is not None and data.updated_at != purchase.updated_at
    _check_date(data.purchase_date)
    _supplier(db, data.supplier_id)
    items, _, _ = _validated_items(db, data)
    charges = _validated_charges(data.charges)
    purchase.supplier_id = data.supplier_id
    purchase.purchase_date = data.purchase_date
    purchase.supplier_invoice_number = data.supplier_invoice_number or None
    purchase.currency = data.currency
    purchase.notes = data.notes or None
    purchase.updated_at = utcnow()
    _replace_lines(db, purchase, items, charges)
    db.flush()
    warnings = _warnings(db, purchase, stale=stale)
    db.commit()
    return SavedPurchase(purchase, warnings)


def discard_purchase(db: Session, *, purchase_id: uuid.UUID) -> None:
    """Descarta un borrador: gastos, líneas y compra, en ese orden (R2)."""
    purchase = _locked_draft(db, purchase_id, "descartar")
    db.execute(delete(PurchaseCharge).where(PurchaseCharge.purchase_id == purchase.id))
    db.execute(delete(PurchaseItem).where(PurchaseItem.purchase_id == purchase.id))
    db.delete(purchase)
    db.commit()


# --- Lectura --------------------------------------------------------------------------


def get_purchase(db: Session, purchase_id: uuid.UUID) -> Purchase:
    purchase = db.get(Purchase, purchase_id)
    if purchase is None:
        raise not_found()
    return purchase


def purchase_items(db: Session, purchase_id: uuid.UUID) -> list[PurchaseItem]:
    return list(
        db.scalars(
            select(PurchaseItem)
            .where(PurchaseItem.purchase_id == purchase_id)
            .order_by(PurchaseItem.line_number)
        )
    )


def purchase_charges(db: Session, purchase_id: uuid.UUID) -> list[PurchaseCharge]:
    return list(
        db.scalars(
            select(PurchaseCharge)
            .where(PurchaseCharge.purchase_id == purchase_id)
            .order_by(PurchaseCharge.line_number)
        )
    )


def purchase_void(db: Session, purchase_id: uuid.UUID) -> PurchaseVoid | None:
    return db.scalar(select(PurchaseVoid).where(PurchaseVoid.purchase_id == purchase_id))


def list_purchases(
    db: Session,
    *,
    status: str | None = None,
    supplier_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    product_id: uuid.UUID | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Purchase], int]:
    """Compras con filtros combinables, de la más reciente a la más antigua (FR-020)."""
    query = select(Purchase)
    if status:
        query = query.where(Purchase.status == status)
    if supplier_id:
        query = query.where(Purchase.supplier_id == supplier_id)
    if date_from:
        query = query.where(Purchase.purchase_date >= date_from)
    if date_to:
        query = query.where(Purchase.purchase_date <= date_to)
    if product_id:
        query = query.where(
            exists().where(
                PurchaseItem.purchase_id == Purchase.id, PurchaseItem.product_id == product_id
            )
        )
    if q and q.strip():
        text = q.strip().lower()
        query = query.where(
            or_(
                func.lower(Purchase.number).contains(text, autoescape=True),
                func.lower(Purchase.supplier_invoice_number).contains(text, autoescape=True),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(Purchase.purchase_date.desc(), Purchase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def item_counts(db: Session, purchase_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not purchase_ids:
        return {}
    return dict(
        db.execute(
            select(PurchaseItem.purchase_id, func.count())
            .where(PurchaseItem.purchase_id.in_(purchase_ids))
            .group_by(PurchaseItem.purchase_id)
        ).all()
    )


def purchases_of_movements(
    db: Session, movements: list[StockMovement]
) -> dict[uuid.UUID, tuple[uuid.UUID, str | None]]:
    """Compra de cada movimiento de compra o anulación, en una sola consulta (FR-021)."""
    item_ids = {m.reference_id: m.id for m in movements if m.reference_type == "purchase_item"}
    if not item_ids:
        return {}
    rows = db.execute(
        select(PurchaseItem.id, Purchase.id, Purchase.number)
        .join(Purchase, Purchase.id == PurchaseItem.purchase_id)
        .where(PurchaseItem.id.in_(item_ids))
    ).all()
    by_item = {item_id: (purchase_id, number) for item_id, purchase_id, number in rows}
    return {
        m.id: by_item[m.reference_id]
        for m in movements
        if m.reference_type == "purchase_item" and m.reference_id in by_item
    }


def draft_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Purchase).where(Purchase.status == "draft"))


# --- Confirmación ---------------------------------------------------------------------


def _lock_products(db: Session, items: list[PurchaseItem]) -> dict[uuid.UUID, Product]:
    """Bloquea los productos en orden de id: dos compras con los mismos productos no se
    bloquean entre sí (R3)."""
    return {
        product_id: lock_product(db, product_id)
        for product_id in sorted({item.product_id for item in items})
    }


def _cost_audit(
    db: Session,
    *,
    actor: AppUser,
    product: Product,
    purchase: Purchase,
    before: Decimal | None,
    after: Decimal | None,
    cause: str,
) -> None:
    record_audit(
        db,
        action="product.cost_updated",
        user_id=actor.id,
        entity_type="product",
        entity_id=product.id,
        before={"avg_cost_usd": None if before is None else str(before)},
        after={"avg_cost_usd": None if after is None else str(after)},
        details={
            "sku": product.sku,
            "cause": cause,
            "purchase_id": str(purchase.id),
            "purchase_number": purchase.number,
        },
    )


def stale_data() -> ApiError:
    return ApiError(
        409,
        "stale_data",
        "Otra persona cambió esta compra desde que la abriste: revísala y vuelve a confirmar",
    )


def confirm_purchase(
    db: Session, *, actor: AppUser, purchase_id: uuid.UUID, updated_at: datetime
) -> tuple[Purchase, list[CostChange]]:
    """Confirma la compra en una sola transacción (FR-008 a FR-015, R3)."""
    purchase = _locked_draft(db, purchase_id, "confirmar")
    if updated_at != purchase.updated_at:
        raise stale_data()
    supplier = db.get(Supplier, purchase.supplier_id)
    if not supplier.is_active:
        raise inactive_supplier(supplier)
    items = purchase_items(db, purchase.id)
    charges = purchase_charges(db, purchase.id)
    products = _lock_products(db, items)
    inactive = sorted(p.sku for p in products.values() if not p.is_active)
    if inactive:
        raise ApiError(
            409,
            "inactive_products",
            "Hay productos inactivos en la compra: reactívalos o quítalos",
            skus=inactive,
        )
    # Si la tasa de esa fecha cambió desde el último guardado (FR-012), los costos que se
    # revisaron ya no son los que se confirmarían: hay que guardar y revisar de nuevo.
    saved_rate = purchase.exchange_rate
    _recalculate(db, purchase, items, charges)
    if purchase.exchange_rate != saved_rate and (
        purchase.currency == "VES" or any(c.currency == "VES" for c in charges)
    ):
        raise ApiError(
            409,
            "rate_changed",
            "La tasa BCV de la fecha de la compra cambió desde que la guardaste: guárdala de "
            "nuevo para recalcular los costos y revísalos antes de confirmar",
        )
    db.flush()

    changes: list[CostChange] = []
    for item in items:
        product = products[item.product_id]
        before = product.avg_cost_usd
        after = weighted_average(product.stock, before, item.quantity, item.landed_unit_cost_usd)
        post_movement(
            db,
            product_id=product.id,
            type="purchase",
            quantity_delta=item.quantity,
            created_by=actor.id,
            reference_type="purchase_item",
            reference_id=item.id,
            cost_before_usd=before,
            cost_after_usd=after,
        )
        product.avg_cost_usd = after
        product.cost_locked = True
        changes.append(CostChange(product.id, product.sku, before, after))

    # El número se toma al final, en la misma transacción: no retiene el contador mientras
    # se procesan las líneas y un fallo no deja huecos (FR-008, R3).
    counter = db.get(SequenceCounter, "purchase", with_for_update=True)
    number = counter.next_number
    counter.next_number = number + 1
    purchase.number = f"C-{number:06d}"
    for change in changes:
        if change.cost_after_usd != change.cost_before_usd:
            _cost_audit(
                db,
                actor=actor,
                product=products[change.product_id],
                purchase=purchase,
                before=change.cost_before_usd,
                after=change.cost_after_usd,
                cause="purchase",
            )

    now = utcnow()
    purchase.status = "confirmed"
    purchase.confirmed_by = actor.id
    purchase.confirmed_at = now
    purchase.updated_at = now
    record_audit(
        db,
        action="purchase.confirmed",
        user_id=actor.id,
        entity_type="purchase",
        entity_id=purchase.id,
        details={
            "number": purchase.number,
            "supplier": supplier.name,
            "currency": purchase.currency,
            "exchange_rate": None
            if purchase.exchange_rate is None
            else str(purchase.exchange_rate),
            "merchandise_total_usd": str(purchase.merchandise_total_usd),
            "charges_total_usd": str(purchase.charges_total_usd),
            "total_usd": str(purchase.total_usd),
            "items": len(items),
        },
    )
    db.commit()
    return purchase, changes


# --- Anulación ------------------------------------------------------------------------


def _locked_confirmed(db: Session, purchase_id: uuid.UUID) -> Purchase:
    purchase = db.get(Purchase, purchase_id, with_for_update=True, populate_existing=True)
    if purchase is None:
        raise not_found()
    if purchase.status != "confirmed":
        raise invalid_state("Solo se puede anular una compra confirmada")
    return purchase


def _void_lines(
    items: list[PurchaseItem], products: dict[uuid.UUID, Product], units: dict[uuid.UUID, Unit]
) -> list[VoidPreviewLine]:
    lines = []
    for item in items:
        product = products[item.product_id]
        before = product.avg_cost_usd
        result = undo_purchase(product.stock, before, item.quantity, item.landed_unit_cost_usd)
        lines.append(
            VoidPreviewLine(
                product_id=product.id,
                sku=product.sku,
                unit_decimals=units[product.unit_id].decimals,
                stock_before=product.stock,
                stock_after=product.stock - item.quantity,
                cost_before_usd=before,
                cost_after_usd=before if result is None else result,
                keeps_cost=result is None,
            )
        )
    return lines


def _units(db: Session) -> dict[uuid.UUID, Unit]:
    return {unit.id: unit for unit in db.scalars(select(Unit))}


def void_preview(db: Session, *, purchase_id: uuid.UUID) -> list[VoidPreviewLine]:
    """Stock y costo que dejaría anular la compra, sin escribir nada (FR-019)."""
    purchase = get_purchase(db, purchase_id)
    if purchase.status != "confirmed":
        raise invalid_state("Solo se puede anular una compra confirmada")
    items = purchase_items(db, purchase.id)
    products = {
        p.id: p
        for p in db.scalars(select(Product).where(Product.id.in_({i.product_id for i in items})))
    }
    return _void_lines(items, products, _units(db))


def void_purchase(
    db: Session, *, actor: AppUser, purchase_id: uuid.UUID, reason: str
) -> tuple[Purchase, int]:
    """Anula una compra confirmada (RN-14/FR-017, FR-018). Devuelve la compra y la
    cantidad de alertas creadas."""
    reason = reason.strip()
    if not 5 <= len(reason) <= 500:
        raise validation_error({"reason": "Escribe el motivo de la anulación (5 a 500 caracteres)"})
    purchase = _locked_confirmed(db, purchase_id)
    items = purchase_items(db, purchase.id)
    products = _lock_products(db, items)
    lines = _void_lines(items, products, _units(db))
    alerts = 0
    for item, line in zip(items, lines, strict=True):
        product = products[item.product_id]
        post_movement(
            db,
            product_id=product.id,
            type="purchase_void",
            quantity_delta=-item.quantity,
            created_by=actor.id,
            reference_type="purchase_item",
            reference_id=item.id,
            allow_negative=True,
            cost_before_usd=line.cost_before_usd,
            cost_after_usd=line.cost_after_usd,
        )
        if line.keeps_cost and line.cost_before_usd is not None:
            alerts += 1
            create_alert(
                db,
                type="purchase_void_cost",
                entity_type="purchase",
                entity_id=purchase.id,
                details={
                    "purchase_number": purchase.number,
                    "product_id": str(product.id),
                    "sku": product.sku,
                    "stock_before": format_quantity(line.stock_before, line.unit_decimals),
                    "stock_after": format_quantity(line.stock_after, line.unit_decimals),
                    "cost_kept": None
                    if line.cost_before_usd is None
                    else str(line.cost_before_usd),
                    "landed_unit_cost_usd": str(item.landed_unit_cost_usd),
                },
            )
        elif line.cost_after_usd != line.cost_before_usd:
            product.avg_cost_usd = line.cost_after_usd
            _cost_audit(
                db,
                actor=actor,
                product=product,
                purchase=purchase,
                before=line.cost_before_usd,
                after=line.cost_after_usd,
                cause="purchase_void",
            )
    db.add(
        PurchaseVoid(
            id=uuid.uuid7(),
            purchase_id=purchase.id,
            reason=reason,
            voided_by=actor.id,
            voided_at=utcnow(),
        )
    )
    # Solo cambia el estado: el trigger rechaza cualquier otro cambio (R2).
    purchase.status = "voided"
    record_audit(
        db,
        action="purchase.voided",
        user_id=actor.id,
        entity_type="purchase",
        entity_id=purchase.id,
        reason=reason,
        details={"number": purchase.number, "alerts": alerts},
    )
    db.commit()
    return purchase, alerts
