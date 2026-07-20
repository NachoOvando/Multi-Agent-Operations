"""Punto único de lectura de necesidades de producción (Planificación).

Análogo a stock_queries.py: tanto el tool propio de Planificación como
`services/cross_domain_reads.py` (lectura cruzada de Compras) delegan acá.
Nunca duplicar esta lógica en otro lugar.

El schema real (tabla, columnas: material_code, quantity, required_date,
work_order, etc.) y la semántica de carga (¿reemplazo completo o
acumulación por orden de trabajo?) se definen al final, junto con el resto
de las tablas que vienen de Excel — ver docs/architecture.md.

Este módulo NO conoce `Domain` ni `permissions_service` — acceso a datos
puro, sin lógica de permisos.
"""

from __future__ import annotations

from sqlalchemy.orm import Session


def get_requirements(material_code: str | None, session: Session) -> list[dict]:
    """Devuelve las necesidades de producción vigentes (todas o de un material).

    TODO: implementar contra la tabla real de necesidades una vez definido
    el schema y la semántica de carga (reemplazo vs. acumulación).
    """
    raise NotImplementedError(
        "Falta definir el modelo de datos de necesidades de producción antes "
        "de implementar esta consulta."
    )


def create_requirement(
    material_code: str,
    quantity: float,
    required_date: str,
    work_order: str,
    session: Session,
) -> dict:
    """Registra una nueva necesidad de producción (una orden de trabajo puntual
    — distinto de la semántica de carga masiva por Excel, que se decide
    aparte, ver docstring del módulo).

    TODO: implementar contra la tabla real de necesidades una vez definido
    el schema.
    """
    raise NotImplementedError(
        "Falta definir el modelo de datos de necesidades de producción antes "
        "de implementar el registro real."
    )
