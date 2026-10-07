"""Dominios decimales para dinero y cantidades.

Declara en un solo lugar las escalas de ADR-0004 y de docs/modelo-de-datos.md §1.2.
Las tablas de las etapas siguientes usan estos dominios en lugar de NUMERIC directo.

Revisión: 0001
Anterior: ninguna
Fecha: 2026-10-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOMAINS = {
    "usd_amount": "NUMERIC(14,2)",  # Precios de venta y montos en USD
    "usd_cost": "NUMERIC(18,6)",  # Costos en USD, incluido el promedio ponderado
    "ves_amount": "NUMERIC(16,2)",  # Montos en Bs
    "rate": "NUMERIC(18,8) CHECK (VALUE > 0)",  # Tasa BCV
    "quantity": "NUMERIC(14,2)",  # Cantidades y stock (puede ser negativo, RN-10)
    "percent": "NUMERIC(5,2) CHECK (VALUE >= 0 AND VALUE <= 100)",  # Descuentos
}


def upgrade() -> None:
    for name, definition in DOMAINS.items():
        op.execute(f"CREATE DOMAIN {name} AS {definition}")


def downgrade() -> None:
    for name in reversed(DOMAINS):
        op.execute(f"DROP DOMAIN {name}")
