"""Agente especialista de Planificación (Google ADK).

Wiring real — ver docstring de agents/almacen/agent.py para el patrón
completo (validado por instalación real de google-adk==2.5.0 en esta
sesión).
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext

from apps.api.src.agents.planificacion import prompts, tools
from apps.api.src.db.session import get_session

_MODEL = "claude-sonnet-5"


def _consultar_necesidades(tool_context: ToolContext, material_code: str | None = None) -> list:
    """Wrapper ADK de tools.consultar_necesidades."""
    with get_session() as session:
        return tools.consultar_necesidades(tool_context.user_id, material_code, session)


def _registrar_necesidad(
    tool_context: ToolContext,
    material_code: str,
    quantity: float,
    required_date: str,
    work_order: str,
) -> dict:
    """Wrapper ADK de tools.registrar_necesidad."""
    with get_session() as session:
        return tools.registrar_necesidad(
            tool_context.user_id, material_code, quantity, required_date, work_order, session
        )


def build_agent(extra_tools: list | None = None) -> Agent:
    """Construye el LlmAgent de Planificación.

    `extra_tools` queda reservado para una futura necesidad de lectura
    cruzada hacia Planificación (hoy no está habilitada en
    CROSS_DOMAIN_READERS de ningún otro dominio).
    """
    return Agent(
        name="planificacion_agent",
        model=LiteLlm(model=f"anthropic/{_MODEL}"),
        instruction=prompts.INSTRUCTION,
        tools=[_consultar_necesidades, _registrar_necesidad, *(extra_tools or [])],
    )
