"""Punto único de lectura/escritura de datos propios de Compras (precios de
proveedor, órdenes de compra).

A diferencia de stock_queries.py/production_queries.py, este módulo no se
usa desde services/cross_domain_reads.py — hoy ningún otro dominio tiene
permiso de lectura cruzada sobre Compras (CROSS_DOMAIN_READERS[Domain.COMPRAS]
está vacío en permissions_service.py). Si eso cambiara, la lectura cruzada
debería delegar acá, igual que stock_queries.py, nunca duplicar la lógica.

El schema real (tabla de precios: material_code, supplier, unit_price,
moq, lead_time_days; tabla de OCs: material_code, quantity, supplier,
expected_date, status) se define al final, después de cerrar el resto del
diseño — ver docs/architecture.md.

Este módulo NO conoce `Domain` ni `permissions_service` — acceso a datos
puro, sin lógica de permisos.
"""

from __future__ import annotations

from sqlalchemy.orm import Session


def get_supplier_price(material_code: str, session: Session) -> dict:
    """Devuelve el precio/proveedor/MOQ/lead time vigente de un material.

    TODO: implementar contra la tabla real de precios de proveedor una vez
    definido el schema.
    """
    raise NotImplementedError(
        "Falta definir el modelo de datos de precios de proveedor antes de "
        "implementar esta consulta."
    )


def create_purchase_order(
    material_code: str,
    quantity: float,
    supplier: str,
    session: Session,
) -> dict:
    """Crea una nueva orden de compra.

    TODO: implementar contra la tabla real de órdenes de compra una vez
    definido el schema.
    """
    raise NotImplementedError(
        "Falta definir el modelo de datos de órdenes de compra antes de "
        "implementar el registro real."
    )
