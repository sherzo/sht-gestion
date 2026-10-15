"""Modelos de la base de datos.

- Usuarios, sesiones y auditoría (RF-44 a RF-46): specs/001-usuarios-autenticacion-permisos/
  data-model.md y docs/modelo-de-datos.md §3.1; los crea la migración 0002.
- Productos, categorías e inventario (RF-01 a RF-12): specs/002-productos-inventario/
  data-model.md y docs/modelo-de-datos.md §3.2 y §3.3; los crea la migración 0004, que
  además impone con triggers el kardex y la inmutabilidad.
- Proveedores, compras y tasa BCV (RF-13 a RF-17): specs/003-proveedores-compras/
  data-model.md y docs/modelo-de-datos.md §3.4 y §3.5; los crea la migración 0005. Las
  reglas (`CHECK` y triggers) viven en la migración.
- Equipos, caja, ventas, pagos y descuentos (RF-18, RF-20 a RF-30):
  specs/004-ventas-multimoneda/data-model.md y docs/modelo-de-datos.md §3.1 y §3.6 a
  §3.8; los crea la migración 0006, con sus reglas.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

USERNAME_PATTERN = r"^[a-z0-9._-]{3,30}$"
ACTION_PATTERN = r"^[a-z_]+\.[a-z_]+$"
REVOKED_REASONS = (
    "logout",
    "password_changed",
    "password_reset",
    "user_deactivated",
    "token_reuse",
    "too_many_attempts",
)


def _uuid7() -> uuid.UUID:
    return uuid.uuid7()


def _in_list(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class AppUser(Base):
    """Usuario del sistema; nunca se borra (FR-016). `user` es palabra reservada."""

    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint(f"username ~ '{USERNAME_PATTERN}'", name="username_format"),
        CheckConstraint(
            "char_length(full_name) BETWEEN 1 AND 100 AND full_name = btrim(full_name)",
            name="full_name_length",
        ),
        CheckConstraint(_in_list("role", ("admin", "seller", "warehouse")), name="role_valid"),
        CheckConstraint("pin_hash IS NULL OR role = 'admin'", name="pin_only_admin"),
        CheckConstraint("pin_failed_attempts >= 0", name="pin_failed_attempts_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    username: Mapped[str] = mapped_column(Text, unique=True)
    full_name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    pin_hash: Mapped[str | None] = mapped_column(Text)
    pin_failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    pin_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserSession(Base):
    """Jornada de trabajo: vence 12 horas después de ingresar la contraseña (FR-005)."""

    __tablename__ = "user_session"
    __table_args__ = (
        CheckConstraint("expires_at > started_at", name="expires_after_start"),
        CheckConstraint(
            f"revoked_reason IS NULL OR {_in_list('revoked_reason', REVOKED_REASONS)}",
            name="revoked_reason_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"), index=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("device.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RefreshToken(Base):
    """Token de renovación rotativo; solo se guarda su hash (research R4)."""

    __tablename__ = "refresh_token"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("user_session.id"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("refresh_token.id"))


class AuditLog(Base):
    """Registro de auditoría de solo inserción (RF-46). Un trigger impide modificarlo."""

    __tablename__ = "audit_log"
    __table_args__ = (CheckConstraint(f"action ~ '{ACTION_PATTERN}'", name="action_format"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("device.id"))
    action: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


# --- Productos, categorías e inventario (etapa 1.1b) ---------------------------------

# Escalas de los dominios de ADR-0004 (migración 0001).
UsdAmount = Numeric(14, 2)
UsdCost = Numeric(18, 6)
Quantity = Numeric(14, 2)

MOVEMENT_TYPES = ("purchase", "sale", "sale_void", "purchase_void", "adjustment")
ADJUSTMENT_REASONS = ("physical_count", "damage", "loss", "correction")
ATTRIBUTE_TYPES = ("text", "number", "option")
REQUEST_STATUSES = ("pending", "approved", "rejected", "withdrawn")
COUNT_STATUSES = ("open", "ready_for_review", "applied", "cancelled")
SKU_PREFIX_PATTERN = r"^[A-Z]{3}$"
ATTRIBUTE_KEY_PATTERN = r"^[a-z][a-z0-9_]{1,39}$"


class Unit(Base):
    """Unidad de medida (RF-05/FR-031): `metro` con 2 decimales, `unidad` con 0."""

    __tablename__ = "unit"
    __table_args__ = (
        CheckConstraint(
            "char_length(code) BETWEEN 1 AND 10 AND code = lower(code)", name="code_format"
        ),
        CheckConstraint("char_length(name) BETWEEN 1 AND 40", name="name_length"),
        CheckConstraint("decimals IN (0, 2)", name="decimals_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    decimals: Mapped[int] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))


class Category(Base):
    """Categoría con prefijo de SKU y correlativo propio (RF-02, RF-03/FR-029, R1)."""

    __tablename__ = "category"
    __table_args__ = (
        CheckConstraint(f"sku_prefix ~ '{SKU_PREFIX_PATTERN}'", name="sku_prefix_format"),
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 60 AND name = btrim(name)", name="name_length"
        ),
        CheckConstraint("next_sku_number >= 1", name="next_sku_number_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    name: Mapped[str] = mapped_column(Text)
    sku_prefix: Mapped[str] = mapped_column(Text, unique=True)
    next_sku_number: Mapped[int] = mapped_column(Integer, default=1)
    default_unit_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("unit.id"))
    unit_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AttributeDefinition(Base):
    """Atributo que tienen los productos de una categoría (RF-04/FR-030, R5)."""

    __tablename__ = "attribute_definition"
    __table_args__ = (
        UniqueConstraint("category_id", "key"),
        CheckConstraint(f"key ~ '{ATTRIBUTE_KEY_PATTERN}'", name="key_format"),
        CheckConstraint(
            "char_length(label) BETWEEN 1 AND 60 AND label = btrim(label)", name="label_length"
        ),
        CheckConstraint(_in_list("data_type", ATTRIBUTE_TYPES), name="data_type_valid"),
        CheckConstraint(
            "(data_type = 'option') = (options IS NOT NULL)", name="options_only_for_option"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    category_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("category.id"))
    key: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(Text)
    # Lista de {"value": texto, "is_active": bool}; las opciones nunca se borran.
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_filterable: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    """Producto que se compra y se vende individualmente (RF-01/FR-001); nunca se borra.

    `stock` y `has_movements` solo los cambia el trigger de `stock_movement` (RN-08, R2).
    """

    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 120 AND name = btrim(name)", name="name_length"
        ),
        CheckConstraint("char_length(description) <= 2000", name="description_length"),
        CheckConstraint("sale_price_usd IS NULL OR sale_price_usd > 0", name="sale_price_positive"),
        CheckConstraint("avg_cost_usd IS NULL OR avg_cost_usd >= 0", name="avg_cost_positive"),
        CheckConstraint("min_stock >= 0", name="min_stock_positive"),
        CheckConstraint(
            "NOT is_published OR (is_active AND sale_price_usd IS NOT NULL)", name="publishable"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    sku: Mapped[str] = mapped_column(Text, unique=True)
    category_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("category.id"))
    unit_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("unit.id"))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    search_text: Mapped[str] = mapped_column(Text)
    sale_price_usd: Mapped[Decimal | None] = mapped_column(UsdAmount)
    avg_cost_usd: Mapped[Decimal | None] = mapped_column(UsdCost)
    cost_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    stock: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("0"))
    min_stock: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("0"))
    has_movements: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))


class ProductPrice(Base):
    """Historial de precios de venta, de solo inserción (FR-012). Previsión RN-18: las
    listas de precios agregarían aquí `price_list_id` nulo (nulo = precio general)."""

    __tablename__ = "product_price"
    __table_args__ = (CheckConstraint("price_usd > 0", name="price_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("product.id"))
    price_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    set_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))


class ProductPhoto(Base):
    """Foto de un producto (FR-008); quitarla la marca y borra el objeto de Storage."""

    __tablename__ = "product_photo"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("product.id"))
    storage_path: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(SmallInteger)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))


class StockMovement(Base):
    """Movimiento del kardex, inmutable (RF-08, RF-09/FR-016, FR-017; RN-08)."""

    __tablename__ = "stock_movement"
    __table_args__ = (
        CheckConstraint(_in_list("type", MOVEMENT_TYPES), name="type_valid"),
        CheckConstraint("quantity_delta <> 0", name="quantity_not_zero"),
        CheckConstraint(
            "(type = 'adjustment') = (adjustment_reason IS NOT NULL)",
            name="adjustment_reason_required",
        ),
        CheckConstraint(
            f"adjustment_reason IS NULL OR {_in_list('adjustment_reason', ADJUSTMENT_REASONS)}",
            name="adjustment_reason_valid",
        ),
        CheckConstraint("note IS NULL OR char_length(note) <= 500", name="note_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("product.id"))
    type: Mapped[str] = mapped_column(Text)
    quantity_delta: Mapped[Decimal] = mapped_column(Quantity)
    balance_after: Mapped[Decimal] = mapped_column(Quantity)
    adjustment_reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    cost_before_usd: Mapped[Decimal | None] = mapped_column(UsdCost)
    cost_after_usd: Mapped[Decimal | None] = mapped_column(UsdCost)
    reference_type: Mapped[str | None] = mapped_column(Text)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("device.id"))


class AdjustmentRequest(Base):
    """Salida de inventario del Almacén que espera la decisión del Admin (FR-019a, RN-19)."""

    __tablename__ = "adjustment_request"
    __table_args__ = (
        CheckConstraint("quantity_delta < 0", name="quantity_negative"),
        CheckConstraint(
            _in_list("adjustment_reason", ADJUSTMENT_REASONS), name="adjustment_reason_valid"
        ),
        CheckConstraint("note IS NULL OR char_length(note) <= 500", name="note_length"),
        CheckConstraint(_in_list("status", REQUEST_STATUSES), name="status_valid"),
        CheckConstraint(
            "(status = 'pending') = (decided_at IS NULL AND decided_by IS NULL)",
            name="decision_when_final",
        ),
        CheckConstraint(
            "status <> 'rejected' OR rejection_reason IS NOT NULL", name="rejection_reason"
        ),
        CheckConstraint(
            "(status = 'approved') = (stock_movement_id IS NOT NULL)",
            name="movement_when_approved",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("product.id"))
    quantity_delta: Mapped[Decimal] = mapped_column(Quantity)
    adjustment_reason: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending")
    requested_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    stock_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("stock_movement.id")
    )


class StockCount(Base):
    """Conteo físico: el Almacén anota a ciegas y solo el Admin lo aplica (RF-12, RN-19)."""

    __tablename__ = "stock_count"
    __table_args__ = (
        CheckConstraint(_in_list("status", COUNT_STATUSES), name="status_valid"),
        CheckConstraint("status <> 'cancelled' OR cancel_reason IS NOT NULL", name="cancel_reason"),
        CheckConstraint(
            "(status IN ('applied', 'cancelled')) = "
            "(closed_at IS NOT NULL AND closed_by IS NOT NULL)",
            name="closed_when_final",
        ),
        CheckConstraint("notes IS NULL OR char_length(notes) <= 500", name="notes_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    status: Mapped[str] = mapped_column(Text, default="open")
    # {"type": "all"} | {"type": "categories", "ids": [...]} | {"type": "products", "ids": [...]}
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    started_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ready_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)


class StockCountLine(Base):
    """Línea de un conteo; guarda el stock del sistema al anotar (FR-025)."""

    __tablename__ = "stock_count_line"
    __table_args__ = (
        UniqueConstraint("stock_count_id", "product_id"),
        CheckConstraint(
            "counted_quantity IS NULL OR counted_quantity >= 0", name="counted_positive"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    stock_count_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("stock_count.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("product.id"))
    counted_quantity: Mapped[Decimal | None] = mapped_column(Quantity)
    expected_quantity: Mapped[Decimal | None] = mapped_column(Quantity)
    counted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stock_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("stock_movement.id")
    )
    # Se apaga al aplicar o cancelar el conteo; el índice único parcial sobre las líneas
    # abiertas impide que un producto esté en dos conteos a la vez (FR-024).
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)


# --- Proveedores, compras y tasa BCV (etapa 1.2) --------------------------------------
# specs/003-proveedores-compras/data-model.md; migración 0005, que impone con triggers la
# inmutabilidad de las compras confirmadas (RN-14, research R2).

VesAmount = Numeric(16, 2)
Rate = Numeric(18, 8)
Percent = Numeric(5, 2)
PURCHASE_STATUSES = ("draft", "confirmed", "voided")
CURRENCIES = ("USD", "VES")
CHARGE_TYPES = ("percent", "fixed")


class Supplier(Base):
    """Proveedor (RF-13/FR-001); nunca se borra."""

    __tablename__ = "supplier"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    name: Mapped[str] = mapped_column(Text)
    rif: Mapped[str | None] = mapped_column(Text, unique=True)
    phone: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExchangeRate(Base):
    """Tasa BCV de una fecha (RF-17, RN-03, RN-15); se corrige, nunca se borra."""

    __tablename__ = "exchange_rate"
    __table_args__ = (UniqueConstraint("rate_type", "business_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    rate_type: Mapped[str] = mapped_column(Text, default="BCV")
    business_date: Mapped[date] = mapped_column(Date)
    rate: Mapped[Decimal] = mapped_column(Rate)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ChargeTemplate(Base):
    """Gasto frecuente que el Admin mantiene para las compras (RF-14/FR-032)."""

    __tablename__ = "charge_template"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    name: Mapped[str] = mapped_column(Text)
    charge_type: Mapped[str] = mapped_column(Text)
    default_value: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    currency: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Purchase(Base):
    """Compra a un proveedor (RF-14 a RF-16); inmutable una vez confirmada (RN-14)."""

    __tablename__ = "purchase"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    number: Mapped[str | None] = mapped_column(Text, unique=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("supplier.id"))
    purchase_date: Mapped[date] = mapped_column(Date)
    supplier_invoice_number: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(Text)
    exchange_rate: Mapped[Decimal | None] = mapped_column(Rate)
    exchange_rate_date: Mapped[date | None] = mapped_column(Date)
    merchandise_total_usd: Mapped[Decimal] = mapped_column(UsdAmount, default=Decimal("0"))
    merchandise_total_ves: Mapped[Decimal | None] = mapped_column(VesAmount)
    charges_total_usd: Mapped[Decimal] = mapped_column(UsdAmount, default=Decimal("0"))
    total_usd: Mapped[Decimal] = mapped_column(UsdAmount, default=Decimal("0"))
    status: Mapped[str] = mapped_column(Text, default="draft")
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PurchaseItem(Base):
    """Línea de una compra con su costo final por unidad (FR-004, FR-031; RN-20)."""

    __tablename__ = "purchase_item"
    __table_args__ = (UniqueConstraint("purchase_id", "product_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    purchase_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("purchase.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("product.id"))
    line_number: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[Decimal] = mapped_column(Quantity)
    unit_cost_ves: Mapped[Decimal | None] = mapped_column(VesAmount)
    unit_cost_usd: Mapped[Decimal] = mapped_column(UsdCost)
    line_total_ves: Mapped[Decimal | None] = mapped_column(VesAmount)
    line_total_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    allocated_charges_usd: Mapped[Decimal] = mapped_column(UsdAmount, default=Decimal("0"))
    landed_unit_cost_usd: Mapped[Decimal] = mapped_column(UsdCost)


class PurchaseCharge(Base):
    """Gasto de una compra: porcentaje de la factura o monto fijo (RN-20/FR-029)."""

    __tablename__ = "purchase_charge"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    purchase_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("purchase.id"))
    line_number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    charge_type: Mapped[str] = mapped_column(Text)
    percent: Mapped[Decimal | None] = mapped_column(Percent)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    currency: Mapped[str | None] = mapped_column(Text)
    amount_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    allocation_method: Mapped[str] = mapped_column(Text, default="value")
    charge_template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("charge_template.id")
    )


class PurchaseVoid(Base):
    """Anulación de una compra confirmada, de solo inserción (RN-14/FR-017)."""

    __tablename__ = "purchase_void"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    purchase_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("purchase.id"), unique=True)
    reason: Mapped[str] = mapped_column(Text)
    voided_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    voided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Alert(Base):
    """Aviso para el Admin (RN-14, research R8); solo se marca como revisado."""

    __tablename__ = "alert"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    type: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))


class SequenceCounter(Base):
    """Correlativo sin huecos de documentos del servidor, como las compras (FR-008, R3)."""

    __tablename__ = "sequence_counter"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    next_number: Mapped[int] = mapped_column(BigInteger)


# --- Ventas, pagos, descuentos y apertura de caja (etapa 1.3) -------------------------
# specs/004-ventas-multimoneda/data-model.md; migración 0006, que impone los CHECK, la
# caja abierta única por equipo y la inmutabilidad de ventas, pagos y anulaciones
# (RN-12, research R9). Las tablas con "id del equipo" reciben el UUIDv7 generado en el
# navegador (ADR-0003).

SALE_ALERT_TYPES = (
    "negative_stock",
    "price_mismatch",
    "total_mismatch",
    "rate_mismatch",
    "discount_review",
    "inactive_user_sync",
    "revoked_device_sync",
)
PAYMENT_KINDS = ("sale_payment", "change", "void_refund", "void_change")
AUTHORIZATION_METHODS = ("pin", "request", "admin_self")
OPERATION_TYPES = ("cash_session.open", "sale.create")


class Device(Base):
    """Equipo de mostrador con su serie de numeración (FR-001 a FR-004; RN-11, R3)."""

    __tablename__ = "device"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    name: Mapped[str] = mapped_column(Text)
    series: Mapped[str] = mapped_column(Text, unique=True)
    last_sequence_number: Mapped[int] = mapped_column(Integer, default=0)
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    registered_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))


class OutboxOperation(Base):
    """Operación del mostrador recibida por la cola (ADR-0003, R4): su id es la clave de
    idempotencia y la fila guarda la respuesta para repetirla en un reenvío."""

    __tablename__ = "outbox_operation"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("device.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    operation_type: Mapped[str] = mapped_column(Text)
    schema_version: Mapped[int] = mapped_column(SmallInteger)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at_device: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text)
    http_status: Mapped[int] = mapped_column(SmallInteger)
    # SQL NULL (no `null` de JSON) cuando no aplica: el CHECK de la migración lo exige.
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))


class CashSession(Base):
    """Caja abierta en un equipo con su fondo inicial (RF-29, RF-30, RN-16; R7). El cierre
    llega en la etapa 1.4."""

    __tablename__ = "cash_session"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("device.id"))
    business_date: Mapped[date] = mapped_column(Date)
    opened_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    opening_float_ves: Mapped[Decimal] = mapped_column(VesAmount)
    opening_float_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    status: Mapped[str] = mapped_column(Text, default="open")
    outbox_operation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("outbox_operation.id"), unique=True
    )


class Customer(Base):
    """Cliente opcional de una venta (RF-28/FR-019, R11); no se borra."""

    __tablename__ = "customer"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    document_id: Mapped[str | None] = mapped_column(Text, unique=True)
    phone: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))


class PaymentMethod(Base):
    """Método de pago del catálogo fijo de RF-24; la clave es su código."""

    __tablename__ = "payment_method"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(Text)
    requires_reference: Mapped[bool] = mapped_column(Boolean)
    is_cash: Mapped[bool] = mapped_column(Boolean)
    sort_order: Mapped[int] = mapped_column(SmallInteger)


class DiscountAuthorization(Base):
    """Autorización de un descuento del Vendedor por PIN o por solicitud (RN-07; R8)."""

    __tablename__ = "discount_authorization"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    sale_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    sale_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    product_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("product.id"))
    discount_type: Mapped[str] = mapped_column(Text)
    requested_value: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount_value: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    base_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    discount_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    method: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("device.id"))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("app_user.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)


class Sale(Base):
    """Venta del mostrador, de solo inserción (RF-26; RN-05, RN-11, RN-12)."""

    __tablename__ = "sale"
    __table_args__ = (UniqueConstraint("series", "sequence_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("device.id"))
    series: Mapped[str] = mapped_column(Text)
    sequence_number: Mapped[int] = mapped_column(Integer)
    number: Mapped[str] = mapped_column(Text, unique=True)
    cash_session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cash_session.id"))
    seller_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    customer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("customer.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    business_date: Mapped[date] = mapped_column(Date)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exchange_rate: Mapped[Decimal] = mapped_column(Rate)
    exchange_rate_date: Mapped[date] = mapped_column(Date)
    subtotal_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    discount_type: Mapped[str | None] = mapped_column(Text)
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    discount_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    discount_authorized_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id")
    )
    discount_authorization_method: Mapped[str | None] = mapped_column(Text)
    discount_authorization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("discount_authorization.id"), unique=True
    )
    total_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    total_ves: Mapped[Decimal] = mapped_column(VesAmount)
    paid_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    change_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    device_total_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    outbox_operation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("outbox_operation.id"), unique=True
    )


class SaleItem(Base):
    """Línea de una venta: un producto individual con su precio y descuentos (RN-13)."""

    __tablename__ = "sale_item"
    __table_args__ = (UniqueConstraint("sale_id", "line_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    sale_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sale.id"))
    line_number: Mapped[int] = mapped_column(SmallInteger)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("product.id"))
    quantity: Mapped[Decimal] = mapped_column(Quantity)
    entered_unit: Mapped[str] = mapped_column(Text)
    unit_price_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    server_price_usd: Mapped[Decimal | None] = mapped_column(UsdAmount)
    line_subtotal_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    item_discount_type: Mapped[str | None] = mapped_column(Text)
    item_discount_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    item_discount_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    item_discount_authorized_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id")
    )
    item_discount_authorization_method: Mapped[str | None] = mapped_column(Text)
    item_discount_authorization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("discount_authorization.id"), unique=True
    )
    allocated_sale_discount_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    line_total_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    unit_cost_usd: Mapped[Decimal | None] = mapped_column(UsdCost)


class SaleVoid(Base):
    """Anulación de una venta, de solo inserción (RF-27/FR-041; R10)."""

    __tablename__ = "sale_void"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    sale_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sale.id"), unique=True)
    reason: Mapped[str] = mapped_column(Text)
    voided_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("app_user.id"))
    voided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Payment(Base):
    """Dinero que entra o sale por una venta: pago, vuelto o su reverso al anular
    (RF-23 a RF-25, RN-04 a RN-06; R10). De solo inserción."""

    __tablename__ = "payment"
    __table_args__ = (UniqueConstraint("sale_id", "kind", "line_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid7)
    sale_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sale.id"))
    line_number: Mapped[int] = mapped_column(SmallInteger)
    cash_session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cash_session.id"))
    kind: Mapped[str] = mapped_column(Text)
    payment_method_code: Mapped[str] = mapped_column(Text, ForeignKey("payment_method.code"))
    currency: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    exchange_rate: Mapped[Decimal] = mapped_column(Rate)
    amount_usd: Mapped[Decimal] = mapped_column(UsdAmount)
    reference: Mapped[str | None] = mapped_column(Text)
    sale_void_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("sale_void.id"))
