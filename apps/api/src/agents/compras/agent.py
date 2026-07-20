"""Agente especialista de Compras (Google ADK).

Wiring real — ver docstring de agents/almacen/agent.py para el patrón
completo (validado por instalación real de google-adk==2.5.0 en esta
sesión). Este archivo NUNCA debe importar services/cross_domain_reads.py ni
referenciar Domain.ALMACEN/Domain.PLANIFICACION directamente — la única
fuente de tools de lectura cruzada es el `extra_tools` que recibe
build_agent, ensamblado por el orquestador (agents/orchestrator.py) según
CROSS_DOMAIN_READERS (permissions_service.py).
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext

from apps.api.src.agents.compras import prompts, tools
from apps.api.src.db.session import get_session

_MODEL = "claude-sonnet-5"


def _consultar_precios_proveedor(tool_context: ToolContext, material_code: str) -> dict:
    """Wrapper ADK de tools.consultar_precios_proveedor."""
    with get_session() as session:
        return tools.consultar_precios_proveedor(tool_context.user_id, material_code, session)


def _registrar_orden_compra(
    tool_context: ToolContext, material_code: str, quantity: float, supplier: str
) -> dict:
    """Wrapper ADK de tools.registrar_orden_compra."""
    with get_session() as session:
        return tools.registrar_orden_compra(
            tool_context.user_id, material_code, quantity, supplier, session
        )


def build_agent(extra_tools: list | None = None) -> Agent:
    """Construye el LlmAgent de Compras.

    `extra_tools`: tools de lectura cruzada (leer_stock_para,
    leer_necesidades_para de services/cross_domain_reads.py) inyectadas por
    el orquestador. Este módulo no las conoce por nombre ni por dominio de
    origen — solo las recibe y las agrega a su tool-set.
    """
    return Agent(
        name="compras_agent",
        model=LiteLlm(model=f"anthropic/{_MODEL}"),
        instruction=prompts.INSTRUCTION,
        tools=[_consultar_precios_proveedor, _registrar_orden_compra, *(extra_tools or [])],
    )
