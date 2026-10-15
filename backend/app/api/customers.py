"""Búsqueda de clientes para la venta (RF-28/FR-019; research R11).

Contrato: specs/004-ventas-multimoneda/contracts/api.md. Los clientes nuevos se crean
dentro de la venta, por la cola de salida.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, require_roles
from app.api.sale_schemas import CustomerOut
from app.domain.roles import Role
from app.services import customers as customers_service

router = APIRouter(prefix="/customers", tags=["customers"])

AdminOrSeller = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.SELLER))]


@router.get("")
def search_customers(
    current: AdminOrSeller, db: DbSession, q: Annotated[str, Query(max_length=100)] = ""
) -> list[CustomerOut]:
    """Por documento (exacto) o por nombre (contiene, sin acentos); como máximo 20."""
    return [
        CustomerOut(
            id=customer.id,
            name=customer.name,
            document_id=customer.document_id,
            phone=customer.phone,
        )
        for customer in customers_service.search_customers(db, q)
    ]
