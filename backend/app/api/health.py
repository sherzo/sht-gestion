"""Endpoints de salud: los usan el despliegue y el monitoreo, no requieren sesión."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import get_engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/db")
def health_db() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "database_unavailable", "message": "La base de datos no responde"},
        ) from exc
    return {"status": "ok"}
