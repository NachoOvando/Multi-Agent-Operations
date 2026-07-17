"""Lectura de SOLO LECTURA entre dominios — única excepción a "el orquestador
es el único componente que conoce los 3 dominios" (CLAUDE.md).

Este módulo vive en `services/`, fuera de `agents/`, precisamente porque no
pertenece a ningún dominio: es el punto neutral donde el orquestador consigue
tools de lectura cruzada para inyectar en el agente especialista que las
necesite (ej. Compras necesita ver stock de Almacén y necesidades de
Planificación para poder sugerir una compra).

Reglas no negociables de este archivo:
- Cada función llama `assert_can_read` PRIMERO, antes de tocar cualquier dato.
- Ningún `tools.py` de dominio importa este módulo directamente — solo el
  orquestador lo hace, al ensamblar el tool-set de cada agente.
- PROHIBIDO cualquier verbo de mutación acá (registrar_, crear_, actualizar_,
  eliminar_): es exclusivamente de lectura. El guardian-arquitectura debe
  rechazar cualquier función de escritura agregada a este archivo.
- La lógica real de "cómo se lee stock/necesidades" no se duplica acá — se
  delega siempre a stock_queries.py / production_queries.py, que son la
  única fuente de esa lógica (reusada también por los tools propios de cada
  dominio).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api.src.services import production_queries, stock_queries
from apps.api.src.services.permissions_service import Domain, assert_can_read


def leer_stock_para(operator_id: str, material_code: str, session: Session) -> dict:
    """Lectura de solo lectura de stock (Almacén) para un operador de otro dominio.

    Requiere que el dominio del operador esté habilitado en
    CROSS_DOMAIN_READERS[Domain.ALMACEN] (ver permissions_service.py).
    """
    assert_can_read(operator_id, Domain.ALMACEN, session)
    return stock_queries.get_stock(material_code, session)


def leer_necesidades_para(
    operator_id: str,
    material_code: str | None,
    session: Session,
) -> list[dict]:
    """Lectura de solo lectura de necesidades de producción (Planificación).

    Requiere que el dominio del operador esté habilitado en
    CROSS_DOMAIN_READERS[Domain.PLANIFICACION] (ver permissions_service.py).
    """
    assert_can_read(operator_id, Domain.PLANIFICACION, session)
    return production_queries.get_requirements(material_code, session)
