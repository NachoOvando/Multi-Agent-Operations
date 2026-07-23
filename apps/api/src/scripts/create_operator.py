"""CLI de administración para provisionar operadores.

No hay auto-registro (regla de negocio deliberada, ver plan de auth): un
admin corre este script a mano por cada cuenta nueva. Pide la password de
forma interactiva (nunca como argumento de línea de comandos, para que no
quede en el historial de shell ni en `ps`), la hashea con bcrypt
(`services/auth_service.hash_password`) y persiste el `Operator`.

Uso (desde la raíz del repo, con DATABASE_URL configurada):
    python -m apps.api.src.scripts.create_operator
"""

from __future__ import annotations

import getpass
import sys

from sqlalchemy.exc import IntegrityError

from apps.api.src.db.models import Operator
from apps.api.src.db.session import get_session
from apps.api.src.services.auth_service import hash_password
from apps.api.src.services.permissions_service import Role


def _prompt_non_empty(label: str) -> str:
    value = input(f"{label}: ").strip()
    while not value:
        print(f"{label} no puede estar vacío.", file=sys.stderr)
        value = input(f"{label}: ").strip()
    return value


def _prompt_role() -> str:
    valid_roles = [role.value for role in Role]
    while True:
        role = input(f"role ({'/'.join(valid_roles)}): ").strip()
        if role in valid_roles:
            return role
        print(f"Rol inválido. Opciones válidas: {', '.join(valid_roles)}", file=sys.stderr)


def _prompt_password() -> str | None:
    password = getpass.getpass("password: ")
    confirm = getpass.getpass("confirmar password: ")
    if not password or password != confirm:
        print("Las contraseñas no coinciden o están vacías.", file=sys.stderr)
        return None
    return password


def main() -> int:
    operator_id = _prompt_non_empty("operator_id")
    username = _prompt_non_empty("username")
    role = _prompt_role()

    password = _prompt_password()
    if password is None:
        return 1

    password_hash = hash_password(password)

    with get_session() as session:
        if session.get(Operator, operator_id) is not None:
            print(f"Ya existe un operador con operator_id={operator_id}.", file=sys.stderr)
            return 1

        operator = Operator(
            operator_id=operator_id,
            username=username,
            password_hash=password_hash,
            role=role,
        )
        session.add(operator)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            print(f"Ya existe un operador con username={username}.", file=sys.stderr)
            return 1

    print(f"Operador '{username}' ({operator_id}, rol={role}) creado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
