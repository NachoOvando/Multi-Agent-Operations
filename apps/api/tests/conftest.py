"""Fixtures compartidas de la suite de tests del backend.

Corre contra SQLite en memoria (no contra Postgres): los modelos tocados por
este slice (`db/models.py::Operator`) son SQLAlchemy 2.0 estándar, sin
features específicas de Postgres (JSONB, etc.), así que `Base.metadata`
crea el schema igual en SQLite. Esto evita depender de Docker/Postgres real
en el sandbox de CI/dev — si en un slice futuro se agregan columnas
Postgres-only a alguna tabla cubierta por tests, esas suites puntuales van a
necesitar Postgres real (docker-compose.yml) en vez de este fixture.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.src.db.models import Base, Operator
from apps.api.src.services.auth_service import hash_password


@pytest.fixture()
def session() -> Iterator[Session]:
    """Engine SQLite en memoria, schema creado desde `Base.metadata`.

    Cada test recibe una sesión nueva sobre un engine nuevo (no compartido
    entre tests) para que no haya estado que se filtre de un test a otro —
    más simple y más aislado que rollback sobre un engine compartido, y
    SQLite en memoria es lo bastante barato como para no importar el costo.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.rollback()
        db_session.close()
        engine.dispose()


@pytest.fixture()
def operator_password() -> str:
    """Password en texto plano conocida, para reusar en los tests de auth."""
    return "correct-horse-battery-staple"


@pytest.fixture()
def operator(session: Session, operator_password: str) -> Operator:
    """Inserta un Operator de prueba (rol comprador) con password hasheado."""
    op = Operator(
        operator_id="op-test-1",
        username="comprador.test",
        password_hash=hash_password(operator_password),
        role="comprador",
    )
    session.add(op)
    session.commit()
    return op
