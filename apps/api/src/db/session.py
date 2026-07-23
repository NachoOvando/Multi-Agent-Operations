"""Engine y sesión de SQLAlchemy para Postgres.

Todo es lazy (nada se conecta ni lee DATABASE_URL hasta que se llama get_session())
para que importar este módulo no falle en contextos sin DB configurada (tests,
type-checking, etc.).

IMPORTANTE — formato de DATABASE_URL (validado en esta sesión instalando
google-adk de verdad, ver docs/context/decisiones.md): usar el prefijo
`postgresql+psycopg://` (psycopg v3, ya en requirements.txt), NUNCA el
genérico `postgresql://` a secas — ese default apunta a `psycopg2`, que no
está instalado en este proyecto. El mismo motivo aplica en el otro sentido a
`google.adk.sessions.DatabaseSessionService`, que arma un engine ASYNC desde
esta misma URL (agents/orchestrator.py) — psycopg v3 soporta sync y async
desde el mismo driver, así que una única URL con este prefijo sirve para
ambos usos sin duplicar configuración.

Railway (y otros proveedores) suelen entregar `DATABASE_URL` con el prefijo
genérico `postgresql://` — `get_database_url()` normaliza defensivamente ese
caso a `postgresql+psycopg://`. Es la ÚNICA función que debe leer
`DATABASE_URL` del entorno en todo el backend (`get_engine()` de acá,
`agents/orchestrator.py::_build_runners` y `alembic/env.py` la reusan) para
no duplicar esa normalización en cada punto de entrada.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_LEGACY_PREFIX = "postgresql://"
_REQUIRED_PREFIX = "postgresql+psycopg://"


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith(_LEGACY_PREFIX):
        return _REQUIRED_PREFIX + database_url[len(_LEGACY_PREFIX) :]
    return database_url


def get_database_url() -> str:
    """Devuelve `DATABASE_URL` ya normalizada (prefijo `postgresql+psycopg://`).

    Fail-closed: nunca inventa un default — si la variable no está definida,
    levanta `RuntimeError` explícito en vez de dejar que `create_engine`
    falle más abajo con un error menos claro.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. Definila como variable de entorno "
            "(nunca hardcodeada en el código)."
        )
    return _normalize_database_url(database_url)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(get_database_url(), pool_pre_ping=True)


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


def get_db() -> Iterator[Session]:
    """Generador compatible con `Depends()` de FastAPI (`Depends(get_db)`).

    Mismo ciclo de vida por-request que `get_session()` (sesión de corta
    duración, se cierra siempre al final) pero con la firma que FastAPI
    espera para inyectarlo como dependencia — no reemplaza `get_session()`,
    que sigue siendo el punto de entrada para código que no corre dentro de
    un request (scripts, tests, etc.).
    """
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
