"""Equipos, apertura de caja, clientes, ventas, pagos, descuentos y cola de salida (RF-18,
RF-20 a RF-30, RN-01 a RN-07, RN-10 a RN-12, RN-16).

Tablas de specs/004-ventas-multimoneda/data-model.md. La base impone las reglas que no
pueden depender solo del código (principio II, research R9):

- Ventas, líneas, pagos, anulaciones y operaciones de la cola son de solo inserción.
- Un equipo solo se revoca una vez y su correlativo solo avanza; una caja no cambia sus
  datos de apertura; una autorización de descuento solo pasa de pendiente a aprobada
  (pudiendo bajar su valor) o rechazada.
- Equipos, cajas, clientes, autorizaciones y métodos de pago no se borran.
- Como máximo una caja abierta por equipo (RN-16).
- Un pago con un método que exige referencia no se guarda sin ella (RF-24).

Incluye los seis métodos de pago (RF-24), el contador de series de equipos (research R3),
los tipos de alerta de la venta (research R6) y las FK de `device_id` que la 1.1 dejó
pendientes.

Revisión: 0006
Anterior: 0005
Fecha: 2026-10-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = """
CREATE TABLE device (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    series text NOT NULL,
    last_sequence_number integer NOT NULL DEFAULT 0,
    token_hash text NOT NULL,
    registered_by uuid NOT NULL REFERENCES app_user (id),
    registered_at timestamptz NOT NULL,
    revoked_at timestamptz,
    revoked_by uuid REFERENCES app_user (id),
    CONSTRAINT ux_device_series UNIQUE (series),
    CONSTRAINT ux_device_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_device_name_length CHECK (char_length(name) BETWEEN 1 AND 60),
    CONSTRAINT ck_device_series_format CHECK (series ~ '^[A-Z]{1,3}$'),
    CONSTRAINT ck_device_sequence_positive CHECK (last_sequence_number >= 0),
    CONSTRAINT ck_device_revoked_pair CHECK ((revoked_at IS NULL) = (revoked_by IS NULL))
);

CREATE TABLE outbox_operation (
    id uuid PRIMARY KEY,
    device_id uuid NOT NULL REFERENCES device (id),
    user_id uuid NOT NULL REFERENCES app_user (id),
    operation_type text NOT NULL,
    schema_version smallint NOT NULL,
    payload jsonb NOT NULL,
    created_at_device timestamptz NOT NULL,
    received_at timestamptz NOT NULL,
    processed_at timestamptz NOT NULL,
    status text NOT NULL,
    http_status smallint NOT NULL,
    result jsonb,
    error jsonb,
    CONSTRAINT ck_outbox_operation_status_valid CHECK (status IN ('processed', 'rejected')),
    CONSTRAINT ck_outbox_operation_outcome CHECK (
        (status = 'processed' AND result IS NOT NULL AND error IS NULL)
        OR (status = 'rejected' AND error IS NOT NULL AND result IS NULL))
);
CREATE INDEX ix_outbox_operation_device ON outbox_operation (device_id, received_at DESC);

CREATE TABLE cash_session (
    id uuid PRIMARY KEY,
    device_id uuid NOT NULL REFERENCES device (id),
    business_date date NOT NULL,
    opened_by uuid NOT NULL REFERENCES app_user (id),
    opened_at timestamptz NOT NULL,
    opening_float_ves ves_amount NOT NULL,
    opening_float_usd usd_amount NOT NULL,
    status text NOT NULL DEFAULT 'open',
    -- Diferida: la fila de la cola se inserta al final, con el resultado (research R4).
    outbox_operation_id uuid NOT NULL REFERENCES outbox_operation (id)
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT ux_cash_session_operation UNIQUE (outbox_operation_id),
    CONSTRAINT ck_cash_session_status_valid CHECK (status IN ('open')),
    CONSTRAINT ck_cash_session_floats CHECK (opening_float_ves >= 0 AND opening_float_usd >= 0)
);
CREATE UNIQUE INDEX ux_cash_session_open_device ON cash_session (device_id)
    WHERE status = 'open';

CREATE TABLE customer (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    document_id text,
    phone text,
    created_at timestamptz NOT NULL,
    created_by uuid NOT NULL REFERENCES app_user (id),
    CONSTRAINT ux_customer_document UNIQUE (document_id),
    CONSTRAINT ck_customer_name_length CHECK (char_length(name) BETWEEN 2 AND 100),
    CONSTRAINT ck_customer_document_format CHECK (
        document_id IS NULL
        OR document_id ~ '^[VE]-[0-9]{6,8}$'
        OR document_id ~ '^[JGVEPC]-[0-9]{8}-[0-9]$'),
    CONSTRAINT ck_customer_phone_length CHECK (phone IS NULL OR char_length(phone) <= 30)
);

CREATE TABLE payment_method (
    code text PRIMARY KEY,
    name text NOT NULL,
    currency text NOT NULL,
    requires_reference boolean NOT NULL,
    is_cash boolean NOT NULL,
    sort_order smallint NOT NULL,
    CONSTRAINT ck_payment_method_currency_valid CHECK (currency IN ('VES', 'USD', 'USDT'))
);

CREATE TABLE discount_authorization (
    id uuid PRIMARY KEY,
    sale_id uuid NOT NULL,
    sale_item_id uuid,
    product_id uuid REFERENCES product (id),
    discount_type text NOT NULL,
    requested_value numeric(14, 2) NOT NULL,
    discount_value numeric(14, 2) NOT NULL,
    base_usd usd_amount NOT NULL,
    discount_usd usd_amount NOT NULL,
    method text NOT NULL,
    status text NOT NULL,
    requested_by uuid NOT NULL REFERENCES app_user (id),
    requested_at timestamptz NOT NULL,
    device_id uuid NOT NULL REFERENCES device (id),
    decided_by uuid REFERENCES app_user (id),
    decided_at timestamptz,
    rejection_reason text,
    CONSTRAINT ck_discount_authorization_type_valid CHECK (
        discount_type IN ('amount', 'percent')),
    CONSTRAINT ck_discount_authorization_method_valid CHECK (method IN ('pin', 'request')),
    CONSTRAINT ck_discount_authorization_status_valid CHECK (
        status IN ('pending', 'approved', 'rejected')),
    CONSTRAINT ck_discount_authorization_values CHECK (
        discount_value > 0 AND discount_value <= requested_value
        AND (discount_type = 'amount' OR requested_value <= 100)
        AND base_usd >= 0 AND discount_usd >= 0 AND discount_usd <= base_usd),
    CONSTRAINT ck_discount_authorization_decision CHECK (
        (status = 'pending') = (decided_by IS NULL)
        AND (decided_by IS NULL) = (decided_at IS NULL)),
    CONSTRAINT ck_discount_authorization_rejection CHECK (
        rejection_reason IS NULL
        OR (status = 'rejected' AND char_length(rejection_reason) <= 200))
);
CREATE INDEX ix_discount_authorization_pending ON discount_authorization (requested_at)
    WHERE status = 'pending';
CREATE INDEX ix_discount_authorization_sale ON discount_authorization (sale_id);

CREATE TABLE sale (
    id uuid PRIMARY KEY,
    device_id uuid NOT NULL REFERENCES device (id),
    series text NOT NULL,
    sequence_number integer NOT NULL,
    number text NOT NULL,
    cash_session_id uuid NOT NULL REFERENCES cash_session (id),
    seller_id uuid NOT NULL REFERENCES app_user (id),
    customer_id uuid REFERENCES customer (id),
    occurred_at timestamptz NOT NULL,
    business_date date NOT NULL,
    synced_at timestamptz NOT NULL,
    exchange_rate rate NOT NULL,
    exchange_rate_date date NOT NULL,
    subtotal_usd usd_amount NOT NULL,
    discount_type text,
    discount_value numeric(14, 2),
    discount_usd usd_amount NOT NULL,
    discount_authorized_by uuid REFERENCES app_user (id),
    discount_authorization_method text,
    discount_authorization_id uuid REFERENCES discount_authorization (id),
    total_usd usd_amount NOT NULL,
    total_ves ves_amount NOT NULL,
    paid_usd usd_amount NOT NULL,
    change_usd usd_amount NOT NULL,
    device_total_usd usd_amount NOT NULL,
    needs_review boolean NOT NULL DEFAULT false,
    -- Diferida: la fila de la cola se inserta al final, con el resultado (research R4).
    outbox_operation_id uuid NOT NULL REFERENCES outbox_operation (id)
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT ux_sale_series_sequence UNIQUE (series, sequence_number),
    CONSTRAINT ux_sale_number UNIQUE (number),
    CONSTRAINT ux_sale_discount_authorization UNIQUE (discount_authorization_id),
    CONSTRAINT ux_sale_operation UNIQUE (outbox_operation_id),
    CONSTRAINT ck_sale_sequence_positive CHECK (sequence_number >= 1),
    CONSTRAINT ck_sale_series_format CHECK (series ~ '^[A-Z]{1,3}$'),
    CONSTRAINT ck_sale_discount_fields CHECK (
        (discount_type IS NULL) = (discount_value IS NULL)
        AND (discount_type IS NOT NULL OR discount_usd = 0)
        AND (discount_type IS NULL OR discount_type IN ('amount', 'percent'))),
    CONSTRAINT ck_sale_authorization_method CHECK (
        discount_authorization_method IS NULL
        OR (discount_type IS NOT NULL
            AND discount_authorization_method IN ('pin', 'request', 'admin_self'))),
    CONSTRAINT ck_sale_totals CHECK (
        total_usd >= 0 AND total_usd = subtotal_usd - discount_usd
        AND paid_usd >= 0 AND change_usd >= 0)
);
CREATE INDEX ix_sale_business_date ON sale (business_date DESC, occurred_at DESC);
CREATE INDEX ix_sale_seller_date ON sale (seller_id, business_date);
CREATE INDEX ix_sale_customer ON sale (customer_id);
CREATE INDEX ix_sale_cash_session ON sale (cash_session_id);

CREATE TABLE sale_item (
    id uuid PRIMARY KEY,
    sale_id uuid NOT NULL REFERENCES sale (id),
    line_number smallint NOT NULL,
    product_id uuid NOT NULL REFERENCES product (id),
    quantity quantity NOT NULL,
    entered_unit text NOT NULL,
    unit_price_usd usd_amount NOT NULL,
    server_price_usd usd_amount,
    line_subtotal_usd usd_amount NOT NULL,
    item_discount_type text,
    item_discount_value numeric(14, 2),
    item_discount_usd usd_amount NOT NULL,
    item_discount_authorized_by uuid REFERENCES app_user (id),
    item_discount_authorization_method text,
    item_discount_authorization_id uuid REFERENCES discount_authorization (id),
    allocated_sale_discount_usd usd_amount NOT NULL,
    line_total_usd usd_amount NOT NULL,
    unit_cost_usd usd_cost,
    CONSTRAINT ux_sale_item_line UNIQUE (sale_id, line_number),
    CONSTRAINT ux_sale_item_authorization UNIQUE (item_discount_authorization_id),
    CONSTRAINT ck_sale_item_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_sale_item_entered_unit CHECK (entered_unit IN ('m', 'cm', 'unit')),
    CONSTRAINT ck_sale_item_discount_fields CHECK (
        (item_discount_type IS NULL) = (item_discount_value IS NULL)
        AND (item_discount_type IS NOT NULL OR item_discount_usd = 0)
        AND (item_discount_type IS NULL OR item_discount_type IN ('amount', 'percent'))),
    CONSTRAINT ck_sale_item_authorization_method CHECK (
        item_discount_authorization_method IS NULL
        OR (item_discount_type IS NOT NULL
            AND item_discount_authorization_method IN ('pin', 'request', 'admin_self'))),
    CONSTRAINT ck_sale_item_totals CHECK (
        line_total_usd >= 0
        AND line_total_usd = line_subtotal_usd - item_discount_usd - allocated_sale_discount_usd)
);
CREATE INDEX ix_sale_item_product ON sale_item (product_id);

CREATE TABLE sale_void (
    id uuid PRIMARY KEY,
    sale_id uuid NOT NULL REFERENCES sale (id),
    reason text NOT NULL,
    voided_by uuid NOT NULL REFERENCES app_user (id),
    voided_at timestamptz NOT NULL,
    CONSTRAINT ux_sale_void_sale UNIQUE (sale_id),
    CONSTRAINT ck_sale_void_reason CHECK (char_length(reason) BETWEEN 5 AND 500)
);

CREATE TABLE payment (
    id uuid PRIMARY KEY,
    sale_id uuid NOT NULL REFERENCES sale (id),
    line_number smallint NOT NULL,
    cash_session_id uuid NOT NULL REFERENCES cash_session (id),
    kind text NOT NULL,
    payment_method_code text NOT NULL REFERENCES payment_method (code),
    currency text NOT NULL,
    amount numeric(16, 2) NOT NULL,
    exchange_rate rate NOT NULL,
    amount_usd usd_amount NOT NULL,
    reference text,
    sale_void_id uuid REFERENCES sale_void (id),
    CONSTRAINT ux_payment_line UNIQUE (sale_id, kind, line_number),
    CONSTRAINT ck_payment_kind_valid CHECK (
        kind IN ('sale_payment', 'change', 'void_refund', 'void_change')),
    CONSTRAINT ck_payment_amount_positive CHECK (amount > 0 AND amount_usd >= 0),
    CONSTRAINT ck_payment_currency_valid CHECK (currency IN ('VES', 'USD', 'USDT')),
    CONSTRAINT ck_payment_reference_length CHECK (
        reference IS NULL OR char_length(reference) BETWEEN 1 AND 60),
    CONSTRAINT ck_payment_void_link CHECK (
        (kind IN ('void_refund', 'void_change')) = (sale_void_id IS NOT NULL))
);
CREATE INDEX ix_payment_cash_session ON payment (cash_session_id);

INSERT INTO payment_method (code, name, currency, requires_reference, is_cash, sort_order)
VALUES
    ('cash_ves', 'Efectivo Bs', 'VES', false, true, 1),
    ('mobile_payment', 'Pago móvil / transferencia', 'VES', true, false, 2),
    ('pos_card', 'Punto de venta', 'VES', true, false, 3),
    ('cash_usd', 'Efectivo USD', 'USD', false, true, 4),
    ('zelle', 'Zelle', 'USD', true, false, 5),
    ('binance_usdt', 'Binance USDT', 'USDT', true, false, 6);

INSERT INTO sequence_counter (name, next_number) VALUES ('device_series', 1);

ALTER TABLE user_session ADD CONSTRAINT fk_user_session_device
    FOREIGN KEY (device_id) REFERENCES device (id);
ALTER TABLE stock_movement ADD CONSTRAINT fk_stock_movement_device
    FOREIGN KEY (device_id) REFERENCES device (id);
ALTER TABLE audit_log ADD CONSTRAINT fk_audit_log_device
    FOREIGN KEY (device_id) REFERENCES device (id);

ALTER TABLE alert DROP CONSTRAINT ck_alert_type_valid;
ALTER TABLE alert ADD CONSTRAINT ck_alert_type_valid CHECK (type IN (
    'purchase_void_cost', 'negative_stock', 'price_mismatch', 'total_mismatch',
    'rate_mismatch', 'discount_review', 'inactive_user_sync', 'revoked_device_sync'));
CREATE INDEX ix_alert_entity ON alert (entity_type, entity_id);
"""

TRIGGERS = """
-- Solo inserción (RN-12): ventas, líneas, pagos, anulaciones y operaciones de la cola.
CREATE TRIGGER sale_immutable BEFORE UPDATE OR DELETE ON sale
    FOR EACH ROW EXECUTE FUNCTION reject_change();
CREATE TRIGGER sale_item_immutable BEFORE UPDATE OR DELETE ON sale_item
    FOR EACH ROW EXECUTE FUNCTION reject_change();
CREATE TRIGGER payment_immutable BEFORE UPDATE OR DELETE ON payment
    FOR EACH ROW EXECUTE FUNCTION reject_change();
CREATE TRIGGER sale_void_immutable BEFORE UPDATE OR DELETE ON sale_void
    FOR EACH ROW EXECUTE FUNCTION reject_change();
CREATE TRIGGER outbox_operation_immutable BEFORE UPDATE OR DELETE ON outbox_operation
    FOR EACH ROW EXECUTE FUNCTION reject_change();

-- No se borran.
CREATE TRIGGER device_no_delete BEFORE DELETE ON device
    FOR EACH ROW EXECUTE FUNCTION reject_delete();
CREATE TRIGGER cash_session_no_delete BEFORE DELETE ON cash_session
    FOR EACH ROW EXECUTE FUNCTION reject_delete();
CREATE TRIGGER customer_no_delete BEFORE DELETE ON customer
    FOR EACH ROW EXECUTE FUNCTION reject_delete();
CREATE TRIGGER discount_authorization_no_delete BEFORE DELETE ON discount_authorization
    FOR EACH ROW EXECUTE FUNCTION reject_delete();
CREATE TRIGGER payment_method_no_delete BEFORE DELETE ON payment_method
    FOR EACH ROW EXECUTE FUNCTION reject_delete();

-- Equipo: se revoca una sola vez y su correlativo solo avanza (research R3, R5).
CREATE FUNCTION device_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (to_jsonb(NEW) - 'revoked_at' - 'revoked_by' - 'last_sequence_number')
        <> (to_jsonb(OLD) - 'revoked_at' - 'revoked_by' - 'last_sequence_number') THEN
        RAISE EXCEPTION 'Un equipo no cambia su nombre, serie ni token';
    END IF;
    IF OLD.revoked_at IS NOT NULL AND (
        NEW.revoked_at IS DISTINCT FROM OLD.revoked_at
        OR NEW.revoked_by IS DISTINCT FROM OLD.revoked_by) THEN
        RAISE EXCEPTION 'Un equipo revocado no cambia su revocación';
    END IF;
    IF NEW.last_sequence_number < OLD.last_sequence_number THEN
        RAISE EXCEPTION 'El correlativo de un equipo solo avanza';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER device_guard BEFORE UPDATE ON device
    FOR EACH ROW EXECUTE FUNCTION device_guard();

-- Caja: los datos de apertura no cambian; el cierre llega en la 1.4 (research R7).
CREATE FUNCTION cash_session_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (to_jsonb(NEW) - 'status') <> (to_jsonb(OLD) - 'status') THEN
        RAISE EXCEPTION 'Los datos de apertura de una caja no se modifican';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cash_session_guard BEFORE UPDATE ON cash_session
    FOR EACH ROW EXECUTE FUNCTION cash_session_guard();

-- Autorización de descuento: solo pendiente → aprobada o rechazada; al aprobar, el valor
-- y el descuento pueden bajar, nunca subir. El cálculo lo hace el servicio (research R8).
CREATE FUNCTION discount_authorization_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status <> 'pending' OR NEW.status NOT IN ('approved', 'rejected') THEN
        RAISE EXCEPTION 'Una autorización de descuento solo se decide una vez';
    END IF;
    IF NEW.discount_value > OLD.discount_value OR NEW.discount_usd > OLD.discount_usd THEN
        RAISE EXCEPTION 'Al aprobar, el descuento no puede ser mayor que el pedido';
    END IF;
    IF (to_jsonb(NEW) - 'status' - 'decided_by' - 'decided_at' - 'rejection_reason'
            - 'discount_value' - 'discount_usd')
        <> (to_jsonb(OLD) - 'status' - 'decided_by' - 'decided_at' - 'rejection_reason'
            - 'discount_value' - 'discount_usd') THEN
        RAISE EXCEPTION 'Los datos de una solicitud de descuento no se modifican';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER discount_authorization_guard BEFORE UPDATE ON discount_authorization
    FOR EACH ROW EXECUTE FUNCTION discount_authorization_guard();

-- Referencia obligatoria según el método (RF-24).
CREATE FUNCTION payment_reference_check() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.reference IS NULL AND EXISTS (
        SELECT 1 FROM payment_method
        WHERE code = NEW.payment_method_code AND requires_reference) THEN
        RAISE EXCEPTION 'El método % exige referencia', NEW.payment_method_code;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER payment_reference_check BEFORE INSERT ON payment
    FOR EACH ROW EXECUTE FUNCTION payment_reference_check();
"""

FUNCTIONS = (
    "device_guard",
    "cash_session_guard",
    "discount_authorization_guard",
    "payment_reference_check",
)


def upgrade() -> None:
    op.execute(TABLES)
    op.execute(TRIGGERS)


def downgrade() -> None:
    # Las alertas de venta impiden restaurar el CHECK anterior: se quitan antes (el trigger
    # de alertas no permite borrar, así que se desactiva solo para esto).
    op.execute("DROP INDEX ix_alert_entity")
    op.execute("ALTER TABLE alert DISABLE TRIGGER alert_guard")
    op.execute("DELETE FROM alert WHERE type <> 'purchase_void_cost'")
    op.execute("ALTER TABLE alert ENABLE TRIGGER alert_guard")
    op.execute("ALTER TABLE alert DROP CONSTRAINT ck_alert_type_valid")
    op.execute(
        "ALTER TABLE alert ADD CONSTRAINT ck_alert_type_valid "
        "CHECK (type IN ('purchase_void_cost'))"
    )
    for table, constraint in (
        ("audit_log", "fk_audit_log_device"),
        ("stock_movement", "fk_stock_movement_device"),
        ("user_session", "fk_user_session_device"),
    ):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {constraint}")
    op.execute("DELETE FROM sequence_counter WHERE name = 'device_series'")
    for table in (
        "payment",
        "sale_void",
        "sale_item",
        "sale",
        "discount_authorization",
        "payment_method",
        "customer",
        "cash_session",
        "outbox_operation",
        "device",
    ):
        op.execute(f"DROP TABLE {table}")
    for function in FUNCTIONS:
        op.execute(f"DROP FUNCTION {function}()")
