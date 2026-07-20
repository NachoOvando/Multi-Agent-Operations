"""Tools scoped al dominio de Compras. No cargar tools de otros dominios acá.

Cada tool valida el permiso del operador contra permissions_service.py ANTES
de tocar cualquier dato (regla dura de CLAUDE.md: los checks van en el tool,
no solo en el orquestador). Este archivo NUNCA referencia Domain.ALMACEN ni
Domain.PLANIFICACION — la lectura cruzada hacia esos dominios la inyecta el
orquestador vía services/cross_domain_reads.py, nunca desde acá.

TODO: el modelo de datos de precios de proveedor y órdenes de compra
(services/purchasing_queries.py) todavía no está definido. Las funciones de
abajo verifican permisos correctamente; la lectura/escritura real queda
pendiente hasta definir ese schema.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api.src.services import purchasing_queries
from apps.api.src.services.permissions_service import Domain, assert_can_perform


def consultar_precios_proveedor(operator_id: str, material_code: str, session: Session) -> dict:
    """Devuelve precio, proveedor, MOQ y lead time vigentes de un material.

    Requiere que el operador tenga la acción 'consultar_precios_proveedor'
    habilitada en el dominio Compras.
    """
    assert_can_perform(operator_id, Domain.COMPRAS, "consultar_precios_proveedor", session)
    return purchasing_queries.get_supplier_price(material_code, session)


def registrar_orden_compra(
    operator_id: str,
    material_code: str,
    quantity: float,
    supplier: str,
    session: Session,
) -> dict:
    """Registra una nueva orden de compra.

    Requiere que el operador tenga la acción 'registrar_orden_compra'
    habilitada en el dominio Compras.

    Regla dura de CLAUDE.md: toda acción que modifica datos debe loguearse
    con operator_id + rol + timestamp. Ese logging todavía no está
    implementado — hay que agregarlo (junto con el modelo de datos) antes de
    habilitar esta acción en producción.
    """
    assert_can_perform(operator_id, Domain.COMPRAS, "registrar_orden_compra", session)

    # TODO: loguear operator_id + rol + timestamp antes de mutar cualquier dato.
    return purchasing_queries.create_purchase_order(material_code, quantity, supplier, session)
