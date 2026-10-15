"""Esquemas de equipos, caja y ventas (contrato: specs/004-ventas-multimoneda/contracts/
api.md). Decimales como cadenas (ADR-0004); fechas ISO."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.product_schemas import UserRef, user_ref
from app.api.purchase_schemas import cost_str
from app.db.models import (
    AppUser,
    CashSession,
    Customer,
    Device,
    Payment,
    Product,
    Sale,
    SaleItem,
    SaleVoid,
    Unit,
)
from app.domain.money import round_usd
from app.domain.roles import Role
from app.domain.units import format_quantity
from app.services.devices import open_cash_session
from app.services.users import users_by_id

CENT = Decimal("0.01")
# Orden de los movimientos de dinero en el detalle: pagos, vueltos y lo de la anulación.
PAYMENT_KIND_ORDER = {"sale_payment": 0, "change": 1, "void_refund": 2, "void_change": 3}


class CashSessionOut(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    business_date: date
    opened_by: UserRef
    opened_at: datetime
    opening_float_ves: str
    opening_float_usd: str
    status: str


class OpenCashSessionRef(BaseModel):
    id: uuid.UUID
    opened_by: UserRef
    opened_at: datetime
    business_date: date


class DeviceOut(BaseModel):
    id: uuid.UUID
    name: str
    series: str
    last_sequence_number: int
    registered_by: UserRef
    registered_at: datetime
    revoked_at: datetime | None
    open_cash_session: OpenCashSessionRef | None


class DeviceRegistered(DeviceOut):
    """Respuesta del registro: única vez que se entrega el token (research R3)."""

    token: str


class DeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=60)


def cash_session_out(db: Session, session: CashSession) -> CashSessionOut:
    opener = users_by_id(db, {session.opened_by})[session.opened_by]
    return CashSessionOut(
        id=session.id,
        device_id=session.device_id,
        business_date=session.business_date,
        opened_by=user_ref(opener),
        opened_at=session.opened_at,
        opening_float_ves=str(session.opening_float_ves),
        opening_float_usd=str(session.opening_float_usd),
        status=session.status,
    )


def devices_out(db: Session, devices: list[Device]) -> list[DeviceOut]:
    sessions = {device.id: open_cash_session(db, device.id) for device in devices}
    users = users_by_id(
        db,
        {device.registered_by for device in devices}
        | {session.opened_by for session in sessions.values() if session is not None},
    )
    result = []
    for device in devices:
        session = sessions[device.id]
        result.append(
            DeviceOut(
                id=device.id,
                name=device.name,
                series=device.series,
                last_sequence_number=device.last_sequence_number,
                registered_by=user_ref(users[device.registered_by]),
                registered_at=device.registered_at,
                revoked_at=device.revoked_at,
                open_cash_session=None
                if session is None
                else OpenCashSessionRef(
                    id=session.id,
                    opened_by=user_ref(users[session.opened_by]),
                    opened_at=session.opened_at,
                    business_date=session.business_date,
                ),
            )
        )
    return result


# --- Venta (RF-26; research R12) --------------------------------------------------------


class ProductRefOut(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    unit_code: str
    unit_decimals: int


class DiscountOut(BaseModel):
    type: str
    value: str
    amount_usd: str
    authorized_by: UserRef | None
    method: str | None


class SaleItemSeller(BaseModel):
    id: uuid.UUID
    line_number: int
    product: ProductRefOut
    quantity: str
    entered_unit: str
    unit_price_usd: str
    server_price_usd: str | None
    line_subtotal_usd: str
    item_discount: DiscountOut | None
    allocated_sale_discount_usd: str
    line_total_usd: str


class SaleItemAdmin(SaleItemSeller):
    unit_cost_usd: str | None
    margin_usd: str | None


class PaymentOut(BaseModel):
    kind: str
    method: str
    currency: str
    amount: str
    amount_usd: str
    reference: str | None


class CustomerOut(BaseModel):
    id: uuid.UUID
    name: str
    document_id: str | None
    phone: str | None


class DeviceRef(BaseModel):
    id: uuid.UUID
    name: str
    series: str


class SaleVoidOut(BaseModel):
    reason: str
    voided_by: UserRef
    voided_at: datetime


class SaleSeller(BaseModel):
    id: uuid.UUID
    number: str
    status: str
    needs_review: bool
    device: DeviceRef
    cash_session_id: uuid.UUID
    seller: UserRef
    customer: CustomerOut | None
    occurred_at: datetime
    business_date: date
    synced_at: datetime
    exchange_rate: str
    exchange_rate_date: date
    items: list[SaleItemSeller]
    subtotal_usd: str
    discount: DiscountOut | None
    discount_usd: str
    total_usd: str
    total_ves: str
    paid_usd: str
    change_usd: str
    overpaid_usd: str
    device_total_usd: str
    payments: list[PaymentOut]
    void: SaleVoidOut | None


class SaleAdmin(SaleSeller):
    items: list[SaleItemAdmin]
    cost_usd: str | None
    margin_usd: str | None


class SaleSummary(BaseModel):
    id: uuid.UUID
    number: str
    status: str
    needs_review: bool
    occurred_at: datetime
    business_date: date
    seller: UserRef
    customer_name: str | None
    device_name: str
    total_usd: str
    total_ves: str


class SalePage(BaseModel):
    items: list[SaleSummary]
    total: int
    page: int
    page_size: int


def money_str(value: Decimal) -> str:
    return str(value.quantize(CENT))


def _discount(
    discount_type: str | None,
    value: Decimal | None,
    amount: Decimal,
    authorized_by: uuid.UUID | None,
    method: str | None,
    users: dict[uuid.UUID, AppUser],
) -> DiscountOut | None:
    if discount_type is None or value is None:
        return None
    return DiscountOut(
        type=discount_type,
        value=money_str(value),
        amount_usd=money_str(amount),
        authorized_by=user_ref(users.get(authorized_by)) if authorized_by else None,
        method=method,
    )


def _grouped[T](rows: list[T], key: str) -> dict[uuid.UUID, list[T]]:
    grouped: dict[uuid.UUID, list[T]] = {}
    for row in rows:
        grouped.setdefault(getattr(row, key), []).append(row)
    return grouped


def sales_for_role(db: Session, sales: list[Sale], role: Role) -> list[SaleSeller]:
    """Ventas con el esquema de su rol: el Admin recibe costo y margen; el Vendedor nunca
    (principio IV, R12). El rol se lee de la base, nunca del token (ADR-0008)."""
    if not sales:
        return []
    ids = [sale.id for sale in sales]
    items = list(
        db.scalars(select(SaleItem).where(SaleItem.sale_id.in_(ids)).order_by(SaleItem.line_number))
    )
    payments = sorted(
        db.scalars(select(Payment).where(Payment.sale_id.in_(ids))),
        key=lambda payment: (PAYMENT_KIND_ORDER[payment.kind], payment.line_number),
    )
    voids = {
        void.sale_id: void for void in db.scalars(select(SaleVoid).where(SaleVoid.sale_id.in_(ids)))
    }
    products = {
        product.id: (product, unit)
        for product, unit in db.execute(
            select(Product, Unit)
            .join(Unit, Unit.id == Product.unit_id)
            .where(Product.id.in_({item.product_id for item in items}))
        )
    }
    customer_ids = {sale.customer_id for sale in sales if sale.customer_id}
    customers = {
        customer.id: customer
        for customer in db.scalars(select(Customer).where(Customer.id.in_(customer_ids)))
    }
    devices = {
        device.id: device
        for device in db.scalars(
            select(Device).where(Device.id.in_({sale.device_id for sale in sales}))
        )
    }
    users = users_by_id(
        db,
        {sale.seller_id for sale in sales}
        | {sale.discount_authorized_by for sale in sales}
        | {item.item_discount_authorized_by for item in items}
        | {void.voided_by for void in voids.values()},
    )
    items_by_sale = _grouped(items, "sale_id")
    payments_by_sale = _grouped(payments, "sale_id")

    admin = role == Role.ADMIN
    result: list[SaleSeller] = []
    for sale in sales:
        lines: list = []
        total_cost: Decimal | None = Decimal("0")
        for item in items_by_sale.get(sale.id, []):
            product, unit = products[item.product_id]
            base = {
                "id": item.id,
                "line_number": item.line_number,
                "product": ProductRefOut(
                    id=product.id,
                    sku=product.sku,
                    name=product.name,
                    unit_code=unit.code,
                    unit_decimals=unit.decimals,
                ),
                "quantity": format_quantity(item.quantity, unit.decimals),
                "entered_unit": item.entered_unit,
                "unit_price_usd": money_str(item.unit_price_usd),
                "server_price_usd": None
                if item.server_price_usd is None
                else money_str(item.server_price_usd),
                "line_subtotal_usd": money_str(item.line_subtotal_usd),
                "item_discount": _discount(
                    item.item_discount_type,
                    item.item_discount_value,
                    item.item_discount_usd,
                    item.item_discount_authorized_by,
                    item.item_discount_authorization_method,
                    users,
                ),
                "allocated_sale_discount_usd": money_str(item.allocated_sale_discount_usd),
                "line_total_usd": money_str(item.line_total_usd),
            }
            if not admin:
                lines.append(SaleItemSeller(**base))
                continue
            line_cost = (
                None
                if item.unit_cost_usd is None
                else round_usd(item.unit_cost_usd * item.quantity)
            )
            total_cost = None if line_cost is None or total_cost is None else total_cost + line_cost
            lines.append(
                SaleItemAdmin(
                    **base,
                    unit_cost_usd=cost_str(item.unit_cost_usd),
                    margin_usd=None
                    if line_cost is None
                    else money_str(item.line_total_usd - line_cost),
                )
            )
        void = voids.get(sale.id)
        customer = customers.get(sale.customer_id) if sale.customer_id else None
        device = devices[sale.device_id]
        overpaid = max(sale.paid_usd - sale.total_usd - sale.change_usd, Decimal("0"))
        common = {
            "id": sale.id,
            "number": sale.number,
            "status": "voided" if void else "registered",
            "needs_review": sale.needs_review,
            "device": DeviceRef(id=device.id, name=device.name, series=device.series),
            "cash_session_id": sale.cash_session_id,
            "seller": user_ref(users[sale.seller_id]),
            "customer": None
            if customer is None
            else CustomerOut(
                id=customer.id,
                name=customer.name,
                document_id=customer.document_id,
                phone=customer.phone,
            ),
            "occurred_at": sale.occurred_at,
            "business_date": sale.business_date,
            "synced_at": sale.synced_at,
            "exchange_rate": str(sale.exchange_rate),
            "exchange_rate_date": sale.exchange_rate_date,
            "subtotal_usd": money_str(sale.subtotal_usd),
            "discount": _discount(
                sale.discount_type,
                sale.discount_value,
                sale.discount_usd,
                sale.discount_authorized_by,
                sale.discount_authorization_method,
                users,
            ),
            "discount_usd": money_str(sale.discount_usd),
            "total_usd": money_str(sale.total_usd),
            "total_ves": money_str(sale.total_ves),
            "paid_usd": money_str(sale.paid_usd),
            "change_usd": money_str(sale.change_usd),
            "overpaid_usd": money_str(overpaid),
            "device_total_usd": money_str(sale.device_total_usd),
            "payments": [
                PaymentOut(
                    kind=payment.kind,
                    method=payment.payment_method_code,
                    currency=payment.currency,
                    amount=money_str(payment.amount),
                    amount_usd=money_str(payment.amount_usd),
                    reference=payment.reference,
                )
                for payment in payments_by_sale.get(sale.id, [])
            ],
            "void": None
            if void is None
            else SaleVoidOut(
                reason=void.reason,
                voided_by=user_ref(users[void.voided_by]),
                voided_at=void.voided_at,
            ),
        }
        if admin:
            result.append(
                SaleAdmin(
                    **common,
                    items=lines,
                    cost_usd=None if total_cost is None else money_str(total_cost),
                    margin_usd=None
                    if total_cost is None
                    else money_str(sale.total_usd - total_cost),
                )
            )
        else:
            result.append(SaleSeller(**common, items=lines))
    return result
