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
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api.src.services.permissions_service import Domain, get_operator_permissions

# TODO: reemplazar `object` por el tipo real `google.adk.runners.Runner` una
# vez que google-adk esté instalado (ver apps/api/requirements.txt).
_RUNNERS_BY_DOMAIN: dict[Domain, object] = {}


def _build_runners() -> dict[Domain, object]:
    """Construye (una sola vez, al boot) el LlmAgent + Runner de ADK de cada
    dominio, con su tool-set final ya ensamblado: tools propias del dominio
    (agents/<dominio>/tools.py) + tools de lectura cruzada inyectadas según
    CROSS_DOMAIN_READERS (services/cross_domain_reads.py).

    TODO: implementar una vez que:
    - google-adk esté instalado (apps/api/requirements.txt).
    - cada agents/<dominio>/agent.py exponga un build_agent(...) real (hoy
      son stubs que lanzan NotImplementedError).
    - agents/compras/tools.py y agents/planificacion/tools.py tengan sus
      propias acciones definidas en DOMAIN_ACTIONS (hoy están vacíos).
    """
    raise NotImplementedError(
        "Falta instalar google-adk e implementar agent.py de cada dominio "
        "antes de construir los Runner reales."
    )


def get_runner_for_domain(domain: Domain) -> object:
    """Devuelve el Runner de ADK pre-construido para `domain` (lazy, cacheado)."""
    if not _RUNNERS_BY_DOMAIN:
        _RUNNERS_BY_DOMAIN.update(_build_runners())
    return _RUNNERS_BY_DOMAIN[domain]


async def handle_query(operator_id: str, query: str, session: Session) -> str:
    """Punto de entrada del orquestador: resuelve el dominio del operador y
    despacha la consulta al Runner correspondiente.

    No es un LlmAgent — ver docstring del módulo. El chequeo de permisos para
    ACCIONES específicas sigue ocurriendo dentro de cada tool invocado por el
    agente, no acá; esta función solo decide QUÉ agente atiende la consulta.
    """
    permissions = get_operator_permissions(operator_id, session)
    runner = get_runner_for_domain(permissions.domain)

    # TODO: invocar runner.run_async(...) (nombre exacto del método a
    # confirmar contra la versión instalada de google-adk) pasando
    # operator_id + query, y devolver/streamear la respuesta al router HTTP
    # (apps/api/src/routers/agents.py).
    raise NotImplementedError("Pendiente de wiring real con google-adk una vez instalado.")
