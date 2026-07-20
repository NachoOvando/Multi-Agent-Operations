"""Tools scoped al dominio de Planificación. No cargar tools de otros dominios acá.

Cada tool valida el permiso del operador contra permissions_service.py ANTES
de tocar cualquier dato (regla dura de CLAUDE.md: los checks van en el tool,
no solo en el orquestador).

TODO: el modelo de datos de necesidades de producción
(services/production_queries.py) todavía no está definido. Las funciones de
abajo verifican permisos correctamente; la lectura/escritura real queda
pendiente hasta definir ese schema.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api.src.services import production_queries
from apps.api.src.services.permissions_service import Domain, assert_can_perform


def consultar_necesidades(
    operator_id: str,
    material_code: str | None,
    session: Session,
) -> list[dict]:
    """Devuelve las necesidades de producción vigentes (todas o de un material).

    Requiere que el operador tenga la acción 'consultar_necesidades'
    habilitada en el dominio Planificación. Delega en
    services/production_queries.py::get_requirements — la misma fuente que
    usa la lectura cruzada de Compras — para no duplicar la lógica de "cómo
    se leen necesidades" en dos lugares.
    """
    assert_can_perform(operator_id, Domain.PLANIFICACION, "consultar_necesidades", session)
    return production_queries.get_requirements(material_code, session)


def registrar_necesidad(
    operator_id: str,
    material_code: str,
    quantity: float,
    required_date: str,
    work_order: str,
    session: Session,
) -> dict:
    """Registra una nueva necesidad de producción.

    Requiere que el operador tenga la acción 'registrar_necesidad' habilitada
    en el dominio Planificación.

    Regla dura de CLAUDE.md: toda acción que modifica datos debe loguearse
    con operator_id + rol + timestamp. Ese logging todavía no está
    implementado — hay que agregarlo (junto con el modelo de datos) antes de
    habilitar esta acción en producción.
    """
    assert_can_perform(operator_id, Domain.PLANIFICACION, "registrar_necesidad", session)

    # TODO: loguear operator_id + rol + timestamp antes de mutar cualquier dato.
    return production_queries.create_requirement(
        material_code, quantity, required_date, work_order, session
    )
