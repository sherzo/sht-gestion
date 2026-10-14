"""Productos, categorías, unidades, kardex, ajustes y conteos (RF-01 a RF-12, RN-08, RN-19).

Tablas de specs/002-productos-inventario/data-model.md. La base impone las reglas que no
pueden depender solo del código (principio II, research R2, R7 y R8):

- El stock solo cambia al insertar un `stock_movement`: un trigger verifica el saldo y
  actualiza `product.stock`, y otro rechaza escribir `stock` o `has_movements` desde
  fuera de ese trigger.
- `stock_movement` y `product_price` son de solo inserción.
- El prefijo de una categoría no cambia si tiene productos.
- Una solicitud de ajuste solo pasa de `pending` a un estado final.
- Un conteo aplicado o cancelado no cambia; sus líneas se anotan solo con el conteo
  abierto y se cierran solo al aplicarlo o cancelarlo.

Incluye los datos iniciales de FR-028 (research R5 y R12) con UUIDv7 fijos.

Revisión: 0004
Anterior: 0003
Fecha: 2026-10-13
"""

import json
from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = """
CREATE TABLE unit (
    id uuid PRIMARY KEY,
    code text NOT NULL,
    name text NOT NULL,
    decimals smallint NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES app_user (id),
    CONSTRAINT uq_unit_code UNIQUE (code),
    CONSTRAINT uq_unit_name UNIQUE (name),
    CONSTRAINT ck_unit_code_format
        CHECK (char_length(code) BETWEEN 1 AND 10 AND code = lower(code)),
    CONSTRAINT ck_unit_name_length CHECK (char_length(name) BETWEEN 1 AND 40),
    CONSTRAINT ck_unit_decimals_valid CHECK (decimals IN (0, 2))
);

CREATE TABLE category (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    sku_prefix text NOT NULL,
    next_sku_number integer NOT NULL DEFAULT 1,
    default_unit_id uuid NOT NULL REFERENCES unit (id),
    unit_locked boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES app_user (id),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_category_sku_prefix UNIQUE (sku_prefix),
    CONSTRAINT ck_category_sku_prefix_format CHECK (sku_prefix ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_category_name_length
        CHECK (char_length(name) BETWEEN 1 AND 60 AND name = btrim(name)),
    CONSTRAINT ck_category_next_sku_number_positive CHECK (next_sku_number >= 1)
);
CREATE UNIQUE INDEX ux_category_active_name ON category (lower(name)) WHERE is_active;

CREATE TABLE attribute_definition (
    id uuid PRIMARY KEY,
    category_id uuid NOT NULL REFERENCES category (id),
    key text NOT NULL,
    label text NOT NULL,
    data_type text NOT NULL,
    options jsonb,
    is_required boolean NOT NULL DEFAULT false,
    is_filterable boolean NOT NULL DEFAULT false,
    sort_order smallint NOT NULL DEFAULT 0,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES app_user (id),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_attribute_definition_category_id_key UNIQUE (category_id, key),
    CONSTRAINT ck_attribute_definition_key_format CHECK (key ~ '^[a-z][a-z0-9_]{1,39}$'),
    CONSTRAINT ck_attribute_definition_label_length
        CHECK (char_length(label) BETWEEN 1 AND 60 AND label = btrim(label)),
    CONSTRAINT ck_attribute_definition_data_type_valid
        CHECK (data_type IN ('text', 'number', 'option')),
    CONSTRAINT ck_attribute_definition_options_only_for_option
        CHECK ((data_type = 'option') = (options IS NOT NULL))
);

CREATE TABLE product (
    id uuid PRIMARY KEY,
    sku text NOT NULL,
    category_id uuid NOT NULL REFERENCES category (id),
    unit_id uuid NOT NULL REFERENCES unit (id),
    name text NOT NULL,
    description text NOT NULL DEFAULT '',
    attributes jsonb NOT NULL DEFAULT '{}',
    search_text text NOT NULL,
    sale_price_usd usd_amount,
    avg_cost_usd usd_cost,
    cost_locked boolean NOT NULL DEFAULT false,
    stock quantity NOT NULL DEFAULT 0,
    min_stock quantity NOT NULL DEFAULT 0,
    has_movements boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,
    is_published boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES app_user (id),
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid REFERENCES app_user (id),
    CONSTRAINT uq_product_sku UNIQUE (sku),
    CONSTRAINT ck_product_name_length
        CHECK (char_length(name) BETWEEN 1 AND 120 AND name = btrim(name)),
    CONSTRAINT ck_product_description_length CHECK (char_length(description) <= 2000),
    CONSTRAINT ck_product_sale_price_positive CHECK (sale_price_usd IS NULL OR sale_price_usd > 0),
    CONSTRAINT ck_product_avg_cost_positive CHECK (avg_cost_usd IS NULL OR avg_cost_usd >= 0),
    CONSTRAINT ck_product_min_stock_positive CHECK (min_stock >= 0),
    CONSTRAINT ck_product_publishable
        CHECK (NOT is_published OR (is_active AND sale_price_usd IS NOT NULL))
);
CREATE INDEX ix_product_category_id_is_active ON product (category_id, is_active);
CREATE INDEX ix_product_is_active_stock ON product (is_active, stock);

CREATE TABLE product_price (
    id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES product (id),
    price_usd usd_amount NOT NULL,
    valid_from timestamptz NOT NULL,
    set_by uuid NOT NULL REFERENCES app_user (id),
    CONSTRAINT ck_product_price_price_positive CHECK (price_usd > 0)
);
CREATE INDEX ix_product_price_product_id_valid_from ON product_price (product_id, valid_from DESC);

CREATE TABLE product_photo (
    id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES product (id),
    storage_path text NOT NULL,
    width integer NOT NULL,
    height integer NOT NULL,
    size_bytes integer NOT NULL,
    sort_order smallint NOT NULL,
    removed_at timestamptz,
    removed_by uuid REFERENCES app_user (id),
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES app_user (id)
);
CREATE INDEX ix_product_photo_product_id ON product_photo (product_id) WHERE removed_at IS NULL;

CREATE TABLE stock_movement (
    id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES product (id),
    type text NOT NULL,
    quantity_delta quantity NOT NULL,
    balance_after quantity NOT NULL,
    adjustment_reason text,
    note text,
    cost_before_usd usd_cost,
    cost_after_usd usd_cost,
    reference_type text,
    reference_id uuid,
    occurred_at timestamptz NOT NULL,
    created_by uuid REFERENCES app_user (id),
    device_id uuid,
    CONSTRAINT ck_stock_movement_type_valid
        CHECK (type IN ('purchase', 'sale', 'sale_void', 'purchase_void', 'adjustment')),
    CONSTRAINT ck_stock_movement_quantity_not_zero CHECK (quantity_delta <> 0),
    CONSTRAINT ck_stock_movement_adjustment_reason_required
        CHECK ((type = 'adjustment') = (adjustment_reason IS NOT NULL)),
    CONSTRAINT ck_stock_movement_adjustment_reason_valid
        CHECK (adjustment_reason IS NULL OR adjustment_reason IN
            ('physical_count', 'damage', 'loss', 'correction')),
    CONSTRAINT ck_stock_movement_note_length CHECK (note IS NULL OR char_length(note) <= 500)
);
CREATE INDEX ix_stock_movement_product_id_occurred_at
    ON stock_movement (product_id, occurred_at DESC);

CREATE TABLE adjustment_request (
    id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES product (id),
    quantity_delta quantity NOT NULL,
    adjustment_reason text NOT NULL,
    note text,
    status text NOT NULL DEFAULT 'pending',
    requested_by uuid NOT NULL REFERENCES app_user (id),
    requested_at timestamptz NOT NULL,
    decided_by uuid REFERENCES app_user (id),
    decided_at timestamptz,
    rejection_reason text,
    stock_movement_id uuid REFERENCES stock_movement (id),
    CONSTRAINT ck_adjustment_request_quantity_negative CHECK (quantity_delta < 0),
    CONSTRAINT ck_adjustment_request_adjustment_reason_valid
        CHECK (adjustment_reason IN ('physical_count', 'damage', 'loss', 'correction')),
    CONSTRAINT ck_adjustment_request_note_length
        CHECK (note IS NULL OR char_length(note) <= 500),
    CONSTRAINT ck_adjustment_request_status_valid
        CHECK (status IN ('pending', 'approved', 'rejected', 'withdrawn')),
    CONSTRAINT ck_adjustment_request_decision_when_final
        CHECK ((status = 'pending') = (decided_at IS NULL AND decided_by IS NULL)),
    CONSTRAINT ck_adjustment_request_rejection_reason
        CHECK (status <> 'rejected' OR rejection_reason IS NOT NULL),
    CONSTRAINT ck_adjustment_request_movement_when_approved
        CHECK ((status = 'approved') = (stock_movement_id IS NOT NULL))
);
CREATE INDEX ix_adjustment_request_status_requested_at
    ON adjustment_request (status, requested_at);

CREATE TABLE stock_count (
    id uuid PRIMARY KEY,
    status text NOT NULL DEFAULT 'open',
    scope jsonb NOT NULL,
    notes text,
    started_by uuid NOT NULL REFERENCES app_user (id),
    started_at timestamptz NOT NULL,
    ready_by uuid REFERENCES app_user (id),
    ready_at timestamptz,
    closed_by uuid REFERENCES app_user (id),
    closed_at timestamptz,
    cancel_reason text,
    CONSTRAINT ck_stock_count_status_valid
        CHECK (status IN ('open', 'ready_for_review', 'applied', 'cancelled')),
    CONSTRAINT ck_stock_count_cancel_reason
        CHECK (status <> 'cancelled' OR cancel_reason IS NOT NULL),
    CONSTRAINT ck_stock_count_closed_when_final
        CHECK ((status IN ('applied', 'cancelled')) =
            (closed_at IS NOT NULL AND closed_by IS NOT NULL)),
    CONSTRAINT ck_stock_count_notes_length CHECK (notes IS NULL OR char_length(notes) <= 500)
);
CREATE INDEX ix_stock_count_status ON stock_count (status);

CREATE TABLE stock_count_line (
    id uuid PRIMARY KEY,
    stock_count_id uuid NOT NULL REFERENCES stock_count (id),
    product_id uuid NOT NULL REFERENCES product (id),
    counted_quantity quantity,
    expected_quantity quantity,
    counted_by uuid REFERENCES app_user (id),
    counted_at timestamptz,
    stock_movement_id uuid REFERENCES stock_movement (id),
    is_open boolean NOT NULL DEFAULT true,
    CONSTRAINT uq_stock_count_line_stock_count_id_product_id UNIQUE (stock_count_id, product_id),
    CONSTRAINT ck_stock_count_line_counted_positive
        CHECK (counted_quantity IS NULL OR counted_quantity >= 0)
);
-- Un producto no puede estar en dos conteos abiertos a la vez (FR-024).
CREATE UNIQUE INDEX ux_stock_count_line_open_product ON stock_count_line (product_id)
    WHERE is_open;
"""

TRIGGERS = """
-- Kardex (R2): el movimiento verifica el saldo y actualiza el stock en la misma operación.
CREATE FUNCTION stock_movement_apply() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    current_stock numeric;
BEGIN
    SELECT stock INTO current_stock FROM product WHERE id = NEW.product_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'El producto % no existe', NEW.product_id;
    END IF;
    IF NEW.balance_after <> current_stock + NEW.quantity_delta THEN
        RAISE EXCEPTION 'Saldo incorrecto: el stock es % y el movimiento es %',
            current_stock, NEW.quantity_delta;
    END IF;
    UPDATE product SET stock = NEW.balance_after, has_movements = true
        WHERE id = NEW.product_id;
    RETURN NEW;
END;
$$;
CREATE TRIGGER stock_movement_apply BEFORE INSERT ON stock_movement
    FOR EACH ROW EXECUTE FUNCTION stock_movement_apply();

CREATE FUNCTION reject_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% es de solo inserción: no se modifica ni se borra', TG_TABLE_NAME;
END;
$$;
CREATE TRIGGER stock_movement_immutable BEFORE UPDATE OR DELETE ON stock_movement
    FOR EACH ROW EXECUTE FUNCTION reject_change();
CREATE TRIGGER product_price_immutable BEFORE UPDATE OR DELETE ON product_price
    FOR EACH ROW EXECUTE FUNCTION reject_change();

-- Nadie escribe el stock directamente (RN-08): solo el trigger del kardex, que corre en
-- un nivel de anidamiento mayor.
CREATE FUNCTION product_stock_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.stock IS DISTINCT FROM OLD.stock
        OR NEW.has_movements IS DISTINCT FROM OLD.has_movements)
        AND pg_trigger_depth() <= 1 THEN
        RAISE EXCEPTION 'El stock solo cambia mediante movimientos de inventario';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER product_stock_guard BEFORE UPDATE ON product
    FOR EACH ROW EXECUTE FUNCTION product_stock_guard();

-- El prefijo de una categoría con productos no cambia (FR-029).
CREATE FUNCTION category_prefix_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.sku_prefix <> OLD.sku_prefix
        AND EXISTS (SELECT 1 FROM product WHERE category_id = OLD.id) THEN
        RAISE EXCEPTION 'El prefijo de una categoría con productos no cambia';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER category_prefix_guard BEFORE UPDATE ON category
    FOR EACH ROW EXECUTE FUNCTION category_prefix_guard();

-- Solicitudes de ajuste (R7): solo de pendiente a un estado final, sin tocar la solicitud.
CREATE FUNCTION adjustment_request_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Las solicitudes de ajuste no se borran';
    END IF;
    IF OLD.status <> 'pending' OR NEW.status = 'pending' THEN
        RAISE EXCEPTION 'Una solicitud solo pasa de pendiente a un estado final';
    END IF;
    IF NEW.product_id <> OLD.product_id
        OR NEW.quantity_delta <> OLD.quantity_delta
        OR NEW.adjustment_reason <> OLD.adjustment_reason
        OR NEW.note IS DISTINCT FROM OLD.note
        OR NEW.requested_by <> OLD.requested_by
        OR NEW.requested_at <> OLD.requested_at THEN
        RAISE EXCEPTION 'Una solicitud de ajuste no se edita';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER adjustment_request_guard BEFORE UPDATE OR DELETE ON adjustment_request
    FOR EACH ROW EXECUTE FUNCTION adjustment_request_guard();

-- Conteos (R8): cerrados no cambian.
CREATE FUNCTION stock_count_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' OR OLD.status IN ('applied', 'cancelled') THEN
        RAISE EXCEPTION 'Un conteo aplicado o cancelado no se modifica';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER stock_count_guard BEFORE UPDATE OR DELETE ON stock_count
    FOR EACH ROW EXECUTE FUNCTION stock_count_guard();

-- Líneas (R8): se anotan solo con el conteo abierto; se cierran (is_open a false y el
-- movimiento generado) con el conteo abierto o listo para revisión, que es cuando se
-- aplica o cancela; con el conteo cerrado no cambian.
CREATE FUNCTION stock_count_line_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    count_status text;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Las líneas de un conteo no se borran';
    END IF;
    SELECT status INTO count_status FROM stock_count WHERE id = NEW.stock_count_id;
    IF TG_OP = 'INSERT' THEN
        IF count_status <> 'open' THEN
            RAISE EXCEPTION 'Solo se agregan líneas a un conteo abierto';
        END IF;
        RETURN NEW;
    END IF;
    IF count_status IN ('applied', 'cancelled') THEN
        RAISE EXCEPTION 'Un conteo aplicado o cancelado no se modifica';
    END IF;
    IF NEW.stock_count_id <> OLD.stock_count_id OR NEW.product_id <> OLD.product_id THEN
        RAISE EXCEPTION 'Una línea de conteo no cambia de conteo ni de producto';
    END IF;
    IF (NEW.counted_quantity IS DISTINCT FROM OLD.counted_quantity
        OR NEW.expected_quantity IS DISTINCT FROM OLD.expected_quantity
        OR NEW.counted_by IS DISTINCT FROM OLD.counted_by
        OR NEW.counted_at IS DISTINCT FROM OLD.counted_at)
        AND count_status <> 'open' THEN
        RAISE EXCEPTION 'Solo se anota con el conteo abierto';
    END IF;
    IF NEW.is_open AND NOT OLD.is_open THEN
        RAISE EXCEPTION 'Una línea cerrada no se vuelve a abrir';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER stock_count_line_guard BEFORE INSERT OR UPDATE OR DELETE ON stock_count_line
    FOR EACH ROW EXECUTE FUNCTION stock_count_line_guard();
"""

FUNCTIONS = (
    "stock_movement_apply",
    "reject_change",
    "product_stock_guard",
    "category_prefix_guard",
    "adjustment_request_guard",
    "stock_count_guard",
    "stock_count_line_guard",
)

# Datos iniciales (FR-028, research R5 y R12). UUIDv7 fijos para que sean reproducibles.
UNIT_METER = "01a136c3-ff63-70d9-9311-58a755c43e81"
UNIT_PIECE = "01a136c3-ff63-70d9-9311-58a802f535fe"
CATEGORY_HOSES = "01a136c3-ff63-70d9-9311-58a9cd7d7ff4"
CATEGORY_FITTINGS = "01a136c3-ff63-70d9-9311-58aad5ab4849"
CATEGORY_FERRULES = "01a136c3-ff63-70d9-9311-58abfe6fb9e9"
CATEGORY_HARDWARE = "01a136c3-ff63-70d9-9311-58ac8662b048"

UNITS = [(UNIT_METER, "m", "metro", 2), (UNIT_PIECE, "u", "unidad", 0)]
CATEGORIES = [
    (CATEGORY_HOSES, "Mangueras", "MAN", UNIT_METER, True),
    (CATEGORY_FITTINGS, "Conexiones", "CON", UNIT_PIECE, False),
    (CATEGORY_FERRULES, "Ferrules", "FER", UNIT_PIECE, False),
    (CATEGORY_HARDWARE, "Ferretería", "FRT", UNIT_PIECE, False),
]

SIZES = ['1/4"', '5/16"', '3/8"', '1/2"', '5/8"', '3/4"', '1"', '1 1/4"', '1 1/2"', '2"']
HOSE_TYPES = ["R1", "R2", "R3", "R12", "4SP", "4SH"]
THREADS = ["JIC", "NPT", "BSP", "ORFS", "Métrica"]

# (id, categoría, clave, etiqueta, tipo, opciones, obligatorio, filtrable, orden)
ATTRIBUTES = [
    ("01a136c3-ff63-70d9-9311-58ad95b6a604", CATEGORY_HOSES, "hose_type", "Tipo", "option",
     HOSE_TYPES, True, True, 1),
    ("01a136c3-ff63-70d9-9311-58ae599479bd", CATEGORY_HOSES, "diameter", "Diámetro", "option",
     SIZES, True, True, 2),
    ("01a136c3-ff63-70d9-9311-58af6bfceef4", CATEGORY_HOSES, "material", "Material", "text",
     None, False, False, 3),
    ("01a136c3-ff63-70d9-9311-58b0b846addd", CATEGORY_FITTINGS, "fitting_type", "Tipo", "text",
     None, True, False, 1),
    ("01a136c3-ff63-70d9-9311-58b1399bc07d", CATEGORY_FITTINGS, "thread", "Rosca", "option",
     THREADS, False, True, 2),
    ("01a136c3-ff63-70d9-9311-58b2822f1db1", CATEGORY_FITTINGS, "size", "Medida", "option",
     SIZES, True, True, 3),
    ("01a136c3-ff63-70d9-9311-58b3dc6a31af", CATEGORY_FITTINGS, "material", "Material", "text",
     None, False, False, 4),
    ("01a136c3-ff63-70d9-9311-58b407c25c8d", CATEGORY_FERRULES, "ferrule_type", "Tipo", "text",
     None, True, False, 1),
    ("01a136c3-ff63-70d9-9311-58b5d5f84ea0", CATEGORY_FERRULES, "size", "Medida", "option",
     SIZES, True, False, 2),
]  # fmt: skip


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _seed() -> None:
    for unit_id, code, name, decimals in UNITS:
        op.execute(
            "INSERT INTO unit (id, code, name, decimals) VALUES "
            f"('{unit_id}', '{code}', '{name}', {decimals})"
        )
    for category_id, name, prefix, unit_id, locked in CATEGORIES:
        op.execute(
            "INSERT INTO category (id, name, sku_prefix, default_unit_id, unit_locked) VALUES "
            f"('{category_id}', {_literal(name)}, '{prefix}', '{unit_id}', {locked})"
        )
    for row in ATTRIBUTES:
        attr_id, category_id, key, label, data_type, values, required, filterable, order = row
        options = (
            _literal(json.dumps([{"value": v, "is_active": True} for v in values]))
            if values
            else "NULL"
        )
        op.execute(
            "INSERT INTO attribute_definition (id, category_id, key, label, data_type, options, "
            "is_required, is_filterable, sort_order) VALUES "
            f"('{attr_id}', '{category_id}', '{key}', {_literal(label)}, '{data_type}', "
            f"{options}, {required}, {filterable}, {order})"
        )


def upgrade() -> None:
    op.execute(TABLES)
    op.execute(TRIGGERS)
    _seed()


def downgrade() -> None:
    for table in (
        "stock_count_line",
        "stock_count",
        "adjustment_request",
        "stock_movement",
        "product_photo",
        "product_price",
        "product",
        "attribute_definition",
        "category",
        "unit",
    ):
        op.execute(f"DROP TABLE {table}")
    for function in FUNCTIONS:
        op.execute(f"DROP FUNCTION {function}()")
