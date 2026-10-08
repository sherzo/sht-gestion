"""Comandos de soporte de la API (research R8).

Uso, desde backend/ y con DATABASE_URL apuntando a la base:

    uv run python -m app.cli reset-password <usuario>

Asigna una contraseña temporal (RF-45/FR-016a), cierra las sesiones del usuario y lo
registra en la auditoría como acción de sistema. Sirve para recuperar al único admin
que olvidó su contraseña (procedimiento en docs/despliegue.md).
"""

import argparse
import secrets
import sys

from sqlalchemy import select

from app.db.models import AppUser
from app.db.session import get_sessionmaker
from app.services.auth import normalize_username
from app.services.users import reset_password


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="app.cli", description="Comandos de soporte de SHT Gestión"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    reset = commands.add_parser("reset-password", help="Asigna una contraseña temporal")
    reset.add_argument("username")
    args = parser.parse_args(argv)
    if args.command == "reset-password":
        return _reset_password(args.username)
    return 2


if __name__ == "__main__":
    sys.exit(main())
