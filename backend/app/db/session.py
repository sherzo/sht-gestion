"""Conexión a Postgres.

En producción la API se conecta a Supabase a través de su pooler en modo transacción,
porque Cloud Run escala a cero y abre conexiones de forma intermitente (ADR-0002). Ese
modo no admite sentencias preparadas del lado del servidor, así que se desactivan
(`prepare_threshold=None`).
"""

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("Falta la variable de entorno DATABASE_URL")
    return create_engine(
        settings.database_url,
        # Pocas conexiones por instancia: el plan gratuito de Supabase limita el total.
        pool_size=2,
        max_overflow=3,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )
