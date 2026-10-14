"""Esquemas de compras (contracts/api.md; research R7).

Admin y Almacén reciben la misma compra, con los costos de factura, los gastos y el
costo final de cada línea (excepción del principio IV, constitución 1.2.0). Solo el
Admin recibe `cost_changes` (costo promedio antes y después) al confirmar. Ningún
esquema tiene `avg_cost_usd`, `cost_before_usd` ni `cost_after_usd` del producto fuera de
`cost_changes`.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.product_schemas import UnitRef, UserRef, unit_ref, user_ref
from app.db.models import Product, Purchase, Supplier, Unit
from app.domain.units import format_quantity
from app.services import purchases as purchases_service
from app.services.purchases import ChargeData, CostChange, ItemData, PurchaseData
from app.services.users import users_by_id

Currency = Literal["USD", "VES"]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
InvoiceNumber = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class PurchaseItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: uuid.UUID
    quantity: Decimal
    unit_cost: Decimal


class PurchaseChargeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Description
    charge_type: Literal["percent", "fixed"]
    percent: Decimal | None = None
    amount: Decimal | None = None
    currency: Currency | None = None
    charge_template_id: uuid.UUID | None = None


class PurchaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_id: uuid.UUID
    purchase_date: date
    currency: Currency
    supplier_invoice_number: InvoiceNumber | None = None
    notes: Notes | None = None
    items: list[PurchaseItemInput]
    charges: list[PurchaseChargeInput] = []
    updated_at: datetime | None = None

    def to_data(self) -> PurchaseData:
        return PurchaseData(
            supplier_id=self.supplier_id,
            purchase_date=self.purchase_date,
            currency=self.currency,
            supplier_invoice_number=self.supplier_invoice_number,
            notes=self.notes,
            items=[ItemData(i.product_id, i.quantity, i.unit_cost) for i in self.items],
            charges=[
                ChargeData(
                    c.description,
                    c.charge_type,
                    c.percent,
                    c.amount,
                    c.currency,
                    c.charge_template_id,
                )
                for c in self.charges
            ],
            updated_at=self.updated_at,
        )


class ConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updated_at: datetime


class VoidInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]


class SupplierRef(BaseModel):
    id: uuid.UUID
    name: str
    rif: str | None


class PurchaseProductRef(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    unit: UnitRef


class PurchaseItemOut(BaseModel):
    id: uuid.UUID
    line_number: int
    product: PurchaseProductRef
    quantity: str
    unit_cost_ves: str | None
    unit_cost_usd: str
    line_total_ves: str | None
    line_total_usd: str
    allocated_charges_usd: str
    landed_unit_cost_usd: str


class PurchaseChargeOut(BaseModel):
    id: uuid.UUID
    line_number: int
    description: str
    charge_type: str
    percent: str | None
    amount: str | None
    currency: str | None
    amount_usd: str
    allocation_method: str
    charge_template_id: uuid.UUID | None


class PurchaseVoidOut(BaseModel):
    reason: str
    voided_by: UserRef | None
    voided_at: datetime


class PurchaseWarning(BaseModel):
    code: str
    message: str
    purchase_number: str | None = None


class PurchaseOut(BaseModel):
    id: uuid.UUID
    number: str | None
    status: str
    supplier: SupplierRef
    purchase_date: date
    supplier_invoice_number: str | None
    currency: str
    exchange_rate: str | None
    exchange_rate_date: date | None
    notes: str | None
    items: list[PurchaseItemOut]
    charges: list[PurchaseChargeOut]
    merchandise_total_usd: str
    merchandise_total_ves: str | None
    charges_total_usd: str
    total_usd: str
    created_by: UserRef | None
    created_at: datetime
    updated_at: datetime
    confirmed_by: UserRef | None
    confirmed_at: datetime | None
    void: PurchaseVoidOut | None
    warnings: list[PurchaseWarning] = []


class CostChangeOut(BaseModel):
    product_id: uuid.UUID
    sku: str
    cost_before_usd: str | None
    cost_after_usd: str | None


class PurchaseConfirmedAdmin(PurchaseOut):
    """Respuesta de confirmar para el Admin: el costo promedio antes y después (R7)."""

    cost_changes: list[CostChangeOut]


class PurchaseVoidedOut(PurchaseOut):
    alerts_created: int


class PurchaseSummary(BaseModel):
    id: uuid.UUID
    number: str | None
    status: str
    purchase_date: date
    supplier: SupplierRef
    supplier_invoice_number: str | None
    currency: str
    total_usd: str
    items_count: int
    created_at: datetime


class PurchasePage(BaseModel):
    items: list[PurchaseSummary]
    total: int
    page: int
    page_size: int


class VoidPreviewItem(BaseModel):
    product_id: uuid.UUID
    sku: str
    stock_before: str
    stock_after: str
    cost_before_usd: str | None
    cost_after_usd: str | None
    keeps_cost: bool


class VoidPreview(BaseModel):
    items: list[VoidPreviewItem]


def supplier_ref(supplier: Supplier) -> SupplierRef:
    return SupplierRef(id=supplier.id, name=supplier.name, rif=supplier.rif)


def _fixed(value: Decimal | None, decimals: int) -> str | None:
    """Decimal como cadena con la escala de su columna (ADR-0004), aunque el objeto aún
    no venga de la base."""
    return None if value is None else str(value.quantize(Decimal(1).scaleb(-decimals)))


def _usd(value: Decimal | None) -> str | None:
    return _fixed(value, 2)


def cost_str(value: Decimal | None) -> str | None:
    return _fixed(value, 6)


def purchase_out(
    db: Session, purchase: Purchase, *, warnings: list[dict[str, Any]] | None = None
) -> PurchaseOut:
    items = purchases_service.purchase_items(db, purchase.id)
    charges = purchases_service.purchase_charges(db, purchase.id)
    void = purchases_service.purchase_void(db, purchase.id)
    products = {
        p.id: p
        for p in db.scalars(select(Product).where(Product.id.in_({i.product_id for i in items})))
    }
    units = {unit.id: unit for unit in db.scalars(select(Unit))}
    users = users_by_id(
        db,
        {purchase.created_by, purchase.confirmed_by, void.voided_by if void else None},
    )
    supplier = db.get(Supplier, purchase.supplier_id)
    item_out = []
    for item in items:
        product = products[item.product_id]
        unit = units[product.unit_id]
        item_out.append(
            PurchaseItemOut(
                id=item.id,
                line_number=item.line_number,
                product=PurchaseProductRef(
                    id=product.id, sku=product.sku, name=product.name, unit=unit_ref(unit)
                ),
                quantity=format_quantity(item.quantity, unit.decimals),
                unit_cost_ves=_usd(item.unit_cost_ves),
                unit_cost_usd=cost_str(item.unit_cost_usd),
                line_total_ves=_usd(item.line_total_ves),
                line_total_usd=_usd(item.line_total_usd),
                allocated_charges_usd=_usd(item.allocated_charges_usd),
                landed_unit_cost_usd=cost_str(item.landed_unit_cost_usd),
            )
        )
    return PurchaseOut(
        id=purchase.id,
        number=purchase.number,
        status=purchase.status,
        supplier=supplier_ref(supplier),
        purchase_date=purchase.purchase_date,
        supplier_invoice_number=purchase.supplier_invoice_number,
        currency=purchase.currency,
        exchange_rate=_fixed(purchase.exchange_rate, 8),
        exchange_rate_date=purchase.exchange_rate_date,
        notes=purchase.notes,
        items=item_out,
        charges=[
            PurchaseChargeOut(
                id=charge.id,
                line_number=charge.line_number,
                description=charge.description,
                charge_type=charge.charge_type,
                percent=_usd(charge.percent),
                amount=_usd(charge.amount),
                currency=charge.currency,
                amount_usd=_usd(charge.amount_usd),
                allocation_method=charge.allocation_method,
                charge_template_id=charge.charge_template_id,
            )
            for charge in charges
        ],
        merchandise_total_usd=_usd(purchase.merchandise_total_usd),
        merchandise_total_ves=_usd(purchase.merchandise_total_ves),
        charges_total_usd=_usd(purchase.charges_total_usd),
        total_usd=_usd(purchase.total_usd),
        created_by=user_ref(users.get(purchase.created_by)),
        created_at=purchase.created_at,
        updated_at=purchase.updated_at,
        confirmed_by=user_ref(users.get(purchase.confirmed_by)) if purchase.confirmed_by else None,
        confirmed_at=purchase.confirmed_at,
        void=PurchaseVoidOut(
            reason=void.reason,
            voided_by=user_ref(users.get(void.voided_by)),
            voided_at=void.voided_at,
        )
        if void
        else None,
        warnings=[PurchaseWarning(**warning) for warning in warnings or []],
    )


def cost_changes_out(changes: list[CostChange]) -> list[CostChangeOut]:
    return [
        CostChangeOut(
            product_id=change.product_id,
            sku=change.sku,
            cost_before_usd=cost_str(change.cost_before_usd),
            cost_after_usd=cost_str(change.cost_after_usd),
        )
        for change in changes
    ]


def summaries_out(db: Session, purchases: list[Purchase]) -> list[PurchaseSummary]:
    suppliers = {
        s.id: s
        for s in db.scalars(
            select(Supplier).where(Supplier.id.in_({p.supplier_id for p in purchases}))
        )
    }
    counts = purchases_service.item_counts(db, [p.id for p in purchases])
    return [
        PurchaseSummary(
            id=p.id,
            number=p.number,
            status=p.status,
            purchase_date=p.purchase_date,
            supplier=supplier_ref(suppliers[p.supplier_id]),
            supplier_invoice_number=p.supplier_invoice_number,
            currency=p.currency,
            total_usd=_usd(p.total_usd),
            items_count=counts.get(p.id, 0),
            created_at=p.created_at,
        )
        for p in purchases
    ]
