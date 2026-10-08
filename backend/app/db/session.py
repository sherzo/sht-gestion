"""Conexión a Postgres.

En producción la API se conecta a Supabase a través de su pooler en modo transacción,
porque Cloud Run escala a cero y abre conexiones de forma intermitente (ADR-0002). Ese
modo no admite sentencias preparadas del lado del servidor, así que se desactivan
(`prepare_threshold=None`).
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

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


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    # expire_on_commit=False: los objetos siguen legibles después de confirmar, para
    # construir la respuesta.
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Una sesión por petición. Los servicios confirman con commit() explícito; si algo
    falla antes, la transacción se deshace al cerrar."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
