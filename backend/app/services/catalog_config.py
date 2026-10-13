"""Configuración del inventario: unidades, categorías y atributos (RF-03 a RF-05;
FR-028 a FR-031).

El sistema se instala con las categorías, unidades y atributos de FR-028 (migración
0004). Nada de esto se borra: se desactiva.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AttributeDefinition, Category, Product, Unit


def list_units(db: Session, include_inactive: bool) -> list[Unit]:
    query = select(Unit).order_by(Unit.name)
    if not include_inactive:
        query = query.where(Unit.is_active.is_(True))
    return list(db.scalars(query))


def list_categories(
    db: Session, *, include_inactive: bool
) -> list[tuple[Category, list[AttributeDefinition], bool]]:
    """Categorías con sus atributos (solo los activos, salvo `include_inactive`) y si
    tienen productos."""
    query = select(Category).order_by(Category.name)
    if not include_inactive:
        query = query.where(Category.is_active.is_(True))
    categories = list(db.scalars(query))
    attributes_query = select(AttributeDefinition).order_by(
        AttributeDefinition.sort_order, AttributeDefinition.label
    )
    if not include_inactive:
        attributes_query = attributes_query.where(AttributeDefinition.is_active.is_(True))
    by_category: dict = {category.id: [] for category in categories}
    for attribute in db.scalars(attributes_query):
        if attribute.category_id in by_category:
            by_category[attribute.category_id].append(attribute)
    with_products = set(db.scalars(select(Product.category_id).distinct()))
    return [
        (category, by_category[category.id], category.id in with_products)
        for category in categories
    ]
