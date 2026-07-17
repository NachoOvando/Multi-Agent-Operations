# Estado del proyecto

> Mantenido por el subagente `documentador`. Refleja qué está implementado de verdad vs. qué es un stub — no asumir que un archivo existente tiene lógica real sin revisarlo acá.

## Implementado (código real, funcionando)

- `apps/api/src/services/permissions_service.py`: `Domain`, `Role`, `ROLE_DOMAIN`, `DOMAIN_ACTIONS`, `CROSS_DOMAIN_READERS`, `get_operator_permissions` (fail-closed), `assert_can_perform`, `assert_can_read`.
- `apps/api/src/db/models.py`: modelo `Operator` (operator_id, role, created_at).
- `apps/api/src/db/session.py`: engine/sesión lazy vía `DATABASE_URL`.
- `apps/api/src/services/cross_domain_reads.py`: `leer_stock_para`, `leer_necesidades_para` — permission-check real (`assert_can_read`), delegan a `stock_queries`/`production_queries` (que sí son stubs — ver abajo).
- `apps/api/src/agents/almacen/tools.py`: `consultar_stock` (permission-check real + delega a `stock_queries.get_stock`, que es stub) y `registrar_movimiento` (permission-check real, cuerpo `NotImplementedError` — falta también el logging de auditoría).
- `apps/api/src/routers/agents.py`: `router = APIRouter(...)` real, sin endpoints todavía.
- `apps/api/src/main.py`: FastAPI app real, monta el router — sin lifespan de boot de ADK todavía.

## Stub (estructura decidida, sin lógica real — todos documentan explícitamente qué falta)

- `apps/api/src/services/stock_queries.py`, `production_queries.py`, `mrp.py`: `NotImplementedError` — esperan el schema de las tablas de negocio (decisión diferida al final).
- `apps/api/src/agents/orchestrator.py`: esqueleto real de dispatcher determinístico (`get_runner_for_domain`, `handle_query`), pero `_build_runners()` lanza `NotImplementedError` — depende de `google-adk` instalado y de que `agent.py` de cada dominio esté implementado.
- `apps/api/src/agents/{compras,almacen,planificacion}/agent.py`: `build_agent(extra_tools=None)` con `NotImplementedError` — depende de `google-adk`.
- `apps/api/src/agents/{compras,planificacion}/tools.py`, `prompts.py`, `base_agent.py`: docstring-only, sin funciones.
- `apps/api/src/agents/almacen/prompts.py`: docstring-only.
- `apps/web/`: scaffold de estructura Next.js, sin chat real.

## No implementado / no decidido todavía

- Auth.js real (hoy el rol viene de una tabla `operators` interina en Postgres).
- Schema de stock, necesidades de producción, precios de proveedor — deliberadamente diferido.
- Pipeline de ingesta de Excel (parseo, mapeo de columnas, upsert).
- `DOMAIN_ACTIONS[Domain.COMPRAS]` y `DOMAIN_ACTIONS[Domain.PLANIFICACION]` — vacíos, esperan que se implementen los tools de esos dominios.
- Logging de auditoría (operator_id + rol + timestamp) en acciones mutantes.
- Instalación real de `google-adk`/`litellm`/`fastapi`/`uvicorn` (están en `requirements.txt` pero no instaladas ni verificadas en este entorno).

## Última actualización

Sesión de consolidación de arquitectura ADK2 (pivote desde el plan inicial LangGraph). Ver `docs/context/decisiones.md` para el detalle cronológico.
