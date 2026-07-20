"""Agente especialista de Almacén (Google ADK).

Wiring real, validado por instalación e inspección directa de
`google-adk==2.5.0` en esta sesión (ver docs/context/decisiones.md):
- `Agent` es alias de `LlmAgent`; acepta `name`, `model`, `instruction`, `tools`.
- `model` acepta un `BaseLlm` — `LiteLlm(model="anthropic/<modelo>")` lo es.
- `tools` acepta callables planos directamente (ADK los envuelve).

Los tools de `agents/almacen/tools.py` son funciones puras y testeables:
reciben `operator_id` y `session` (SQLAlchemy) como parámetros explícitos.
ADK no puede inyectar eso directamente — lo que SÍ inyecta automáticamente es
un `tool_context: ToolContext` si el tool lo declara como parámetro. Por eso
este archivo define wrappers finos que:
1. Sacan `operator_id` de `tool_context.user_id` (ver orchestrator.py:
   `Runner.run_async(user_id=operator_id, ...)` es quien setea ese valor).
2. Abren una sesión de DB de corta duración por invocación
   (`db/session.py::get_session`).
3. Delegan en la función real de tools.py.

Esta es la única capa que traduce entre ADK y las funciones puras de
tools.py — tools.py en sí mismo no importa nada de google.adk.
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext

from apps.api.src.agents.almacen import prompts, tools
from apps.api.src.db.session import get_session

# Sonnet para agentes de área — ver docs/architecture.md. No probado contra
# una llamada real (requiere ANTHROPIC_API_KEY configurada en el entorno).
_MODEL = "claude-sonnet-5"


def _consultar_stock(tool_context: ToolContext, material_code: str) -> dict:
    """Wrapper ADK de tools.consultar_stock."""
    with get_session() as session:
        return tools.consultar_stock(tool_context.user_id, material_code, session)


def _registrar_movimiento(
    tool_context: ToolContext, material_code: str, quantity_delta: float
) -> dict:
    """Wrapper ADK de tools.registrar_movimiento."""
    with get_session() as session:
        return tools.registrar_movimiento(
            tool_context.user_id, material_code, quantity_delta, session
        )


def build_agent(extra_tools: list | None = None) -> Agent:
    """Construye el LlmAgent de Almacén.

    `extra_tools` queda reservado para tools de lectura cruzada que el
    orquestador pudiera inyectar en el futuro (hoy Almacén no figura como
    lector en ningún CROSS_DOMAIN_READERS de otro dominio).
    """
    return Agent(
        name="almacen_agent",
        model=LiteLlm(model=f"anthropic/{_MODEL}"),
        instruction=prompts.INSTRUCTION,
        tools=[_consultar_stock, _registrar_movimiento, *(extra_tools or [])],
    )
