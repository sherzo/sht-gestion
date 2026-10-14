"""Proveedores, compras con gastos, tasa BCV y alertas (RF-13 a RF-17, RN-09, RN-14,
RN-15, RN-20).

Tablas de specs/003-proveedores-compras/data-model.md. La base impone las reglas que no
pueden depender solo del código (principio II, research R2):

- Una compra en borrador se edita y se borra; confirmada, solo puede pasar a anulada sin
  cambiar ningún otro dato. Sus líneas y gastos solo cambian con la compra en borrador.
- `purchase_void` es de solo inserción.
- Proveedores, gastos frecuentes y tasas no se borran; una tasa no cambia de fecha.
- Una alerta solo se marca como revisada.

Incluye la fila inicial del correlativo de compras (FR-008, research R3).

Revisión: 0005
Anterior: 0004
Fecha: 2026-10-13
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = """
CREATE TABLE supplier (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    rif text,
    phone text,
    notes text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES app_user (id),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_supplier_name_length CHECK (char_length(name) BETWEEN 1 AND 120),
    CONSTRAINT ck_supplier_rif_format CHECK (rif IS NULL OR rif ~ '^[JGVEPC]-[0-9]{8}-[0-9]$'),
    CONSTRAINT ck_supplier_phone_length CHECK (phone IS NULL OR char_length(phone) <= 30),
    CONSTRAINT ck_supplier_notes_length CHECK (notes IS NULL OR char_length(notes) <= 1000)
);
CREATE UNIQUE INDEX ux_supplier_rif ON supplier (rif);

CREATE TABLE exchange_rate (
    id uuid PRIMARY KEY,
    rate_type text NOT NULL DEFAULT 'BCV',
    business_date date NOT NULL,
    rate rate NOT NULL,
    created_by uuid NOT NULL REFERENCES app_user (id),
    created_at timestamptz NOT NULL,
    updated_by uuid REFERENCES app_user (id),
    updated_at timestamptz,
    CONSTRAINT ck_exchange_rate_type_valid CHECK (rate_type IN ('BCV')),
    CONSTRAINT ux_exchange_rate_type_date UNIQUE (rate_type, business_date),
    CONSTRAINT ck_exchange_rate_correction CHECK ((updated_by IS NULL) = (updated_at IS NULL))
);
CREATE INDEX ix_exchange_rate_type_date ON exchange_rate (rate_type, business_date DESC);

CREATE TABLE charge_template (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    charge_type text NOT NULL,
    default_value numeric(16,2),
    currency text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid REFERENCES app_user (id),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_charge_template_name_length CHECK (char_length(name) BETWEEN 1 AND 80),
    CONSTRAINT ck_charge_template_type_valid CHECK (charge_type IN ('percent', 'fixed')),
    CONSTRAINT ck_charge_template_currency CHECK (
        (charge_type = 'fixed' AND currency IN ('USD', 'VES'))
        OR (charge_type = 'percent' AND currency IS NULL)),
    CONSTRAINT ck_charge_template_value CHECK (
        default_value IS NULL
        OR (default_value > 0 AND (charge_type = 'fixed' OR default_value <= 100)))
);
CREATE UNIQUE INDEX ux_charge_template_active_name ON charge_template (lower(name))
    WHERE is_active;

CREATE TABLE sequence_counter (
    name text PRIMARY KEY,
    next_number bigint NOT NULL,
    CONSTRAINT ck_sequence_counter_positive CHECK (next_number >= 1)
);

CREATE TABLE purchase (
    id uuid PRIMARY KEY,
    number text,
    supplier_id uuid NOT NULL REFERENCES supplier (id),
    purchase_date date NOT NULL,
    supplier_invoice_number text,
    currency text NOT NULL,
    exchange_rate rate,
    exchange_rate_date date,
    merchandise_total_usd usd_amount NOT NULL,
    merchandise_total_ves ves_amount,
    charges_total_usd usd_amount NOT NULL,
    total_usd usd_amount NOT NULL,
    status text NOT NULL DEFAULT 'draft',
    notes text,
    created_by uuid NOT NULL REFERENCES app_user (id),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    confirmed_by uuid REFERENCES app_user (id),
    confirmed_at timestamptz,
    CONSTRAINT ux_purchase_number UNIQUE (number),
    CONSTRAINT ck_purchase_status_valid CHECK (status IN ('draft', 'confirmed', 'voided')),
    CONSTRAINT ck_purchase_currency_valid CHECK (currency IN ('USD', 'VES')),
    CONSTRAINT ck_purchase_rate_with_date CHECK (
        (exchange_rate IS NULL) = (exchange_rate_date IS NULL)),
    CONSTRAINT ck_purchase_rate_for_ves CHECK (currency = 'USD' OR exchange_rate IS NOT NULL),
    CONSTRAINT ck_purchase_ves_total CHECK (
        (currency = 'VES') = (merchandise_total_ves IS NOT NULL)),
    CONSTRAINT ck_purchase_confirmed_fields CHECK (
        status = 'draft'
        OR (number IS NOT NULL AND confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)),
    CONSTRAINT ck_purchase_invoice_length CHECK (
        supplier_invoice_number IS NULL OR char_length(supplier_invoice_number) <= 50),
    CONSTRAINT ck_purchase_notes_length CHECK (notes IS NULL OR char_length(notes) <= 1000),
    CONSTRAINT ck_purchase_totals CHECK (
        merchandise_total_usd >= 0 AND charges_total_usd >= 0
        AND total_usd = merchandise_total_usd + charges_total_usd)
);
CREATE INDEX ix_purchase_status_date ON purchase (status, purchase_date DESC);
CREATE INDEX ix_purchase_supplier_date ON purchase (supplier_id, purchase_date DESC);
CREATE INDEX ix_purchase_supplier_invoice
    ON purchase (supplier_id, lower(supplier_invoice_number));

CREATE TABLE purchase_item (
    id uuid PRIMARY KEY,
    purchase_id uuid NOT NULL REFERENCES purchase (id),
    product_id uuid NOT NULL REFERENCES product (id),
    line_number integer NOT NULL,
    quantity quantity NOT NULL,
    unit_cost_ves ves_amount,
    unit_cost_usd usd_cost NOT NULL,
    line_total_ves ves_amount,
    line_total_usd usd_amount NOT NULL,
    allocated_charges_usd usd_amount NOT NULL,
    landed_unit_cost_usd usd_cost NOT NULL,
    CONSTRAINT ux_purchase_item_product UNIQUE (purchase_id, product_id),
    CONSTRAINT ck_purchase_item_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_purchase_item_cost_positive CHECK (unit_cost_usd > 0),
    CONSTRAINT ck_purchase_item_ves_cost CHECK (unit_cost_ves IS NULL OR unit_cost_ves > 0),
    CONSTRAINT ck_purchase_item_ves_pair CHECK (
        (unit_cost_ves IS NULL) = (line_total_ves IS NULL)),
    CONSTRAINT ck_purchase_item_allocated CHECK (allocated_charges_usd >= 0),
    CONSTRAINT ck_purchase_item_landed CHECK (landed_unit_cost_usd > 0)
);
CREATE INDEX ix_purchase_item_purchase ON purchase_item (purchase_id);
CREATE INDEX ix_purchase_item_product ON purchase_item (product_id);

CREATE TABLE purchase_charge (
    id uuid PRIMARY KEY,
    purchase_id uuid NOT NULL REFERENCES purchase (id),
    line_number integer NOT NULL,
    description text NOT NULL,
    charge_type text NOT NULL,
    percent percent,
    amount numeric(16,2),
    currency text,
    amount_usd usd_amount NOT NULL,
    allocation_method text NOT NULL DEFAULT 'value',
    charge_template_id uuid REFERENCES charge_template (id),
    CONSTRAINT ck_purchase_charge_description CHECK (char_length(description) BETWEEN 1 AND 120),
    CONSTRAINT ck_purchase_charge_type_valid CHECK (charge_type IN ('percent', 'fixed')),
    CONSTRAINT ck_purchase_charge_fields CHECK (
        (charge_type = 'percent' AND percent > 0 AND amount IS NULL AND currency IS NULL)
        OR (charge_type = 'fixed' AND percent IS NULL AND amount > 0
            AND currency IN ('USD', 'VES'))),
    CONSTRAINT ck_purchase_charge_amount_usd CHECK (amount_usd >= 0),
    CONSTRAINT ck_purchase_charge_allocation CHECK (allocation_method IN ('value'))
);
CREATE INDEX ix_purchase_charge_purchase ON purchase_charge (purchase_id);

CREATE TABLE purchase_void (
    id uuid PRIMARY KEY,
    purchase_id uuid NOT NULL REFERENCES purchase (id),
    reason text NOT NULL,
    voided_by uuid NOT NULL REFERENCES app_user (id),
    voided_at timestamptz NOT NULL,
    CONSTRAINT ux_purchase_void_purchase UNIQUE (purchase_id),
    CONSTRAINT ck_purchase_void_reason CHECK (char_length(reason) BETWEEN 5 AND 500)
);

CREATE TABLE alert (
    id uuid PRIMARY KEY,
    type text NOT NULL,
    entity_type text NOT NULL,
    entity_id uuid NOT NULL,
    details jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    resolved_at timestamptz,
    resolved_by uuid REFERENCES app_user (id),
    CONSTRAINT ck_alert_type_valid CHECK (type IN ('purchase_void_cost')),
    CONSTRAINT ck_alert_resolved_pair CHECK ((resolved_at IS NULL) = (resolved_by IS NULL))
);
CREATE INDEX ix_alert_open ON alert (created_at DESC) WHERE resolved_at IS NULL;

INSERT INTO sequence_counter (name, next_number) VALUES ('purchase', 1);
"""

TRIGGERS = """
-- Compra: en borrador se edita y se borra; confirmada solo pasa a anulada sin cambiar
-- ningún otro dato; anulada no cambia (RN-14, research R2).
CREATE FUNCTION purchase_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status <> 'draft' THEN
            RAISE EXCEPTION 'Una compra confirmada no se borra: se anula';
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.status = 'draft' THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'confirmed' AND NEW.status = 'voided'
        AND (to_jsonb(NEW) - 'status') = (to_jsonb(OLD) - 'status') THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Una compra confirmada no se modifica: se anula y se registra de nuevo';
END;
$$;
CREATE TRIGGER purchase_guard BEFORE UPDATE OR DELETE ON purchase
    FOR EACH ROW EXECUTE FUNCTION purchase_guard();

-- Líneas y gastos: solo con la compra en borrador.
CREATE FUNCTION purchase_child_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    parent_status text;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        SELECT status INTO parent_status FROM purchase WHERE id = OLD.purchase_id;
        IF parent_status IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'Las líneas y gastos de una compra confirmada no se modifican';
        END IF;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status INTO parent_status FROM purchase WHERE id = NEW.purchase_id;
        IF parent_status IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'Las líneas y gastos de una compra confirmada no se modifican';
        END IF;
        RETURN NEW;
    END IF;
    RETURN OLD;
END;
$$;
CREATE TRIGGER purchase_item_guard BEFORE INSERT OR UPDATE OR DELETE ON purchase_item
    FOR EACH ROW EXECUTE FUNCTION purchase_child_guard();
CREATE TRIGGER purchase_charge_guard BEFORE INSERT OR UPDATE OR DELETE ON purchase_charge
    FOR EACH ROW EXECUTE FUNCTION purchase_child_guard();

CREATE TRIGGER purchase_void_immutable BEFORE UPDATE OR DELETE ON purchase_void
    FOR EACH ROW EXECUTE FUNCTION reject_change();

-- Proveedores, gastos frecuentes y tasas no se borran.
CREATE FUNCTION reject_delete() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% no se borra: se desactiva o se corrige', TG_TABLE_NAME;
END;
$$;
CREATE TRIGGER supplier_no_delete BEFORE DELETE ON supplier
    FOR EACH ROW EXECUTE FUNCTION reject_delete();
CREATE TRIGGER charge_template_no_delete BEFORE DELETE ON charge_template
    FOR EACH ROW EXECUTE FUNCTION reject_delete();
CREATE TRIGGER exchange_rate_no_delete BEFORE DELETE ON exchange_rate
    FOR EACH ROW EXECUTE FUNCTION reject_delete();

-- Una tasa se corrige (RN-15), pero no cambia de tipo ni de fecha.
CREATE FUNCTION exchange_rate_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.rate_type IS DISTINCT FROM OLD.rate_type
        OR NEW.business_date IS DISTINCT FROM OLD.business_date THEN
        RAISE EXCEPTION 'Una tasa no cambia de tipo ni de fecha';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER exchange_rate_guard BEFORE UPDATE ON exchange_rate
    FOR EACH ROW EXECUTE FUNCTION exchange_rate_guard();

-- Una alerta solo pasa de abierta a revisada (research R8).
CREATE FUNCTION alert_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Las alertas no se borran';
    END IF;
    IF OLD.resolved_at IS NOT NULL OR NEW.resolved_at IS NULL
        OR (to_jsonb(NEW) - 'resolved_at' - 'resolved_by')
            <> (to_jsonb(OLD) - 'resolved_at' - 'resolved_by') THEN
        RAISE EXCEPTION 'Una alerta solo se marca como revisada';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER alert_guard BEFORE UPDATE OR DELETE ON alert
    FOR EACH ROW EXECUTE FUNCTION alert_guard();
"""

FUNCTIONS = (
    "purchase_guard",
    "purchase_child_guard",
    "reject_delete",
    "exchange_rate_guard",
    "alert_guard",
)


def upgrade() -> None:
    op.execute(TABLES)
    op.execute(TRIGGERS)


def downgrade() -> None:
    for table in (
        "alert",
        "purchase_void",
        "purchase_charge",
        "purchase_item",
        "purchase",
        "sequence_counter",
        "charge_template",
        "exchange_rate",
        "supplier",
    ):
        op.execute(f"DROP TABLE {table}")
    for function in FUNCTIONS:
        op.execute(f"DROP FUNCTION {function}()")
