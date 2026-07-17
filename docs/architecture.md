# Arquitectura: Agentes operativos (Compras / Almacén / Planificación)

## Objetivo del sistema

Cada operador (Compras, Almacén, Planificación) conversa con un agente de IA especializado en su dominio. Un orquestador rutea cada consulta al agente correspondiente según el rol del operador. El caso de uso central: el agente de Compras necesita saber cuánto stock hay (Almacén) y qué necesidades de producción existen (Planificación) para poder sugerir qué y cuándo comprar — sin que eso implique que un comprador pueda escribir datos de otro dominio.

## Stack

- **Frontend**: Next.js + TypeScript (`apps/web/`).
- **Backend**: Python, FastAPI (`apps/api/src/`).
- **Agentes**: Google ADK (`google-adk`), modelos Claude vía el wrapper `LiteLlm` de ADK (no Gemini).
- **Datos**: PostgreSQL. Excel/CSV es el formato de **entrada** (ingesta), nunca la fuente de verdad persistente — se normaliza a Postgres. El schema exacto de las tablas de negocio (stock, necesidades, precios) se define al final, después de cerrar el resto del diseño.

## Modelo de permisos (dos ejes ortogonales)

`apps/api/src/services/permissions_service.py` es la única fuente de verdad de permisos para los 3 agentes.

1. **`Role` → `Domain` (fijo, 1:1)**: cada operador tiene un rol que mapea a exactamente un dominio (comprador→compras, almacenero→almacen, planificador→planificacion). Sin roles cruzados por usuario. Mientras Auth.js no exista, el rol se lee de la tabla `operators` en Postgres (`db/models.py`); cuando Auth.js esté listo, solo cambia de dónde sale `operator_id` — esta interfaz no cambia.

2. **`assert_can_perform(operator_id, domain, action, session)`** — gobierna **acciones/escritura dentro del dominio propio** del operador. `DOMAIN_ACTIONS` es la única fuente de verdad de qué acciones existen por dominio; un tool cuya acción no está listada ahí es rechazado aunque el rol sea correcto. Este es el check que debe llamar CADA tool de acción (ej. `almacen/tools.py::registrar_movimiento`), no solo el orquestador.

3. **`assert_can_read(operator_id, target_domain, session)`** — gobierna **lectura de solo-lectura entre dominios**, un eje completamente separado. `CROSS_DOMAIN_READERS: dict[Domain, frozenset[Domain]]` declara qué dominios pueden leer (nunca escribir) los datos de otro. Hoy: Compras puede leer Almacén y Planificación. Se cumple trivialmente si el operador es del propio `target_domain`.

Estos dos ejes nunca se mezclan: `assert_can_perform` no habilita lectura cruzada, `assert_can_read` nunca habilita escritura.

## La única excepción a "el orquestador conoce los 3 dominios"

CLAUDE.md establece que el orquestador es el único componente que conoce los 3 dominios, y que ningún agente carga tools de otro dominio. Tal como está escrito, esto podría leerse como una prohibición total de que cualquier símbolo `Domain.X` aparezca fuera de `orchestrator.py` — pero permissions_service.py mismo ya conoce los 3 dominios, y el caso de uso central del proyecto requiere lectura cruzada. La lectura correcta:

- La regla prohíbe cargar tools de **acción/escritura** de otro dominio, y prohíbe que un `tools.py` de dominio (ej. `agents/compras/tools.py`) importe o razone sobre otro dominio directamente.
- **`services/cross_domain_reads.py`** es la única excepción explícita. Vive en `services/`, fuera de `agents/`, precisamente porque no pertenece a ningún dominio. Contiene funciones como `leer_stock_para(operator_id, material_code, session)`: cada una llama `assert_can_read` primero, y delega la consulta real a un servicio neutral (`services/stock_queries.py`, `services/production_queries.py`) — la única fuente de "cómo se lee stock/necesidades", reusada tanto por el tool propio del dominio dueño como por la lectura cruzada. Así la lógica nunca se duplica ni se mezcla dentro de otro dominio.
- Reglas no negociables de `cross_domain_reads.py`: (1) cada función llama `assert_can_read` antes de tocar cualquier dato; (2) **prohibido cualquier verbo de mutación** (`registrar_`, `crear_`, `actualizar_`, `eliminar_`) — es exclusivamente de lectura; (3) ningún `tools.py` de dominio lo importa directamente — solo el orquestador, al ensamblar el tool-set de cada agente.
- **`services/mrp.py`** (cálculo de cobertura/sugerencia de compra) es agnóstico de permisos: no importa `Domain` ni `permissions_service`, recibe datos ya autorizados y solo calcula. Mantiene un único módulo con lógica de permisos cruzados.

**Límite documentado, no resuelto todavía**: `assert_can_read` es granularidad "dominio completo" (todo o nada). Si en el futuro hace falta ocultar campos específicos (ej. costos) de una lectura cruzada, esta función no lo expresa — quedaría como una extensión futura, no un problema de este diseño.

## El orquestador es un dispatcher determinístico, no un LLM

`agents/orchestrator.py` **no** es un `LlmAgent` de Google ADK con `sub_agents`/transferencia automática. Dado que `ROLE_DOMAIN` es una función fija 1:1, el ruteo es 100% determinístico — no hay ambigüedad de intención que un LLM deba resolver. Usar un LLM para esa decisión agregaría latencia, costo, y una superficie de no-determinismo/inyección de prompt sin ganar nada.

Como el tool-set final de cada dominio es **estático** (fijo por `Domain`, no varía por operador individual — tanto `DOMAIN_ACTIONS` como `CROSS_DOMAIN_READERS` son fijos), los 3 `LlmAgent` + `Runner` de ADK se pre-construyen **una sola vez al boot** de la aplicación (`_build_runners()` en `orchestrator.py`), no por request. El trabajo del orquestador por request se reduce a:

1. `get_operator_permissions(operator_id, session)` → resuelve el dominio del operador (determinístico).
2. Selecciona el `Runner` ya construido para ese dominio.
3. Invoca el `Runner` con la consulta del operador.

El chequeo de permisos real sigue ocurriendo dentro de cada tool invocado por el agente (fail-closed) — el orquestador solo decide QUÉ agente atiende, nunca reemplaza los checks de `assert_can_perform`/`assert_can_read`.

## Integración con Google ADK (a verificar contra la versión instalada)

Patrón esperado — todavía no instalado en esta sesión, verificar nombres exactos al implementar:

- `from google.adk.agents import Agent` (alias `LlmAgent`) — un `Agent` por dominio, con `tools` = lista de `FunctionTool` (tools propias + lectura cruzada inyectada por el orquestador).
- `from google.adk.models.lite_llm import LiteLlm` — para usar modelos Claude (`LiteLlm(model="anthropic/claude-...")`), con `ANTHROPIC_API_KEY` en el entorno. LiteLLM no requeriría el SDK `anthropic` instalado aparte.
- `from google.adk.tools import FunctionTool`, `SessionService`, `Runner` — para ejecutar y persistir conversaciones.
- Se usa `Runner` como librería dentro de nuestro propio FastAPI (no el helper `get_fast_api_app` de ADK), porque `routers/agents.py` es un router HTTP propio, sin lógica de negocio embebida, consistente con el resto de la arquitectura (capas: router → orquestador/services → db).

## Ingesta de datos (diseño conceptual — schema deferido)

Excel/CSV es el formato de entrada de los operadores. Para stock específicamente: **cada carga es una foto completa** que reemplaza el stock vigente (full-replace), no un log acumulativo — así es como suelen exportar los sistemas de control de stock. La semántica de otros archivos (necesidades de Planificación, precios de Compras) todavía no está definida y se decidirá cuando se implemente cada pipeline, sin asumir que sigue el mismo patrón que stock.

El pipeline (a implementar al final, cuando se cierre el schema): Excel sube → pandas parsea → mapeo de columnas (asistido por LLM) → preview/confirmación del operador → upsert a la tabla del dominio vía `services/stock_queries.py` / `services/production_queries.py`.

## Capas y flujo de una consulta

```
Next.js (apps/web) — chat por dominio
   │ HTTP
   ▼
FastAPI routers/agents.py — sin lógica de negocio
   │
   ▼
agents/orchestrator.py — dispatcher determinístico
   │ (resuelve dominio vía permissions_service, selecciona Runner pre-construido)
   ▼
LlmAgent de Google ADK (uno por dominio, boot-time)
   │ tools propias (agents/<dominio>/tools.py) + lectura cruzada inyectada
   ▼
services/*_queries.py, services/cross_domain_reads.py, services/mrp.py
   ▼
PostgreSQL (db/models.py, db/session.py)
```

## Estructura de directorios

```
apps/
  api/
    requirements.txt
    src/
      main.py                       # FastAPI app, monta routers/
      agents/
        orchestrator.py             # dispatcher determinístico
        base_agent.py
        compras/{agent.py, tools.py, prompts.py}
        almacen/{agent.py, tools.py, prompts.py}
        planificacion/{agent.py, tools.py, prompts.py}
      services/
        permissions_service.py      # Domain, Role, DOMAIN_ACTIONS, CROSS_DOMAIN_READERS,
                                     # assert_can_perform, assert_can_read
        cross_domain_reads.py       # única excepción — solo lectura, solo orquestador
        stock_queries.py            # única fuente de "cómo se lee/escribe stock"
        production_queries.py       # única fuente de "cómo se lee necesidades"
        mrp.py                      # cálculo puro, agnóstico de permisos
      db/{models.py, session.py}
      routers/agents.py
  web/                              # Next.js, scaffold mínimo
docs/
  architecture.md                   # este archivo
  context/
    estado-proyecto.md              # snapshot vivo (mantenido por el subagente documentador)
    decisiones.md                   # log cronológico de decisiones
.claude/
  agents/
    documentador.md
    guardian-arquitectura.md
```

## Qué queda pendiente (fuera de este diseño)

- Schema exacto de las tablas de negocio (stock, necesidades, precios) y el pipeline de ingesta de Excel — decisión explícitamente diferida por el usuario.
- Instalar `google-adk` y reemplazar los `NotImplementedError` de `agent.py`/`orchestrator.py` por la construcción real de `LlmAgent`/`Runner`.
- Implementar `tools.py` de Compras y Planificación (hoy `DOMAIN_ACTIONS` está vacío para ambos).
- Auth.js real (hoy el rol se lee de una tabla `operators` interina en Postgres).
- Logging de auditoría (operator_id + rol + timestamp) en toda acción mutante — pendiente en `registrar_movimiento`.
- Chat real en `apps/web` (hoy es solo scaffold de estructura).
