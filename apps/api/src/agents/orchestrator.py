"""Orquestador: dispatcher determinístico de consultas al agente especialista
correspondiente.

Es el ÚNICO componente (junto con services/cross_domain_reads.py, su única
excepción documentada) que conoce los 3 Domain explícitamente — ver CLAUDE.md.

Por qué NO es un LlmAgent de Google ADK con sub_agents/transferencia
automática: el ruteo es 100% determinístico, porque ROLE_DOMAIN
(permissions_service.py) es una función fija 1:1 rol->dominio. No hay
ambigüedad de intención que un LLM deba resolver — usar un LLM para esa
decisión agregaría latencia, costo y una superficie de no-determinismo /
inyección de prompt sin ganar nada.

El tool-set final de cada agente especialista es ESTÁTICO (fijo por Domain,
no varía por operador individual) porque CROSS_DOMAIN_READERS también es
fijo — por eso los 3 LlmAgent + Runner de ADK se pre-construyen una sola vez
al boot (ver _build_runners), no por request. El trabajo por request se
reduce a: resolver el dominio del operador -> elegir el Runner ya construido
-> invocarlo. El chequeo de permisos real sigue ocurriendo dentro de cada
tool (fail-closed, sin cambios respecto a assert_can_perform/assert_can_read).

Wiring validado por instalación real de google-adk==2.5.0 en esta sesión
(ver docs/context/decisiones.md): `DatabaseSessionService(db_url=...)`,
`Runner(agent=, app_name=, session_service=, auto_create_session=True)`,
`Runner.run_async(user_id=, session_id=, new_message=types.Content(...))`
(async generator de `Event`). `auto_create_session=True` evita tener que
crear la sesión de ADK a mano antes de cada consulta.
"""

from __future__ import annotations

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from sqlalchemy.orm import Session

from apps.api.src.agents.almacen.agent import build_agent as build_almacen_agent
from apps.api.src.agents.compras.agent import build_agent as build_compras_agent
from apps.api.src.agents.planificacion.agent import (
    build_agent as build_planificacion_agent,
)
from apps.api.src.db.session import get_database_url
from apps.api.src.services import cross_domain_reads
from apps.api.src.services.permissions_service import (
    CROSS_DOMAIN_READERS,
    Domain,
    get_operator_permissions,
)

_APP_NAME = "agentes-operativos"

_BUILDERS = {
    Domain.ALMACEN: build_almacen_agent,
    Domain.COMPRAS: build_compras_agent,
    Domain.PLANIFICACION: build_planificacion_agent,
}

# Tools de lectura cruzada disponibles por dominio LEÍDO (ver
# services/cross_domain_reads.py) — la única fuente permitida de tools
# cruzados. El orquestador las inyecta en el agente del dominio LECTOR según
# CROSS_DOMAIN_READERS; ningún agent.py de dominio las referencia por su cuenta.
_CROSS_DOMAIN_TOOLS: dict[Domain, list] = {
    Domain.ALMACEN: [cross_domain_reads.leer_stock_para],
    Domain.PLANIFICACION: [cross_domain_reads.leer_necesidades_para],
}

_RUNNERS_BY_DOMAIN: dict[Domain, Runner] = {}


def _extra_tools_for(domain: Domain) -> list:
    """Tools de lectura cruzada que le corresponden a `domain` como LECTOR
    (no como dueño de los datos) — resuelto a partir de CROSS_DOMAIN_READERS.
    """
    extra: list = []
    for target_domain, readers in CROSS_DOMAIN_READERS.items():
        if domain in readers:
            extra.extend(_CROSS_DOMAIN_TOOLS.get(target_domain, []))
    return extra


def _build_runners() -> dict[Domain, Runner]:
    """Construye (una sola vez, al boot) el LlmAgent + Runner de ADK de cada
    dominio, con su tool-set final ya ensamblado: tools propias del dominio
    (agents/<dominio>/agent.py) + tools de lectura cruzada inyectadas según
    CROSS_DOMAIN_READERS.
    """
    database_url = get_database_url()  # ya normalizada (postgresql+psycopg://)
    session_service = DatabaseSessionService(db_url=database_url)

    runners: dict[Domain, Runner] = {}
    for domain, builder in _BUILDERS.items():
        agent = builder(extra_tools=_extra_tools_for(domain))
        runners[domain] = Runner(
            agent=agent,
            app_name=_APP_NAME,
            session_service=session_service,
            auto_create_session=True,
        )
    return runners


def get_runner_for_domain(domain: Domain) -> Runner:
    """Devuelve el Runner de ADK pre-construido para `domain` (lazy, cacheado)."""
    if not _RUNNERS_BY_DOMAIN:
        _RUNNERS_BY_DOMAIN.update(_build_runners())
    return _RUNNERS_BY_DOMAIN[domain]


async def handle_query(operator_id: str, query: str, session: Session) -> str:
    """Punto de entrada del orquestador: resuelve el dominio del operador y
    despacha la consulta al Runner correspondiente.

    No es un LlmAgent — ver docstring del módulo. El chequeo de permisos para
    ACCIONES/lectura cruzada específicas sigue ocurriendo dentro de cada tool
    invocado por el agente (vía tool_context.user_id, ver agents/almacen/
    agent.py); esta función solo decide QUÉ agente atiende la consulta.

    TODO: estrategia de `session_id` de ADK todavía no decidida — hoy se usa
    una sesión persistente por operador (operator_id como session_id).
    Revisar cuando exista un modelo real de conversaciones.
    """
    permissions = get_operator_permissions(operator_id, session)
    runner = get_runner_for_domain(permissions.domain)

    adk_session_id = operator_id  # TODO: ver nota de session_id arriba.

    response_parts: list[str] = []
    async for event in runner.run_async(
        user_id=operator_id,
        session_id=adk_session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=query)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_parts.append(part.text)

    return "".join(response_parts)
