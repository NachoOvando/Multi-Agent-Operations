"""Agente especialista de Compras (Google ADK).

TODO: construir acá el LlmAgent real (modelo Claude vía google.adk.models.
lite_llm.LiteLlm, tools propias de agents/compras/tools.py + `extra_tools`
de lectura cruzada) una vez que google-adk esté instalado y
agents/compras/tools.py tenga sus propias acciones definidas.

Este archivo NUNCA debe importar services/cross_domain_reads.py ni
referenciar Domain.ALMACEN/Domain.PLANIFICACION directamente — la única
fuente de tools de lectura cruzada es el `extra_tools` que recibe
build_agent, ensamblado por el orquestador (agents/orchestrator.py) según
CROSS_DOMAIN_READERS (permissions_service.py).
"""

from __future__ import annotations


def build_agent(extra_tools: list | None = None) -> object:
    """Construye el LlmAgent de Compras.

    `extra_tools`: tools de lectura cruzada (leer_stock_para,
    leer_necesidades_para de services/cross_domain_reads.py) inyectadas por
    el orquestador. Este módulo no las conoce por nombre ni por dominio de
    origen — solo las recibe y las agrega a su tool-set.

    TODO: implementar con google.adk.agents.Agent una vez instalado.
    """
    raise NotImplementedError("Falta instalar google-adk para construir el LlmAgent real.")
