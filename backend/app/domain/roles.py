"""Roles del sistema (PRD §4, FR-009): cada usuario tiene exactamente uno."""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    SELLER = "seller"
    WAREHOUSE = "warehouse"
