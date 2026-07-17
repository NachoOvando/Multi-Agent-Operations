"""Punto único de lectura/escritura de stock.

Fuente única de "cómo se lee/escribe stock" — tanto `agents/almacen/tools.py`
(tool propio del dominio) como `services/cross_domain_reads.py` (lectura
cruzada de Compras) delegan acá. Nunca duplicar esta lógica en otro lugar.

El schema real (tabla, columnas: material_code, quantity, location, etc.) se
define al final, después de cerrar el resto del diseño. Cada carga de Excel de
stock es una foto completa que reemplaza el stock vigente (full-replace), no
un log acumulativo — ver docs/architecture.md.

Este módulo NO conoce `Domain` ni `permissions_service` — es acceso a datos
puro, sin lógica de permisos. El permission-check vive en quien lo llama
(`almacen/tools.py` vía `assert_can_perform`, `cross_domain_reads.py` vía
`assert_can_read`).
"""

from __future__ import annotations

from sqlalchemy.orm import Session


def get_stock(material_code: str, session: Session) -> dict:
    """Devuelve el stock actual de un material.

    TODO: implementar contra la tabla real de stock una vez definido el
    schema (pendiente hasta cerrar el diseño de ingesta de Excel).
    """
    raise NotImplementedError(
        "Falta definir el modelo de datos de stock antes de implementar esta consulta."
    )


def upsert_stock_snapshot(rows: list[dict], session: Session) -> None:
    """Reemplaza el stock vigente por una foto completa (full-replace).

    TODO: implementar el upsert real una vez definido el schema de la tabla
    de stock y el formato de columnas del Excel de origen.
    """
    raise NotImplementedError(
        "Falta definir el modelo de datos de stock antes de implementar el reemplazo completo."
    )
