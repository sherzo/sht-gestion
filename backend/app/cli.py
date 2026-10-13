"""Comandos de soporte de la API (research R8 de la etapa 1.1a y quickstart de la 1.1b).

Uso, desde backend/ y con DATABASE_URL apuntando a la base:

    uv run python -m app.cli reset-password <usuario>
    uv run python -m app.cli seed-demo-products 1000

`reset-password` asigna una contraseña temporal (RF-45/FR-016a), cierra las sesiones del
usuario y lo registra en la auditoría como acción de sistema. Sirve para recuperar al
único admin que olvidó su contraseña (procedimiento en docs/despliegue.md).

`seed-demo-products` crea productos sintéticos para medir la búsqueda (SC-001). Solo
funciona con ENVIRONMENT=local: nunca carga datos de prueba en producción.
"""

import argparse
import random
import secrets
import sys
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AppUser, Category, Product
from app.db.session import get_sessionmaker
from app.domain.search import build_search_text
from app.domain.sku import format_sku
from app.services.auth import normalize_username
from app.services.inventory import post_movement
from app.services.users import reset_password

SIZES = ['1/4"', '5/16"', '3/8"', '1/2"', '5/8"', '3/4"', '1"', '1 1/4"']
HOSE_TYPES = ["R1", "R2", "R3", "R12", "4SP", "4SH"]
THREADS = ["JIC", "NPT", "BSP", "ORFS"]
FITTINGS = ["Hembra giratoria", "Macho fijo", "Codo 90°", "Codo 45°", "Recta", "Te"]
FERRULES = ["Prensable", "Reutilizable", "Para 4SP"]
HARDWARE = ["Tornillo", "Arandela", "Tuerca", "Abrazadera", "Teflón", "Válvula de bola"]


def _reset_password(username: str) -> int:
    with get_sessionmaker()() as db:
        user = db.scalar(select(AppUser).where(AppUser.username == normalize_username(username)))
        if user is None:
            print(f"El usuario «{username}» no existe.", file=sys.stderr)
            return 1
        temporary = secrets.token_urlsafe(9)
        reset_password(db, actor=None, user_id=user.id, new_password=temporary)
    print(f"Contraseña temporal de {user.username} (deberá cambiarla al entrar): {temporary}")
    return 0


def _demo_product(prefix: str, rng: random.Random) -> tuple[str, dict[str, str]]:
    size = rng.choice(SIZES)
    if prefix == "MAN":
        kind = rng.choice(HOSE_TYPES)
        return f"Manguera hidráulica {kind} {size}", {"hose_type": kind, "diameter": size}
    if prefix == "CON":
        kind, thread = rng.choice(FITTINGS), rng.choice(THREADS)
        name = f"Conexión {kind.lower()} {thread} {size}"
        return name, {"fitting_type": kind, "size": size, "thread": thread}
    if prefix == "FER":
        kind = rng.choice(FERRULES)
        return f"Ferrule {kind.lower()} {size}", {"ferrule_type": kind, "size": size}
    return f"{rng.choice(HARDWARE)} {size}", {}


def seed_demo_products(db: Session, count: int, *, seed: int = 11) -> int:
    """Crea `count` productos repartidos entre las cuatro categorías iniciales, con stock
    cargado por movimientos de corrección (RN-08). Devuelve cuántos creó."""
    rng = random.Random(seed)
    categories = list(
        db.scalars(
            select(Category)
            .where(Category.sku_prefix.in_(["MAN", "CON", "FER", "FRT"]))
            .order_by(Category.sku_prefix)
            .with_for_update()
        )
    )
    created: list[tuple[Product, int]] = []
    for index in range(count):
        category = categories[index % len(categories)]
        name, attributes = _demo_product(category.sku_prefix, rng)
        sku = format_sku(category.sku_prefix, category.next_sku_number)
        category.next_sku_number += 1
        decimals = 2 if category.unit_locked else 0
        product = Product(
            sku=sku,
            category_id=category.id,
            unit_id=category.default_unit_id,
            name=name,
            description="Producto de prueba",
            attributes=attributes,
            search_text=build_search_text(name, "Producto de prueba", sku, attributes.values()),
            min_stock=Decimal(rng.randint(0, 10)),
            stock=Decimal("0"),
            is_active=True,
            is_published=False,
            cost_locked=False,
            has_movements=False,
        )
        db.add(product)
        created.append((product, decimals))
    db.flush()
    for product, decimals in created:
        if rng.random() < 0.7:
            quantity = Decimal(rng.randint(1, 5000)) / (100 if decimals else 1)
            post_movement(
                db,
                product_id=product.id,
                type="adjustment",
                quantity_delta=quantity,
                created_by=None,
                adjustment_reason="correction",
                note="Datos de prueba",
            )
    db.commit()
    return len(created)


def _seed_demo_products(count: int) -> int:
    if get_settings().environment != "local":
        print("seed-demo-products solo se permite con ENVIRONMENT=local.", file=sys.stderr)
        return 1
    with get_sessionmaker()() as db:
        created = seed_demo_products(db, count)
    print(f"Se crearon {created} productos de prueba.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="app.cli", description="Comandos de soporte de SHT Gestión"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    reset = commands.add_parser("reset-password", help="Asigna una contraseña temporal")
    reset.add_argument("username")
    demo = commands.add_parser(
        "seed-demo-products", help="Crea productos de prueba (solo en local)"
    )
    demo.add_argument("count", type=int)
    args = parser.parse_args(argv)
    if args.command == "reset-password":
        return _reset_password(args.username)
    if args.command == "seed-demo-products":
        return _seed_demo_products(args.count)
    return 2


if __name__ == "__main__":
    sys.exit(main())
