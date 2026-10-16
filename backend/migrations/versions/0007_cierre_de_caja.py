"""Egresos, cierre y cuadre de caja (RF-27, RF-31 a RF-33, RN-12, RN-16).

Tablas y columnas de specs/005-cierre-caja/data-model.md. La base impone las reglas que no
pueden depender solo del código (principio II, research R2 y R3):

- Una caja solo pasa de abierta a cerrada, una vez, y cerrada no admite ningún cambio; sus
  datos de apertura nunca cambian.
- Una caja cerrada tiene exactamente un conteo por método de pago (se verifica al
  confirmar), y los conteos son de solo inserción y solo de cajas cerradas.
- Los egresos no se borran; solo se anulan, una vez y con la caja abierta. Un egreso con
  un método que exige referencia no se guarda sin ella (RF-24, PRD v0.12).

Incluye los tipos de alerta del cierre (research R11).

Revisión: 0007
Anterior: 0006
Fecha: 2026-10-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALERT_TYPES_0006 = (
    "'purchase_void_cost', 'negative_stock', 'price_mismatch', 'total_mismatch', "
    "'rate_mismatch', 'discount_review', 'inactive_user_sync', 'revoked_device_sync'"
)
ALERT_TYPES_0007 = (
    ALERT_TYPES_0006 + ", 'cash_difference', 'expected_mismatch', 'post_close_operation'"
)

TABLES = f"""
ALTER TABLE cash_session
    ADD COLUMN closed_at timestamptz,
    ADD COLUMN closed_recorded_at timestamptz,
    ADD COLUMN closed_by uuid REFERENCES app_user (id),
    ADD COLUMN closed_from_device_id uuid REFERENCES device (id),
    ADD COLUMN closed_outside_device boolean,
    ADD COLUMN closing_note text,
    -- Diferida: la fila de la cola se inserta al final, con el resultado (research R4 de
    -- la 1.3).
    ADD COLUMN closing_operation_id uuid REFERENCES outbox_operation (id)
        DEFERRABLE INITIALLY DEFERRED,
    ADD CONSTRAINT ux_cash_session_closing_operation UNIQUE (closing_operation_id),
    DROP CONSTRAINT ck_cash_session_status_valid,
    ADD CONSTRAINT ck_cash_session_status_valid CHECK (status IN ('open', 'closed')),
    ADD CONSTRAINT ck_cash_session_closing CHECK (
        (status = 'open'
            AND closed_at IS NULL AND closed_recorded_at IS NULL AND closed_by IS NULL
            AND closed_from_device_id IS NULL AND closed_outside_device IS NULL
            AND closing_note IS NULL AND closing_operation_id IS NULL)
        OR (status = 'closed'
            AND closed_at IS NOT NULL AND closed_recorded_at IS NOT NULL
            AND closed_by IS NOT NULL AND closed_outside_device IS NOT NULL)),
    ADD CONSTRAINT ck_cash_session_note_length CHECK (
        closing_note IS NULL OR char_length(closing_note) BETWEEN 5 AND 500);
CREATE INDEX ix_cash_session_business_date ON cash_session (business_date DESC, opened_at DESC);

CREATE TABLE cash_outflow (
    id uuid PRIMARY KEY,
    cash_session_id uuid NOT NULL REFERENCES cash_session (id),
    device_id uuid NOT NULL REFERENCES device (id),
    payment_method_code text NOT NULL REFERENCES payment_method (code),
    currency text NOT NULL,
    amount numeric(16, 2) NOT NULL,
    reason text NOT NULL,
    reference text,
    created_by uuid NOT NULL REFERENCES app_user (id),
    occurred_at timestamptz NOT NULL,
    outbox_operation_id uuid NOT NULL REFERENCES outbox_operation (id)
        DEFERRABLE INITIALLY DEFERRED,
    voided_at timestamptz,
    voided_by uuid REFERENCES app_user (id),
    void_reason text,
    CONSTRAINT ux_cash_outflow_operation UNIQUE (outbox_operation_id),
    CONSTRAINT ck_cash_outflow_currency_valid CHECK (currency IN ('VES', 'USD', 'USDT')),
    CONSTRAINT ck_cash_outflow_amount_positive CHECK (amount > 0),
    CONSTRAINT ck_cash_outflow_reason_length CHECK (char_length(reason) BETWEEN 5 AND 200),
    CONSTRAINT ck_cash_outflow_reference_length CHECK (
        reference IS NULL OR char_length(reference) BETWEEN 1 AND 60),
    CONSTRAINT ck_cash_outflow_void CHECK (
        (voided_at IS NULL AND voided_by IS NULL AND void_reason IS NULL)
        OR (voided_at IS NOT NULL AND voided_by IS NOT NULL
            AND char_length(void_reason) BETWEEN 5 AND 200))
);
CREATE INDEX ix_cash_outflow_cash_session ON cash_outflow (cash_session_id);

CREATE TABLE cash_count (
    id uuid PRIMARY KEY,
    cash_session_id uuid NOT NULL REFERENCES cash_session (id),
    payment_method_code text NOT NULL REFERENCES payment_method (code),
    currency text NOT NULL,
    expected_amount numeric(16, 2) NOT NULL,
    device_expected_amount numeric(16, 2),
    counted_amount numeric(16, 2) NOT NULL,
    difference numeric(16, 2) NOT NULL,
    CONSTRAINT ux_cash_count_method UNIQUE (cash_session_id, payment_method_code),
    CONSTRAINT ck_cash_count_currency_valid CHECK (currency IN ('VES', 'USD', 'USDT')),
    CONSTRAINT ck_cash_count_counted_non_negative CHECK (counted_amount >= 0),
    CONSTRAINT ck_cash_count_difference CHECK (difference = counted_amount - expected_amount)
);

ALTER TABLE alert DROP CONSTRAINT ck_alert_type_valid;
ALTER TABLE alert ADD CONSTRAINT ck_alert_type_valid CHECK (type IN ({ALERT_TYPES_0007}));
"""

TRIGGERS = """
-- Caja: los datos de apertura no cambian; la única transición es abierta → cerrada, y
-- cerrada no admite ningún cambio (RF-33, RN-12). El CHECK ck_cash_session_closing exige
-- que el cierre fije sus columnas a la vez (research R2).
CREATE OR REPLACE FUNCTION cash_session_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'closed' THEN
        RAISE EXCEPTION 'Una caja cerrada no se modifica';
    END IF;
    IF (to_jsonb(NEW) - 'status' - 'closed_at' - 'closed_recorded_at' - 'closed_by'
            - 'closed_from_device_id' - 'closed_outside_device' - 'closing_note'
            - 'closing_operation_id')
        <> (to_jsonb(OLD) - 'status' - 'closed_at' - 'closed_recorded_at' - 'closed_by'
            - 'closed_from_device_id' - 'closed_outside_device' - 'closing_note'
            - 'closing_operation_id') THEN
        RAISE EXCEPTION 'Los datos de apertura de una caja no se modifican';
    END IF;
    RETURN NEW;
END;
$$;

-- Al confirmar, una caja que pasó a cerrada tiene un conteo por cada método de pago (el
-- único por método impide que sobren).
CREATE FUNCTION cash_session_counts_complete() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = 'closed' AND OLD.status = 'open' AND
        (SELECT count(*) FROM cash_count WHERE cash_session_id = NEW.id)
            <> (SELECT count(*) FROM payment_method) THEN
        RAISE EXCEPTION 'Una caja cerrada debe tener un conteo por cada método de pago';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER cash_session_counts_complete AFTER UPDATE ON cash_session
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION cash_session_counts_complete();

-- Conteos: solo inserción y solo en una caja cerrada.
CREATE TRIGGER cash_count_immutable BEFORE UPDATE OR DELETE ON cash_count
    FOR EACH ROW EXECUTE FUNCTION reject_change();
CREATE FUNCTION cash_count_session_closed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM cash_session WHERE id = NEW.cash_session_id AND status = 'closed') THEN
        RAISE EXCEPTION 'Los conteos solo se registran al cerrar la caja';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cash_count_session_closed BEFORE INSERT ON cash_count
    FOR EACH ROW EXECUTE FUNCTION cash_count_session_closed();

-- Egresos: referencia obligatoria según el método, con la misma función de los pagos.
CREATE TRIGGER cash_outflow_reference BEFORE INSERT ON cash_outflow
    FOR EACH ROW EXECUTE FUNCTION payment_reference_check();

-- Egresos: no se borran; solo se anulan, una vez y con la caja abierta (research R3).
CREATE FUNCTION cash_outflow_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Un egreso no se borra: se anula';
    END IF;
    IF OLD.voided_at IS NOT NULL THEN
        RAISE EXCEPTION 'Un egreso anulado no se modifica';
    END IF;
    IF (to_jsonb(NEW) - 'voided_at' - 'voided_by' - 'void_reason')
        <> (to_jsonb(OLD) - 'voided_at' - 'voided_by' - 'void_reason') THEN
        RAISE EXCEPTION 'Los datos de un egreso no se modifican';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM cash_session WHERE id = OLD.cash_session_id AND status = 'open') THEN
        RAISE EXCEPTION 'Un egreso de una caja cerrada no se anula';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cash_outflow_guard BEFORE UPDATE OR DELETE ON cash_outflow
    FOR EACH ROW EXECUTE FUNCTION cash_outflow_guard();
"""

# Guard de la 1.3 (0006), que se restaura al bajar.
CASH_SESSION_GUARD_0006 = """
CREATE OR REPLACE FUNCTION cash_session_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (to_jsonb(NEW) - 'status') <> (to_jsonb(OLD) - 'status') THEN
        RAISE EXCEPTION 'Los datos de apertura de una caja no se modifican';
    END IF;
    RETURN NEW;
END;
$$;
"""


def upgrade() -> None:
    op.execute(TABLES)
    op.execute(TRIGGERS)


def downgrade() -> None:
    # Una caja cerrada no puede volver a abierta (habría más de una abierta por equipo y se
    # perdería su cierre): bajar solo es posible sin cierres.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM cash_session WHERE status = 'closed') THEN
                RAISE EXCEPTION 'No se puede bajar de 0007 con cajas cerradas';
            END IF;
        END;
        $$;
        """
    )
    # Las alertas del cierre impiden restaurar el CHECK anterior: se quitan antes (el
    # trigger de alertas no permite borrar, así que se desactiva solo para esto).
    op.execute("ALTER TABLE alert DISABLE TRIGGER alert_guard")
    op.execute(
        "DELETE FROM alert WHERE type IN "
        "('cash_difference', 'expected_mismatch', 'post_close_operation')"
    )
    op.execute("ALTER TABLE alert ENABLE TRIGGER alert_guard")
    op.execute("ALTER TABLE alert DROP CONSTRAINT ck_alert_type_valid")
    op.execute(
        f"ALTER TABLE alert ADD CONSTRAINT ck_alert_type_valid CHECK (type IN ({ALERT_TYPES_0006}))"
    )

    op.execute("DROP TABLE cash_count")
    op.execute("DROP TABLE cash_outflow")
    op.execute("DROP FUNCTION cash_count_session_closed()")
    op.execute("DROP FUNCTION cash_outflow_guard()")
    op.execute("DROP TRIGGER cash_session_counts_complete ON cash_session")
    op.execute("DROP FUNCTION cash_session_counts_complete()")
    op.execute(CASH_SESSION_GUARD_0006)
    op.execute("DROP INDEX ix_cash_session_business_date")
    op.execute(
        """
        ALTER TABLE cash_session
            DROP CONSTRAINT ck_cash_session_note_length,
            DROP CONSTRAINT ck_cash_session_closing,
            DROP CONSTRAINT ck_cash_session_status_valid,
            ADD CONSTRAINT ck_cash_session_status_valid CHECK (status IN ('open')),
            DROP COLUMN closing_operation_id,
            DROP COLUMN closing_note,
            DROP COLUMN closed_outside_device,
            DROP COLUMN closed_from_device_id,
            DROP COLUMN closed_by,
            DROP COLUMN closed_recorded_at,
            DROP COLUMN closed_at
        """
    )
