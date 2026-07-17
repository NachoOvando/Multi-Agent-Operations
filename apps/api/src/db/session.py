"""Engine y sesión de SQLAlchemy para Postgres.

Todo es lazy (nada se conecta ni lee DATABASE_URL hasta que se llama get_session())
para que importar este módulo no falle en contextos sin DB configurada (tests,
type-checking, etc.).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. Definila como variable de entorno "
            "(nunca hardcodeada en el código)."
        )
    return create_engine(database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    """Sesión de DB de corta duración. Uso: `with get_session() as session: ...`."""
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
