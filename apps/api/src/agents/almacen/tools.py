"""Tools scoped al dominio de Almacén. No cargar tools de otros dominios acá.

Cada tool valida el permiso del operador contra permissions_service.py ANTES de
tocar cualquier dato — no alcanza con que el orquestador ya haya ruteado la
consulta hasta acá (regla dura de CLAUDE.md: los checks van en el tool, no solo
en el orquestador).

TODO: el modelo de datos de stock (tabla, columnas: material_code, quantity,
location, etc.) todavía no está definido. Las funciones de abajo verifican
permisos correctamente; la lectura/escritura real de stock queda pendiente
hasta definir ese schema con el resto del equipo.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api.src.services import stock_queries
from apps.api.src.services.permissions_service import Domain, assert_can_perform


def consultar_stock(operator_id: str, material_code: str, session: Session) -> dict:
    """Devuelve el stock actual de un material.

    Requiere que el operador tenga la acción 'consultar_stock' habilitada en
    el dominio Almacén. La lectura real delega en services/stock_queries.py —
    la misma fuente que usa la lectura cruzada de Compras — para no duplicar
    la lógica de "cómo se lee stock" en dos lugares.
    """
    assert_can_perform(operator_id, Domain.ALMACEN, "consultar_stock", session)
    return stock_queries.get_stock(material_code, session)


def registrar_movimiento(
    operator_id: str,
    material_code: str,
    quantity_delta: float,
    session: Session,
) -> dict:
    """Registra un movimiento de stock (ingreso o egreso de un material).

    Requiere que el operador tenga la acción 'registrar_movimiento' habilitada
    en el dominio Almacén.

    Regla dura de CLAUDE.md: toda acción que modifica datos debe loguearse con
    operator_id + rol + timestamp. Ese logging todavía no está implementado —
    hay que agregarlo (junto con el modelo de datos) antes de habilitar esta
    acción en producción.
    """
    assert_can_perform(operator_id, Domain.ALMACEN, "registrar_movimiento", session)

    # TODO: loguear operator_id + rol + timestamp antes de mutar cualquier dato.
    raise NotImplementedError(
        "Falta definir el modelo de datos de stock antes de implementar el "
        "registro real de movimientos."
    )
