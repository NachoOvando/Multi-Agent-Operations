"""Configuración de Alembic para apps/api.

Los imports del proyecto son absolutos (`apps.api.src...`, ver CLAUDE.md /
db/session.py), lo que requiere que la raíz del repo esté en `sys.path`.
A diferencia de `uvicorn` (que agrega el CWD a `sys.path` en su propio CLI),
Alembic no lo hace — lo agregamos acá de forma explícita, calculando la raíz
en relación a este archivo (no al CWD), para que
`alembic -c apps/api/alembic.ini upgrade head` funcione igual desde la raíz
del repo (Railway) o desde `apps/api` (dev local).

La URL de conexión sale de `DATABASE_URL` vía
`db/session.py::get_database_url()` (normalizada, nunca hardcodeada acá) —
reusa la misma lógica que usa la app en runtime, no la duplica.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.api.src.db.models import Base  # noqa: E402
from apps.api.src.db.session import get_database_url  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera SQL sin conectarse a una DB real (`alembic upgrade head --sql`)."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones contra la DB real (`DATABASE_URL`)."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
