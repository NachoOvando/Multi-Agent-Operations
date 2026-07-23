"""Smoke tests de `services/permissions_service.py`.

El archivo no cambió en este slice (solo se agregó auth encima), así que no
hace falta cobertura exhaustiva acá — el objetivo es confirmar que el
contrato que ya usan los 3 agentes (`get_operator_permissions`,
`assert_can_perform`, `assert_can_read`) sigue funcionando igual, no
re-testear cada combinación de `DOMAIN_ACTIONS`/`CROSS_DOMAIN_READERS`.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from apps.api.src.db.models import Operator
from apps.api.src.services.auth_service import hash_password
from apps.api.src.services.permissions_service import (
    Domain,
    PermissionDeniedError,
    Role,
    UnknownOperatorError,
    assert_can_perform,
    assert_can_read,
    get_operator_permissions,
)


@pytest.fixture()
def almacenero(session: Session) -> Operator:
    op = Operator(
        operator_id="op-almacen-1",
        username="almacenero.test",
        password_hash=hash_password("cualquier-password"),
        role=Role.ALMACENERO.value,
    )
    session.add(op)
    session.commit()
    return op


@pytest.fixture()
def planificador(session: Session) -> Operator:
    op = Operator(
        operator_id="op-planif-1",
        username="planificador.test",
        password_hash=hash_password("cualquier-password"),
        role=Role.PLANIFICADOR.value,
    )
    session.add(op)
    session.commit()
    return op


# --- get_operator_permissions ---------------------------------------------


def test_get_operator_permissions_returns_correct_domain(
    session: Session, operator: Operator
) -> None:
    permissions = get_operator_permissions(operator.operator_id, session)

    assert permissions.operator_id == operator.operator_id
    assert permissions.role == Role.COMPRADOR
    assert permissions.domain == Domain.COMPRAS
    assert "registrar_orden_compra" in permissions.actions


def test_get_operator_permissions_unknown_operator_raises(session: Session) -> None:
    with pytest.raises(UnknownOperatorError):
        get_operator_permissions("operator-id-que-no-existe", session)


# --- assert_can_perform ----------------------------------------------------


def test_assert_can_perform_allows_action_in_own_domain(
    session: Session, operator: Operator
) -> None:
    # No debe lanzar.
    assert_can_perform(operator.operator_id, Domain.COMPRAS, "registrar_orden_compra", session)


def test_assert_can_perform_rejects_action_from_other_domain(
    session: Session, operator: Operator
) -> None:
    with pytest.raises(PermissionDeniedError):
        assert_can_perform(operator.operator_id, Domain.ALMACEN, "registrar_movimiento", session)


def test_assert_can_perform_rejects_unknown_action_in_own_domain(
    session: Session, operator: Operator
) -> None:
    with pytest.raises(PermissionDeniedError):
        assert_can_perform(operator.operator_id, Domain.COMPRAS, "accion_inexistente", session)


# --- assert_can_read --------------------------------------------------------


def test_assert_can_read_allows_own_domain(session: Session, operator: Operator) -> None:
    # No debe lanzar: un comprador siempre puede leer su propio dominio.
    assert_can_read(operator.operator_id, Domain.COMPRAS, session)


def test_assert_can_read_allows_authorized_cross_domain_read(
    session: Session, operator: Operator
) -> None:
    # CROSS_DOMAIN_READERS[ALMACEN] incluye COMPRAS -> un comprador puede
    # leer datos de almacén. No debe lanzar.
    assert_can_read(operator.operator_id, Domain.ALMACEN, session)
    assert_can_read(operator.operator_id, Domain.PLANIFICACION, session)


def test_assert_can_read_rejects_unauthorized_cross_domain_read(
    session: Session, almacenero: Operator
) -> None:
    # CROSS_DOMAIN_READERS[COMPRAS] está vacío -> ningún otro dominio puede
    # leer compras, ni siquiera almacén.
    with pytest.raises(PermissionDeniedError):
        assert_can_read(almacenero.operator_id, Domain.COMPRAS, session)


def test_assert_can_read_rejects_cross_domain_not_listed(
    session: Session, almacenero: Operator
) -> None:
    # CROSS_DOMAIN_READERS[PLANIFICACION] solo incluye COMPRAS -> un
    # almacenero no puede leer planificación.
    with pytest.raises(PermissionDeniedError):
        assert_can_read(almacenero.operator_id, Domain.PLANIFICACION, session)
