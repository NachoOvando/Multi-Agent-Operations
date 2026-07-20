"""Consulta de permisos por operador: qué dominios y acciones tiene habilitados.

Fuente de verdad para los 3 agentes. Mientras Auth.js no exista, el rol de cada
operador se lee de la tabla `operators` en Postgres (ver db/models.py). Cuando
Auth.js esté listo, el único punto a adaptar es de dónde sale `operator_id` —
la interfaz pública de este módulo (operator_id -> OperatorPermissions) no cambia.

Regla dura de CLAUDE.md: ningún tool nuevo se agrega a un agente sin verificar
este archivo. `DOMAIN_ACTIONS` es la única fuente de verdad de qué acciones
existen por dominio — un tool cuya acción no está listada acá es rechazado por
`assert_can_perform`, aunque el operador tenga el rol correcto.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session

from apps.api.src.db.models import Operator


class Domain(str, Enum):
    COMPRAS = "compras"
    ALMACEN = "almacen"
    PLANIFICACION = "planificacion"


class Role(str, Enum):
    COMPRADOR = "comprador"
    ALMACENERO = "almacenero"
    PLANIFICADOR = "planificador"


# Un rol mapea a exactamente un dominio (modelo fijo, sin roles cruzados por usuario).
ROLE_DOMAIN: dict[Role, Domain] = {
    Role.COMPRADOR: Domain.COMPRAS,
    Role.ALMACENERO: Domain.ALMACEN,
    Role.PLANIFICADOR: Domain.PLANIFICACION,
}

# Acciones válidas por dominio: cualquier operador con el rol de ese dominio
# tiene TODAS estas acciones habilitadas (no hay permisos por acción dentro
# del rol). Completar cada set a medida que se implementen los tools de
# tools.py de ese dominio — nunca al revés.
DOMAIN_ACTIONS: dict[Domain, frozenset[str]] = {
    Domain.ALMACEN: frozenset({"consultar_stock", "registrar_movimiento"}),
    Domain.COMPRAS: frozenset({"consultar_precios_proveedor", "registrar_orden_compra"}),
    Domain.PLANIFICACION: frozenset({"consultar_necesidades", "registrar_necesidad"}),
}

# Lectura cruzada de SOLO LECTURA entre dominios — eje de permiso distinto de
# DOMAIN_ACTIONS/assert_can_perform (que gobierna acciones/escritura dentro del
# propio dominio del operador). Clave = dominio siendo LEÍDO; valor = qué
# dominios (operadores de esos dominios) tienen permiso de leerlo. Nunca
# habilita escritura — ver services/cross_domain_reads.py, la única excepción
# permitida a "el orquestador es el único componente que conoce los 3 dominios"
# (CLAUDE.md). Completar solo cuando exista una necesidad de negocio real,
# nunca de forma especulativa.
CROSS_DOMAIN_READERS: dict[Domain, frozenset[Domain]] = {
    Domain.ALMACEN: frozenset({Domain.COMPRAS}),
    Domain.PLANIFICACION: frozenset({Domain.COMPRAS}),
    Domain.COMPRAS: frozenset(),
}


class UnknownOperatorError(Exception):
    """El operator_id no existe en la tabla operators."""


class PermissionDeniedError(Exception):
    """El operador no tiene permiso para la acción solicitada."""


@dataclass(frozen=True)
class OperatorPermissions:
    operator_id: str
    role: Role
    domain: Domain
    actions: frozenset[str]


def get_operator_permissions(operator_id: str, session: Session) -> OperatorPermissions:
    """Devuelve el dominio y las acciones permitidas para un operador.

    Fail closed: lanza UnknownOperatorError si el operator_id no existe. Nunca
    se asume un rol por default para un operador desconocido.
    """
    operator = session.get(Operator, operator_id)
    if operator is None:
        raise UnknownOperatorError(f"operator_id desconocido: {operator_id}")

    role = Role(operator.role)
    domain = ROLE_DOMAIN[role]
    actions = DOMAIN_ACTIONS[domain]

    return OperatorPermissions(
        operator_id=operator_id,
        role=role,
        domain=domain,
        actions=actions,
    )


def assert_can_perform(operator_id: str, domain: Domain, action: str, session: Session) -> None:
    """Verifica que el operador pueda ejecutar `action` en `domain`.

    Esta es la función que debe llamar CADA tool (no solo el orquestador) antes
    de ejecutar su lógica — ver CLAUDE.md, regla dura sobre logging/permisos.
    Lanza PermissionDeniedError si el operador no corresponde al dominio o si
    la acción no está habilitada.
    """
    permissions = get_operator_permissions(operator_id, session)

    if permissions.domain != domain:
        raise PermissionDeniedError(
            f"operador {operator_id} (rol {permissions.role.value}) no tiene "
            f"acceso al dominio {domain.value}"
        )

    if action not in permissions.actions:
        raise PermissionDeniedError(
            f"operador {operator_id} no tiene la acción '{action}' habilitada "
            f"en {domain.value}"
        )


def assert_can_read(operator_id: str, target_domain: Domain, session: Session) -> None:
    """Verifica que el operador pueda LEER datos de `target_domain` (solo lectura).

    Se cumple si el operador es del propio `target_domain` (leer lo suyo
    siempre está permitido) o si su dominio está en
    CROSS_DOMAIN_READERS[target_domain]. Nunca habilita escritura — para eso
    sigue existiendo exclusivamente `assert_can_perform`.

    Esta función es la única que debe llamar `services/cross_domain_reads.py`
    (la única excepción documentada a "el orquestador es el único componente
    que conoce los 3 dominios" — ver CLAUDE.md). Ningún `tools.py` de dominio
    debe llamarla directamente para leer otro dominio.
    """
    permissions = get_operator_permissions(operator_id, session)

    if permissions.domain == target_domain:
        return

    if permissions.domain not in CROSS_DOMAIN_READERS.get(target_domain, frozenset()):
        raise PermissionDeniedError(
            f"operador {operator_id} (dominio {permissions.domain.value}) no "
            f"tiene permiso de lectura cruzada sobre {target_domain.value}"
        )
