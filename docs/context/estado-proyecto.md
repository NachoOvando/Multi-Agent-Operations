# Estado del proyecto

> Mantenido por el subagente `documentador`. Refleja qué está implementado de verdad vs. qué es un stub — no asumir que un archivo existente tiene lógica real sin revisarlo acá.

## Implementado (código real, funcionando)

- `apps/api/src/services/permissions_service.py`: `Domain`, `Role`, `ROLE_DOMAIN`, `DOMAIN_ACTIONS` (ahora completo para los 3 dominios: Almacén, Compras, Planificación — ver abajo), `CROSS_DOMAIN_READERS`, `get_operator_permissions` (fail-closed), `assert_can_perform`, `assert_can_read`.
- `apps/api/src/db/models.py`: modelo `Operator` (operator_id, role, created_at).
- `apps/api/src/db/session.py`: engine/sesión lazy vía `DATABASE_URL`. Documenta el requisito de prefijo `postgresql+psycopg://` (ver `docs/context/decisiones.md`).
- `apps/api/src/services/cross_domain_reads.py`: `leer_stock_para`, `leer_necesidades_para` — permission-check real (`assert_can_read`), delegan a `stock_queries`/`production_queries` (que siguen siendo stubs — ver abajo). Verificado end-to-end: el `Runner` de Compras recibe exactamente estos dos tools inyectados por el orquestador.
- **`apps/api/src/agents/orchestrator.py`**: dejó de ser esqueleto — `_build_runners()`, `_extra_tools_for(domain)` y `handle_query()` son código real que construye `DatabaseSessionService` + los 3 `LlmAgent`/`Runner` de ADK una sola vez, resuelve el dominio del operador vía `permissions_service`, e invoca `runner.run_async(...)`. Validado instalando `google-adk==2.5.0` de verdad en `apps/api/.venv` (no solo `py_compile`): se construyeron los 3 `Runner` completos contra un `DATABASE_URL` de prueba y se confirmó que Compras recibe `leer_stock_para` + `leer_necesidades_para` inyectados, y que Almacén/Planificación no tienen ninguna referencia cruzada.
- **`apps/api/src/agents/almacen/agent.py`, `agents/compras/agent.py`, `agents/planificacion/agent.py`**: `build_agent(extra_tools=None)` real — construyen un `Agent` (alias `LlmAgent` de ADK) con `model=LiteLlm(model="anthropic/claude-sonnet-5")` y wrappers `_nombre_tool(tool_context: ToolContext, ...)` que extraen `operator_id` de `tool_context.user_id`, abren sesión de DB corta con `db/session.py::get_session()` y delegan a la función real de `tools.py`. Patrón confirmado contra la API real de ADK 2.5.0 (no es solo el diseño documentado — se instaló y se probó).
- `apps/api/src/agents/almacen/tools.py`: `consultar_stock` (permission-check real + delega a `stock_queries.get_stock`, que es stub) y `registrar_movimiento` (permission-check real, cuerpo `NotImplementedError` — falta también el logging de auditoría y el schema de stock).
- **`apps/api/src/agents/compras/tools.py`** (antes vacío, ahora implementado): `consultar_precios_proveedor` y `registrar_orden_compra` — permission-check real (`assert_can_perform`), delegan a `services/purchasing_queries.py` (nuevo, stub — ver abajo).
- **`apps/api/src/agents/planificacion/tools.py`** (antes vacío, ahora implementado): `consultar_necesidades` (reusa `production_queries.get_requirements` — la misma fuente que usa la lectura cruzada de Compras, sin duplicar lógica) y `registrar_necesidad` — permission-check real, delega a `production_queries.py` (stub).
- `apps/api/src/agents/{almacen,compras,planificacion}/prompts.py`: `INSTRUCTION` real con reglas de dominio (antes docstring-only, ahora contenido real usado por `build_agent`).
- `apps/api/requirements.txt`: versiones verificadas por instalación real en esta sesión — `google-adk>=2.5.0`, `fastapi>=0.139.0`, `uvicorn>=0.51.0`, `sqlalchemy>=2.0`, `psycopg[binary]>=3.1`, y `litellm==1.91.4` pineado (ver decisión en `decisiones.md`).
- `apps/api/.env.example` (nuevo): documenta `DATABASE_URL` con prefijo obligatorio `postgresql+psycopg://` y `ANTHROPIC_API_KEY`.
- `apps/api/.venv/`: entorno virtual real con las dependencias instaladas y verificadas (no solo declaradas en requirements.txt).
- `apps/api/src/routers/agents.py`: `router = APIRouter(...)` real, sin endpoints todavía (sin cambios respecto a la sesión anterior).
- `apps/api/src/main.py`: FastAPI app real, monta el router — sin lifespan de boot de ADK todavía (sin cambios respecto a la sesión anterior).

## Stub (estructura decidida, sin lógica real — todos documentan explícitamente qué falta)

- `apps/api/src/services/stock_queries.py`: `get_stock`, `upsert_stock_snapshot` — `NotImplementedError`, esperan el schema de stock.
- `apps/api/src/services/production_queries.py`: `get_requirements`, `create_requirement` — `NotImplementedError`, esperan el schema de necesidades de producción.
- **`apps/api/src/services/purchasing_queries.py`** (nuevo en esta sesión): `get_supplier_price`, `create_purchase_order` — `NotImplementedError`, esperan el schema de precios de proveedor/órdenes de compra.
- `apps/api/src/services/mrp.py`: `compute_coverage` — `NotImplementedError`, depende de que `stock_queries`/`production_queries` devuelvan datos reales.
- `apps/api/src/agents/base_agent.py`: docstring-only, sin uso real todavía (ningún `agent.py` de dominio lo importa).
- `apps/api/src/routers/agents.py`: sin endpoint que conecte HTTP → `orchestrator.handle_query`.
- `apps/api/src/main.py`: sin `lifespan` que pre-construya los Runners al boot.
- `apps/web/`: scaffold de estructura Next.js, sin chat real.

## No implementado / no decidido todavía

- Auth.js real (hoy el rol viene de una tabla `operators` interina en Postgres).
- Schema de stock, necesidades de producción, precios de proveedor — deliberadamente diferido.
- Pipeline de ingesta de Excel (parseo, mapeo de columnas, upsert).
- Logging de auditoría (operator_id + rol + timestamp) en acciones mutantes — pendiente en `registrar_movimiento`, `registrar_orden_compra`, `registrar_necesidad` (los tres tienen el TODO explícito en el código).
- Endpoint HTTP real en `routers/agents.py` que reciba la consulta del operador y llame `orchestrator.handle_query`.
- `lifespan` de FastAPI en `main.py` que invoque `get_runner_for_domain` (o `_build_runners`) al arrancar la app, en vez de construirse lazy en el primer request.
- Estrategia definitiva de `session_id` de ADK (hoy `handle_query` usa `operator_id` como `session_id`, marcado como TODO explícito a revisar cuando exista un modelo real de conversaciones).
- Llamada real end-to-end contra la API de Anthropic: se validó la *construcción* de los 3 `Runner`/`LlmAgent` con `google-adk` instalado, pero no se probó una invocación real de `runner.run_async(...)` contra un modelo (requiere `ANTHROPIC_API_KEY` configurada).
- Actualizar el pin de `litellm==1.91.4` cuando haya wheel precompilado disponible para una versión más nueva en el entorno de destino (hoy bloqueado por falta de Cargo/MSVC Build Tools en Windows).

## Última actualización

Sesión de instalación real de `google-adk==2.5.0` + `litellm` en un venv (`apps/api/.venv`), que validó contra la API real lo que antes era "a verificar" en `docs/architecture.md`, y de implementación de los tools propios de Compras y Planificación (antes vacíos). El orquestador y los 3 `agent.py` de dominio pasaron de esqueleto/`NotImplementedError` a wiring real y verificado end-to-end (construcción de Runners + inyección de tools cruzados). Lo que sigue siendo `NotImplementedError` es exclusivamente la lógica de datos de negocio (`stock_queries`, `production_queries`, `purchasing_queries`, `mrp`), que espera el schema de Excel — deliberadamente diferido, sin cambios en esa decisión. Ver `docs/context/decisiones.md` para el detalle cronológico.
