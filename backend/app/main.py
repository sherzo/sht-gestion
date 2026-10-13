"""Punto de entrada de la API de SHT Gestión."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import audit, auth, health, setup, users
from app.core.config import get_settings
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SHT Gestión API", version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(health.router)
    api_v1.include_router(setup.router)
    api_v1.include_router(auth.router)
    api_v1.include_router(users.router)
    api_v1.include_router(audit.router)
    app.include_router(api_v1)

    # Fotos en disco solo en desarrollo y pruebas; en producción las sirve Supabase (R9).
    if settings.photo_storage == "local" and settings.environment in ("local", "test"):
        app.mount(
            "/media",
            StaticFiles(directory=settings.photo_local_dir, check_dir=False),
            name="media",
        )
    return app


app = create_app()
