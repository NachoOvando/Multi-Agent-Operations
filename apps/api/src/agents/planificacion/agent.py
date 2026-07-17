"""Agente especialista de Planificación (Google ADK).

TODO: construir acá el LlmAgent real (modelo Claude vía google.adk.models.
lite_llm.LiteLlm, tools de agents/planificacion/tools.py, prompt de
agents/planificacion/prompts.py) una vez que google-adk esté instalado.
"""

from __future__ import annotations


def build_agent(extra_tools: list | None = None) -> object:
    """Construye el LlmAgent de Planificación.

    `extra_tools` queda reservado para una futura necesidad de lectura
    cruzada hacia Planificación (hoy no está habilitada en
    CROSS_DOMAIN_READERS de ningún otro dominio).

    TODO: implementar con google.adk.agents.Agent una vez instalado.
    """
    raise NotImplementedError("Falta instalar google-adk para construir el LlmAgent real.")
