"""Agente especialista de Almacén (Google ADK).

TODO: construir acá el LlmAgent real (modelo Claude vía google.adk.models.
lite_llm.LiteLlm, tools de agents/almacen/tools.py, prompt de
agents/almacen/prompts.py) una vez que google-adk esté instalado. El
orquestador (agents/orchestrator.py) invoca build_agent() al boot para
pre-construir el Runner de este dominio.
"""

from __future__ import annotations


def build_agent(extra_tools: list | None = None) -> object:
    """Construye el LlmAgent de Almacén.

    `extra_tools` queda reservado para tools de lectura cruzada que el
    orquestador pudiera inyectar en el futuro (hoy Almacén no figura como
    lector en ningún CROSS_DOMAIN_READERS de otro dominio).

    TODO: implementar con google.adk.agents.Agent una vez instalado.
    """
    raise NotImplementedError("Falta instalar google-adk para construir el LlmAgent real.")
