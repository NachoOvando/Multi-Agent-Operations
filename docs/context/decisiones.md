# Log de decisiones

> Mantenido por el subagente `documentador`. Registro cronológico de decisiones ya cerradas, para que no se reabran sin querer en sesiones futuras. Formato: decisión + motivo + alternativas descartadas.

## Framework de agentes: Google ADK

**Decisión**: usar `google-adk` (Python) para los 3 agentes especialistas, con modelos Claude vía el wrapper `LiteLlm` (no Gemini).
**Motivo**: el usuario lo confirmó explícitamente como "ADK2" tras describir un patrón orquestador + especialistas con tools scoped por dominio, que encaja con las primitivas de ADK (`Agent`/`LlmAgent`, `FunctionTool`, `Runner`).
**Descartado**: LangGraph (plan inicial de la sesión, reemplazado por completo).

## Orquestador determinístico, no LLM

**Decisión**: el orquestador es una función Python que resuelve el dominio del operador (vía `ROLE_DOMAIN`, fijo 1:1) y despacha al `Runner` de ADK correspondiente — no un `LlmAgent` con `sub_agents`/transferencia automática.
**Motivo**: el ruteo no tiene ambigüedad de intención que resolver (el rol del operador determina el dominio de forma determinística); un LLM ahí solo agregaría latencia, costo, y superficie de inyección de prompt.
**Descartado**: orquestador como `LlmAgent` raíz con `sub_agents`.

## Cross-domain read: necesario, solo lectura

**Decisión**: el agente de Compras necesita leer (nunca escribir) datos de Almacén (stock) y Planificación (necesidades) para poder sugerir compras. Se modela con un eje de permiso separado (`assert_can_read` + `CROSS_DOMAIN_READERS`), distinto de `assert_can_perform`/`DOMAIN_ACTIONS` (acciones propias del dominio).
**Motivo**: es el caso de uso original y central del proyecto — sin esto, el sistema no cumple su objetivo. El modelo de permisos inicial (estrictamente 1 rol = 1 dominio, sin cruces) no lo permitía y había que resolver la tensión explícitamente.
**Cómo se resolvió sin romper "el orquestador es el único que conoce los 3 dominios"**: se creó `services/cross_domain_reads.py`, módulo neutral fuera de `agents/`, como única excepción documentada — ver `docs/architecture.md`.
**Descartado**: dejar que `agents/compras/tools.py` importe directamente `Domain.ALMACEN`/`Domain.PLANIFICACION` (violaría la regla al pie de la letra); usar `AgentTool` de ADK para invocar el LLM de otro dominio (más caro/lento que un simple tool de lectura de datos, ya que no hace falta razonamiento del otro agente, solo datos).

## Excel: formato de entrada, no fuente de verdad

**Decisión**: Excel/CSV es cómo los operadores manejan sus datos hoy, pero se ingesta y normaliza a Postgres — el sistema nunca lee Excel en tiempo real para responder consultas.
**Motivo**: el orquestador necesita cruzar datos de forma confiable y auditable (stock vs. necesidades vs. precios); eso requiere una fuente de verdad relacional, no recalcular sobre spreadsheets en cada consulta.

## Semántica de ingesta de stock: full-replace

**Decisión**: cada carga de Excel de stock representa una foto completa del stock vigente y reemplaza (upsert full-replace) la tabla correspondiente — no es un log acumulativo de movimientos.
**Motivo**: confirmado explícitamente por el usuario; es como suelen exportar los sistemas de control de stock.
**Nota**: esto se confirmó específicamente para stock. Necesidades de producción (Planificación) y precios/OCs (Compras) probablemente tengan semántica distinta (por work order, por catálogo) — no asumir el mismo patrón, preguntar cuando se implemente cada pipeline.

## Schema de datos de negocio: diferido al final

**Decisión**: el contenido/formato exacto de las tablas que vienen de Excel (columnas de stock, necesidades, precios) se define al final, después de cerrar el resto del diseño arquitectónico.
**Motivo**: pedido explícito del usuario — "la idea es tener todo diseñado y después avanzar con esa instancia". Por eso `stock_queries.py`, `production_queries.py` y `mrp.py` son stubs con `NotImplementedError` documentado, no placeholders con un schema inventado.

## Auth.js: no existe todavía, tabla interina en Postgres

**Decisión**: mientras Auth.js no esté implementado, el rol de cada operador se lee de una tabla `operators` (operator_id, role) en Postgres. La interfaz pública de `permissions_service.py` (operator_id → permisos) no cambia cuando Auth.js llegue — solo cambia de dónde sale `operator_id`.
**Motivo**: el usuario confirmó que Auth.js todavía no existe y que el modelo de roles es "un rol = un dominio fijo" (simple, sin roles cruzados).

## Stack: Next.js + Python confirmado

**Decisión**: Next.js como frontend (`apps/web/`), Python/FastAPI como backend (`apps/api/`) — sin cambios respecto al estándar global del usuario.
**Motivo**: confirmado explícitamente; además coherente con la propia regla del usuario ("si toca datos tabulares o procesamiento de archivos → Python").

## google-adk==2.5.0 instalado y validado: API real confirma el diseño documentado

**Decisión**: se instaló `google-adk==2.5.0` de verdad en un venv (`apps/api/.venv`) y se verificó contra la API real (no solo lectura de docs) lo que `docs/architecture.md` marcaba como "a verificar": `Agent` es alias de `LlmAgent`; acepta callables planos en `tools` sin envolverlos manualmente en `FunctionTool`; `model` acepta `LiteLlm(model="anthropic/<modelo>")`; `Runner` tiene `auto_create_session=True` (evita gestionar sesiones de ADK a mano); `Runner.run_async` es un async generator que requiere `user_id`, `session_id`, `new_message=types.Content(role="user", parts=[types.Part(text=...)])`.
**Motivo**: cerrar la incertidumbre marcada explícitamente como "a verificar" antes de escribir wiring real en `orchestrator.py` y en los 3 `agent.py` de dominio — evitar código especulativo contra una API no confirmada.
**Resultado**: el diseño previamente documentado (patrón esperado) resultó correcto en todos estos puntos; no hizo falta rediseñar nada, solo reemplazar `NotImplementedError` por la implementación real siguiendo el patrón ya documentado en `docs/architecture.md`.

## DATABASE_URL: prefijo obligatorio `postgresql+psycopg://`

**Decisión**: toda `DATABASE_URL` del proyecto debe usar el prefijo `postgresql+psycopg://` (psycopg v3), nunca `postgresql://` a secas.
**Motivo**: se detectó instalando `google-adk` de verdad que el prefijo genérico `postgresql://` hace que SQLAlchemy (y el engine async que arma `DatabaseSessionService` de ADK) default a `psycopg2`, que no está instalado en este proyecto (se usa `psycopg[binary]>=3.1` en requirements.txt). El mismo prefijo sirve tanto para el engine sync propio (`db/session.py`) como para el engine async de ADK (`orchestrator.py`) — psycopg v3 soporta ambos modos desde el mismo driver, así que no hace falta duplicar configuración.
**Documentado en**: `apps/api/src/db/session.py` (docstring) y `apps/api/.env.example` (nuevo archivo, con el valor de ejemplo ya corregido).
**Descartado**: usar `psycopg2` como driver — hubiera requerido agregarlo a requirements.txt sin necesidad real, cuando psycopg3 ya cubre sync y async.

## litellm pineado a 1.91.4

**Decisión**: `litellm==1.91.4` (versión exacta, no rango) en `requirements.txt`, instalado con `pip install --only-binary=litellm -r requirements.txt`.
**Motivo**: versiones más nuevas de `litellm` incluyen una extensión nativa en Rust (`litellm-rust`/python-bridge vía `maturin`) que requiere compilar desde source con Cargo + MSVC Build Tools (`link.exe`) — herramientas no instaladas en este entorno Windows. La versión `1.91.4` es la más reciente con wheel precompilado disponible, evitando ese requisito de compilación.
**Descartado**: instalar Cargo + MSVC Build Tools para poder usar una versión más nueva sin pin — se descartó por ahora para no agregar una dependencia de toolchain pesada al entorno de desarrollo solo para desbloquear una versión de una dependencia transitiva (LiteLlm de ADK). Revisar este pin cuando exista wheel precompilado para una versión más nueva en el entorno de destino real (ver nota en `requirements.txt` y en `docs/context/estado-proyecto.md`).

## Tools de Compras y Planificación: implementados reusando la fuente única de lectura

**Decisión**: se implementaron `agents/compras/tools.py` (`consultar_precios_proveedor`, `registrar_orden_compra`, contra el nuevo `services/purchasing_queries.py`) y `agents/planificacion/tools.py` (`consultar_necesidades`, `registrar_necesidad`). `consultar_necesidades` reusa `services/production_queries.py::get_requirements` — la misma función que ya usa `cross_domain_reads.leer_necesidades_para` — en vez de crear una segunda función de lectura.
**Motivo**: evitar duplicar "cómo se leen necesidades" en dos lugares (regla dura de CLAUDE.md sobre no mezclar/duplicar lógica de negocio entre dominios), consistente con el mismo patrón ya usado por `stock_queries.get_stock` en Almacén.
**Estado real**: los permission-checks (`assert_can_perform`) son reales y funcionan; la lectura/escritura de datos sigue en `NotImplementedError` en `purchasing_queries.py` y `production_queries.py` porque el schema de esas tablas sigue diferido (ver decisión "Schema de datos de negocio: diferido al final"). Se actualizó `DOMAIN_ACTIONS[Domain.COMPRAS]` y `DOMAIN_ACTIONS[Domain.PLANIFICACION]` en `permissions_service.py` con las acciones correspondientes — antes estaban vacíos.
