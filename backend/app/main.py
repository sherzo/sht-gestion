"""Punto de entrada de la API de SHT Gestión."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    alerts,
    audit,
    auth,
    catalog_config,
    charge_templates,
    customers,
    devices,
    exchange_rates,
    health,
    inventory,
    products,
    purchases,
    setup,
    stock_counts,
    suppliers,
    sync,
    users,
)
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
    api_v1.include_router(catalog_config.router)
    api_v1.include_router(products.router)
    api_v1.include_router(inventory.router)
    api_v1.include_router(stock_counts.router)
    api_v1.include_router(suppliers.router)
    api_v1.include_router(purchases.router)
    api_v1.include_router(exchange_rates.router)
    api_v1.include_router(charge_templates.router)
    api_v1.include_router(alerts.router)
    api_v1.include_router(devices.router)
    api_v1.include_router(customers.router)
    api_v1.include_router(sync.router)
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
