"""agrega campos de auth a operators: username (unique) + password_hash

Slice 1 de auth (JWT propio emitido por FastAPI): cada operador ahora
necesita username + password_hash para poder loguearse. No hay backfill de
password_hash acá a propósito — no existe una password "real" para
inventarle a filas preexistentes, y esta tabla es interina/dev (ver
docstring de db/models.py). Si hay filas preexistentes en el entorno donde
se corre esta migración, hay que provisionarlas con
`scripts/create_operator.py` (borrar y recrear) antes de aplicar upgrade.

Revision ID: 0002_operator_auth_fields
Revises: 0001_baseline_operators
Create Date: 2026-07-23
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_operator_auth_fields"
down_revision: Union[str, None] = "0001_baseline_operators"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("operators", sa.Column("username", sa.String(), nullable=False))
    op.add_column("operators", sa.Column("password_hash", sa.String(), nullable=False))
    op.create_index("ix_operators_username", "operators", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_operators_username", table_name="operators")
    op.drop_column("operators", "password_hash")
    op.drop_column("operators", "username")
