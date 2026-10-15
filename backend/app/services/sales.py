"""Ventas del mostrador (RF-20 a RF-28; RN-02, RN-04 a RN-07, RN-10 a RN-13; research R4 a R6,
R8, R10 a R12, R16 y R17 de la etapa 1.3).

`create_sale` es el manejador de la operación `sale.create` de la cola. El servidor es la
autoridad: recalcula la venta con `domain/sale_math.py` y, en la misma transacción,
guarda la venta, sus líneas y pagos, las salidas de kardex, el cliente nuevo, las alertas
y la auditoría.

Nunca rechaza una venta por razones de negocio (stock, precio, total, tasa, descuento sin
autorización): la registra y crea una alerta para el Admin (RN-10, R6). Solo rechaza lo
estructural, que el equipo no envía si funciona bien (R4).
"""

import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import ApiError, validation_error
from app.db.models import (
    AppUser,
    CashSession,
    Customer,
    Device,
    DiscountAuthorization,
    ExchangeRate,
    Payment,
    PaymentMethod,
    Product,
    Sale,
    SaleItem,
    SaleVoid,
    StockMovement,
    Unit,
)
from app.domain.business_time import business_date
from app.domain.money import round_usd, validate_price, validate_rate, validate_usd_amount
from app.domain.roles import Role
from app.domain.sale_math import (
    DiscountInput,
    LineInput,
    MoneyInput,
    SaleInput,
    SaleResult,
    amount_usd,
    compute_sale,
)
from app.domain.units import validate_quantity
from app.services.alerts import create_sale_alert
from app.services.audit import record_audit
from app.services.customers import CustomerData, resolve_customer
from app.services.exchange_rates import BCV
from app.services.inventory import post_movement

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class DiscountData:
    type: str  # "amount" | "percent"
    value: Decimal
    authorization_id: uuid.UUID | None = None


@dataclass(frozen=True)
class ItemData:
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    entered_unit: str  # "m" | "cm" | "unit"
    unit_price_usd: Decimal
    discount: DiscountData | None = None


@dataclass(frozen=True)
class MoneyData:
    method: str
    amount: Decimal
    reference: str | None = None


@dataclass(frozen=True)
class SaleData:
    id: uuid.UUID
    sequence_number: int
    cash_session_id: uuid.UUID
    seller_id: uuid.UUID
    occurred_at: datetime
    exchange_rate: Decimal
    exchange_rate_date: date
    items: list[ItemData]
    payments: list[MoneyData]
    change: list[MoneyData]
    device_total_usd: Decimal
    discount: DiscountData | None = None
    customer: CustomerData | None = None
    customer_id: uuid.UUID | None = None


@dataclass
class SaleOutcome:
    sale: Sale
    alerts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Authorization:
    authorized_by: uuid.UUID | None
    method: str | None
    authorization_id: uuid.UUID | None


# --- Validación estructural -------------------------------------------------------------


def _field_error(name: str, message: str) -> ApiError:
    return validation_error({f"payload.{name}": message})


def _lock_device(db: Session, device: Device) -> None:
    """Serializa las ventas de un mismo equipo: correlativo y caja sin carreras."""
    db.execute(select(Device.id).where(Device.id == device.id).with_for_update())


def _cash_session(db: Session, device: Device, session_id: uuid.UUID) -> CashSession:
    session = db.get(CashSession, session_id, with_for_update=True)
    if session is None or session.device_id != device.id or session.status != "open":
        raise ApiError(
            409,
            "cash_session_unavailable",
            "La caja de la venta no está abierta en este equipo",
        )
    return session


def _check_sequence(db: Session, device: Device, sequence_number: int) -> None:
    taken = db.scalar(
        select(Sale.id).where(Sale.series == device.series, Sale.sequence_number == sequence_number)
    )
    if taken is not None:
        raise ApiError(
            409,
            "sequence_conflict",
            "Ese número de venta ya se usó en este equipo: el equipo debe registrarse de nuevo",
            number=sale_number(device.series, sequence_number),
        )


def _products(db: Session, items: list[ItemData]) -> dict[uuid.UUID, tuple[Product, Unit]]:
    """Productos de la venta, bloqueados en orden de id para evitar bloqueos cruzados entre
    ventas simultáneas (R16)."""
    ids = sorted({item.product_id for item in items})
    rows = db.execute(
        select(Product, Unit)
        .join(Unit, Unit.id == Product.unit_id)
        .where(Product.id.in_(ids))
        .order_by(Product.id)
        .with_for_update(of=Product)
    ).all()
    found = {product.id: (product, unit) for product, unit in rows}
    for index, item in enumerate(items):
        if item.product_id not in found:
            raise _field_error(f"items.{index}.product_id", "El producto no existe")
    return found


def _validated_items(
    items: list[ItemData], products: dict[uuid.UUID, tuple[Product, Unit]]
) -> list[ItemData]:
    result = []
    for index, item in enumerate(items):
        _, unit = products[item.product_id]
        try:
            quantity = validate_quantity(
                item.quantity, unit.decimals, allow_zero=False, allow_negative=False
            )
        except ValueError as exc:
            raise _field_error(f"items.{index}.quantity", str(exc)) from exc
        try:
            price = validate_price(item.unit_price_usd)
        except ValueError as exc:
            raise _field_error(f"items.{index}.unit_price_usd", str(exc)) from exc
        result.append(
            ItemData(item.id, item.product_id, quantity, item.entered_unit, price, item.discount)
        )
    return result


def _validated_money(
    db: Session, entries: list[MoneyData], group: str
) -> list[tuple[MoneyData, PaymentMethod]]:
    methods = {method.code: method for method in db.scalars(select(PaymentMethod))}
    result = []
    for index, entry in enumerate(entries):
        method = methods.get(entry.method)
        if method is None:
            raise _field_error(f"{group}.{index}.method", "El método de pago no existe")
        try:
            amount = validate_usd_amount(entry.amount)
        except ValueError as exc:
            raise _field_error(f"{group}.{index}.amount", str(exc)) from exc
        reference = (entry.reference or "").strip() or None
        if method.requires_reference and reference is None:
            raise _field_error(f"{group}.{index}.reference", "Este método exige referencia")
        if reference is not None and len(reference) > 60:
            raise _field_error(f"{group}.{index}.reference", "Admite como máximo 60 caracteres")
        result.append((MoneyData(entry.method, amount, reference), method))
    return result


def _money_inputs(entries: list[tuple[MoneyData, PaymentMethod]]) -> list[MoneyInput]:
    return [MoneyInput(entry.method, method.currency, entry.amount) for entry, method in entries]


def _discount_input(discount: DiscountData | None) -> DiscountInput | None:
    return None if discount is None else DiscountInput(discount.type, discount.value)


def sale_number(series: str, sequence_number: int) -> str:
    return f"{series}-{sequence_number:06d}"


# --- Cálculo, autorizaciones y alertas -------------------------------------------------


def _compute(
    data: SaleData,
    items: list[ItemData],
    payments: list[tuple[MoneyData, PaymentMethod]],
    change: list[tuple[MoneyData, PaymentMethod]],
) -> tuple[SaleResult, list[Decimal], bool]:
    """Recalcula la venta. Devuelve el resultado, lo que cubre cada vuelto en USD y si el
    total del equipo difiere del del servidor.

    Con el mismo total en el equipo y en el servidor, pagos que no cubren o un vuelto mayor
    que el excedente son un error del equipo (422). Si los totales difieren, la venta se
    registra igual y se alerta (FR-032): el equipo cobró sobre su total.
    """
    lines = [
        LineInput(str(item.id), item.unit_price_usd, item.quantity, _discount_input(item.discount))
        for item in items
    ]
    base = SaleInput(
        rate=data.exchange_rate,
        lines=lines,
        discount=_discount_input(data.discount),
        payments=_money_inputs(payments),
    )
    try:
        result = compute_sale(base)
    except ValueError as exc:
        raise _field_error("items", str(exc)) from exc
    change_inputs = _money_inputs(change)
    change_usd = [amount_usd(entry, data.exchange_rate) for entry in change_inputs]
    mismatch = result.total_usd != data.device_total_usd
    if not mismatch:
        if result.balance_usd > 0:
            raise _field_error("payments", "Los pagos no cubren el total de la venta")
        if sum(change_usd, ZERO) > result.excess_usd:
            raise _field_error("change", "El vuelto no puede ser mayor que el excedente")
    return result, change_usd, mismatch


def _authorize(
    db: Session,
    *,
    seller: AppUser,
    sale_id: uuid.UUID,
    sale_item_id: uuid.UUID | None,
    discount: DiscountData,
    base_usd: Decimal,
) -> Authorization | None:
    """Quién autorizó un descuento (RN-07, R8). None si es de un Vendedor sin autorización
    válida: la venta se registra igual y va a revisión (FR-028)."""
    if seller.role == Role.ADMIN.value:
        return Authorization(seller.id, "admin_self", None)
    if discount.authorization_id is None:
        return None
    authorization = db.get(DiscountAuthorization, discount.authorization_id, with_for_update=True)
    matches = (
        authorization is not None
        and authorization.status == "approved"
        and authorization.sale_id == sale_id
        and authorization.sale_item_id == sale_item_id
        and authorization.discount_type == discount.type
        and authorization.discount_value == discount.value
        and authorization.base_usd == base_usd
    )
    if not matches:
        return None
    used = db.scalar(
        select(Sale.id).where(Sale.discount_authorization_id == authorization.id)
    ) or db.scalar(
        select(SaleItem.id).where(SaleItem.item_discount_authorization_id == authorization.id)
    )
    if used is not None:
        return None
    return Authorization(authorization.decided_by, authorization.method, authorization.id)


def _rate_matches(db: Session, rate: Decimal, on_date: date) -> tuple[bool, Decimal | None]:
    loaded = db.scalar(
        select(ExchangeRate.rate).where(
            ExchangeRate.rate_type == BCV, ExchangeRate.business_date == on_date
        )
    )
    return loaded is not None and loaded == rate, loaded


# --- Registro ----------------------------------------------------------------------------


def create_sale(
    db: Session, *, device: Device, user: AppUser, operation_id: uuid.UUID, data: SaleData
) -> SaleOutcome:
    """Registra la venta completa en la transacción en curso (FR-018)."""
    _lock_device(db, device)
    if data.seller_id != user.id:
        raise _field_error("seller_id", "La venta debe quedar a nombre de quien la envía")
    seller = user
    if data.sequence_number < 1:
        raise _field_error("sequence_number", "El correlativo empieza en 1")
    try:
        rate = validate_rate(data.exchange_rate)
    except ValueError as exc:
        raise _field_error("exchange_rate", str(exc)) from exc
    if not data.items:
        raise _field_error("items", "La venta no tiene productos")
    session = _cash_session(db, device, data.cash_session_id)
    _check_sequence(db, device, data.sequence_number)
    products = _products(db, data.items)
    items = _validated_items(data.items, products)
    payments = _validated_money(db, data.payments, "payments")
    change = _validated_money(db, data.change, "change")
    data = replace(data, exchange_rate=rate)
    result, change_usd, total_mismatch = _compute(data, items, payments, change)
    customer: Customer | None = resolve_customer(
        db, actor=user, data=data.customer, customer_id=data.customer_id
    )

    outcome_alerts: dict[str, dict] = {}
    warnings: list[str] = []
    needs_review = False

    # Autorizaciones de los descuentos, antes de insertar: la venta es de solo inserción y
    # su marca de revisión se decide aquí (RN-07, FR-028).
    sale_auth = None
    if data.discount is not None:
        sale_auth = _authorize(
            db,
            seller=seller,
            sale_id=data.id,
            sale_item_id=None,
            discount=data.discount,
            base_usd=result.subtotal_usd,
        )
        needs_review = needs_review or sale_auth is None
    item_auths: list[Authorization | None] = []
    for item, line in zip(items, result.lines, strict=True):
        item_auth = None
        if item.discount is not None:
            item_auth = _authorize(
                db,
                seller=seller,
                sale_id=data.id,
                sale_item_id=item.id,
                discount=item.discount,
                base_usd=line.line_subtotal_usd,
            )
            needs_review = needs_review or item_auth is None
        item_auths.append(item_auth)

    number = sale_number(device.series, data.sequence_number)
    sale = Sale(
        id=data.id,
        device_id=device.id,
        series=device.series,
        sequence_number=data.sequence_number,
        number=number,
        cash_session_id=session.id,
        seller_id=seller.id,
        customer_id=customer.id if customer else None,
        occurred_at=data.occurred_at,
        business_date=business_date(data.occurred_at),
        synced_at=utcnow(),
        exchange_rate=rate,
        exchange_rate_date=data.exchange_rate_date,
        subtotal_usd=result.subtotal_usd,
        discount_type=data.discount.type if data.discount else None,
        discount_value=data.discount.value if data.discount else None,
        discount_usd=result.discount_usd,
        discount_authorized_by=sale_auth.authorized_by if sale_auth else None,
        discount_authorization_method=sale_auth.method if sale_auth else None,
        discount_authorization_id=sale_auth.authorization_id if sale_auth else None,
        total_usd=result.total_usd,
        total_ves=result.total_ves,
        paid_usd=result.paid_usd,
        change_usd=sum(change_usd, ZERO),
        device_total_usd=round_usd(data.device_total_usd),
        needs_review=needs_review,
        outbox_operation_id=operation_id,
    )
    db.add(sale)
    db.flush()

    price_mismatches = []
    discount_details = []
    sale_items: list[SaleItem] = []
    for index, (item, line, item_auth) in enumerate(
        zip(items, result.lines, item_auths, strict=True)
    ):
        product, _ = products[item.product_id]
        if item.discount is not None:
            discount_details.append(
                {
                    "line_number": index + 1,
                    "sku": product.sku,
                    "type": item.discount.type,
                    "value": str(item.discount.value),
                    "amount_usd": str(line.item_discount_usd),
                    "authorized_by": str(item_auth.authorized_by) if item_auth else None,
                    "method": item_auth.method if item_auth else None,
                }
            )
        server_price = product.sale_price_usd
        if server_price != item.unit_price_usd:
            price_mismatches.append(
                {
                    "sku": product.sku,
                    "name": product.name,
                    "sale_price_usd": str(item.unit_price_usd),
                    "server_price_usd": None if server_price is None else str(server_price),
                }
            )
        sale_item = SaleItem(
            id=item.id,
            sale_id=sale.id,
            line_number=index + 1,
            product_id=product.id,
            quantity=item.quantity,
            entered_unit=item.entered_unit,
            unit_price_usd=item.unit_price_usd,
            server_price_usd=server_price if server_price != item.unit_price_usd else None,
            line_subtotal_usd=line.line_subtotal_usd,
            item_discount_type=item.discount.type if item.discount else None,
            item_discount_value=item.discount.value if item.discount else None,
            item_discount_usd=line.item_discount_usd,
            item_discount_authorized_by=item_auth.authorized_by if item_auth else None,
            item_discount_authorization_method=item_auth.method if item_auth else None,
            item_discount_authorization_id=item_auth.authorization_id if item_auth else None,
            allocated_sale_discount_usd=line.allocated_sale_discount_usd,
            line_total_usd=line.line_total_usd,
            unit_cost_usd=product.avg_cost_usd,
        )
        db.add(sale_item)
        sale_items.append(sale_item)
    db.flush()

    for index, ((entry, method), covered) in enumerate(
        zip(payments, result.payments_usd, strict=True)
    ):
        db.add(_payment(sale, session, index + 1, "sale_payment", entry, method, covered))
    for index, ((entry, method), covered) in enumerate(zip(change, change_usd, strict=True)):
        db.add(_payment(sale, session, index + 1, "change", entry, method, covered))
    db.flush()

    # Salidas de kardex: se admiten aunque dejen el stock negativo (RN-10).
    negatives = []
    for sale_item in sorted(sale_items, key=lambda line: line.product_id):
        movement = post_movement(
            db,
            product_id=sale_item.product_id,
            type="sale",
            quantity_delta=-sale_item.quantity,
            created_by=seller.id,
            reference_type="sale_item",
            reference_id=sale_item.id,
            allow_negative=True,
            device_id=device.id,
        )
        if movement.balance_after < 0:
            product, _ = products[sale_item.product_id]
            negatives.append(
                {
                    "sku": product.sku,
                    "name": product.name,
                    "quantity": str(sale_item.quantity),
                    "stock_after": str(movement.balance_after),
                }
            )

    if data.sequence_number > device.last_sequence_number:
        device.last_sequence_number = data.sequence_number

    # Alertas: una por tipo y venta (R6).
    if negatives:
        outcome_alerts["negative_stock"] = {"products": negatives}
        warnings.append("negative_stock")
    if price_mismatches:
        outcome_alerts["price_mismatch"] = {"products": price_mismatches}
    if total_mismatch:
        outcome_alerts["total_mismatch"] = {
            "device_total_usd": str(sale.device_total_usd),
            "server_total_usd": str(result.total_usd),
            "balance_usd": str(result.balance_usd),
        }
    rate_ok, loaded_rate = _rate_matches(db, rate, data.exchange_rate_date)
    if not rate_ok:
        outcome_alerts["rate_mismatch"] = {
            "sale_rate": str(rate),
            "loaded_rate": None if loaded_rate is None else str(loaded_rate),
            "rate_date": data.exchange_rate_date.isoformat(),
        }
    if needs_review:
        outcome_alerts["discount_review"] = {"seller": seller.full_name}
    if not seller.is_active:
        outcome_alerts["inactive_user_sync"] = {"seller": seller.full_name}
    for alert_type, details in outcome_alerts.items():
        create_sale_alert(db, type=alert_type, sale=sale, details=details)

    if data.discount is not None or discount_details:
        record_audit(
            db,
            action="sale.discounted",
            user_id=seller.id,
            device_id=device.id,
            entity_type="sale",
            entity_id=sale.id,
            details={
                "number": number,
                "sale_discount": None
                if data.discount is None
                else {
                    "type": data.discount.type,
                    "value": str(data.discount.value),
                    "amount_usd": str(result.discount_usd),
                    "authorized_by": str(sale_auth.authorized_by) if sale_auth else None,
                    "method": sale_auth.method if sale_auth else None,
                },
                "item_discounts": discount_details,
                "needs_review": needs_review,
            },
        )
    return SaleOutcome(sale=sale, alerts=list(outcome_alerts), warnings=warnings)


# --- Consulta (FR-045, FR-046; research R12) -------------------------------------------


@dataclass(frozen=True)
class SaleFilters:
    date_from: date | None = None
    date_to: date | None = None
    number: str | None = None
    seller_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    device_id: uuid.UUID | None = None
    status: str | None = None  # "registered" | "voided" | "needs_review"


def _visible_to(actor: AppUser):
    """El Vendedor solo ve sus ventas cuya fecha de negocio es hoy en Caracas (matriz de
    permisos, FR-046); el servidor lo impone en la consulta."""
    if actor.role == Role.ADMIN.value:
        return []
    return [Sale.seller_id == actor.id, Sale.business_date == business_date(utcnow())]


def list_sales(
    db: Session, *, actor: AppUser, filters: SaleFilters, page: int, page_size: int
) -> tuple[list[Sale], int]:
    conditions = list(_visible_to(actor))
    if actor.role == Role.ADMIN.value:
        if filters.date_from:
            conditions.append(Sale.business_date >= filters.date_from)
        if filters.date_to:
            conditions.append(Sale.business_date <= filters.date_to)
        if filters.seller_id:
            conditions.append(Sale.seller_id == filters.seller_id)
    if filters.number:
        conditions.append(Sale.number.ilike(f"%{filters.number.strip()}%"))
    if filters.customer_id:
        conditions.append(Sale.customer_id == filters.customer_id)
    if filters.device_id:
        conditions.append(Sale.device_id == filters.device_id)
    voided = select(SaleVoid.id).where(SaleVoid.sale_id == Sale.id).exists()
    if filters.status == "voided":
        conditions.append(voided)
    elif filters.status == "registered":
        conditions.append(~voided)
    elif filters.status == "needs_review":
        conditions.append(Sale.needs_review)
    query = select(Sale).where(*conditions)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(Sale.occurred_at.desc(), Sale.number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def visible_sale(db: Session, *, actor: AppUser, sale_id: uuid.UUID) -> Sale:
    """Detalle de una venta; para el Vendedor, una ajena o de otro día es 404."""
    sale = db.scalar(select(Sale).where(Sale.id == sale_id, *_visible_to(actor)))
    if sale is None:
        raise ApiError(404, "not_found", "La venta no existe")
    return sale


def voided_ids(db: Session, sale_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not sale_ids:
        return set()
    return set(db.scalars(select(SaleVoid.sale_id).where(SaleVoid.sale_id.in_(sale_ids))))


def sales_of_movements(
    db: Session, movements: list[StockMovement]
) -> dict[uuid.UUID, tuple[uuid.UUID, str]]:
    """Venta de cada salida por venta o reverso por anulación, en una consulta (FR-048)."""
    item_ids = {m.reference_id for m in movements if m.reference_type == "sale_item"}
    if not item_ids:
        return {}
    rows = db.execute(
        select(SaleItem.id, Sale.id, Sale.number)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(SaleItem.id.in_(item_ids))
    ).all()
    by_item = {item_id: (sale_id, number) for item_id, sale_id, number in rows}
    return {
        m.id: by_item[m.reference_id]
        for m in movements
        if m.reference_type == "sale_item" and m.reference_id in by_item
    }


# --- Anulación (RF-27; FR-041 a FR-043; research R10) ----------------------------------

# Espejo de cada movimiento de dinero: lo que entró sale y lo que salió vuelve.
VOID_KIND = {"sale_payment": "void_refund", "change": "void_change"}


def get_sale(db: Session, sale_id: uuid.UUID, *, for_update: bool = False) -> Sale:
    sale = db.get(Sale, sale_id, with_for_update=for_update)
    if sale is None:
        raise ApiError(404, "not_found", "La venta no existe")
    return sale


def void_sale(db: Session, *, actor: AppUser, sale_id: uuid.UUID, reason: str) -> Sale:
    """Anula la venta completa en una transacción: reverso de kardex por línea y espejo de
    cada pago y vuelto en la caja de la venta. Una venta se anula una sola vez.

    La caja que recibe la devolución si la de la venta ya estuviera cerrada se decide en
    la etapa 1.4 (PRD §10); en esta etapa las cajas no se cierran."""
    sale = get_sale(db, sale_id, for_update=True)
    if db.scalar(select(SaleVoid.id).where(SaleVoid.sale_id == sale.id)) is not None:
        raise ApiError(409, "invalid_state", "La venta ya estaba anulada")
    sale_void = SaleVoid(
        id=uuid.uuid7(), sale_id=sale.id, reason=reason, voided_by=actor.id, voided_at=utcnow()
    )
    db.add(sale_void)
    db.flush()

    items = db.scalars(
        select(SaleItem).where(SaleItem.sale_id == sale.id).order_by(SaleItem.product_id)
    ).all()
    for item in items:
        post_movement(
            db,
            product_id=item.product_id,
            type="sale_void",
            quantity_delta=item.quantity,
            created_by=actor.id,
            reference_type="sale_item",
            reference_id=item.id,
            device_id=sale.device_id,
        )

    payments = db.scalars(
        select(Payment)
        .where(Payment.sale_id == sale.id, Payment.kind.in_(VOID_KIND))
        .order_by(Payment.kind, Payment.line_number)
    ).all()
    for payment in payments:
        db.add(
            Payment(
                id=uuid.uuid7(),
                sale_id=sale.id,
                line_number=payment.line_number,
                cash_session_id=sale.cash_session_id,
                kind=VOID_KIND[payment.kind],
                payment_method_code=payment.payment_method_code,
                currency=payment.currency,
                amount=payment.amount,
                exchange_rate=payment.exchange_rate,
                amount_usd=payment.amount_usd,
                reference=payment.reference,
                sale_void_id=sale_void.id,
            )
        )
    db.flush()
    record_audit(
        db,
        action="sale.voided",
        user_id=actor.id,
        device_id=sale.device_id,
        entity_type="sale",
        entity_id=sale.id,
        before={"number": sale.number, "total_usd": str(sale.total_usd), "status": "registered"},
        after={"status": "voided"},
        reason=reason,
    )
    return sale


def _payment(
    sale: Sale,
    session: CashSession,
    line_number: int,
    kind: str,
    entry: MoneyData,
    method: PaymentMethod,
    covered: Decimal,
) -> Payment:
    return Payment(
        id=uuid.uuid7(),
        sale_id=sale.id,
        line_number=line_number,
        cash_session_id=session.id,
        kind=kind,
        payment_method_code=method.code,
        currency=method.currency,
        amount=entry.amount,
        exchange_rate=sale.exchange_rate,
        amount_usd=covered,
        reference=entry.reference,
    )
