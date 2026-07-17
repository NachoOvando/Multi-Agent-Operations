"""Cálculo de cobertura y sugerencia de compra (MRP determinístico).

Módulo agnóstico de permisos y de dominios: NO importa `Domain` ni
`permissions_service`. Recibe datos ya leídos/autorizados (por
`services/cross_domain_reads.py`) y solo calcula — es matemática pura,
trivial de testear sin DB, sin LLM y sin permisos de por medio.

Mantener esta separación es intencional: el único módulo con lógica de
permisos cruzados entre dominios sigue siendo `cross_domain_reads.py`; este
archivo nunca debe adquirir esa responsabilidad.
"""

from __future__ import annotations


def compute_coverage(stock: dict, requirements: list[dict]) -> dict:
    """Calcula si el stock actual cubre las necesidades dadas, y desde cuándo no.

    TODO: implementar la lógica real (resta de stock proyectado vs.
    necesidades por fecha, considerando lead time y MOQ) una vez que
    stock_queries.py y production_queries.py devuelvan datos reales.
    """
    raise NotImplementedError(
        "Falta el schema de stock/necesidades antes de implementar el cálculo real."
    )
