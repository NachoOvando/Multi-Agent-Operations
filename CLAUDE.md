## Proyecto: Agentes operativos (Compras / Almacén / Planificación)

### Arquitectura
- Orquestador + 3 agentes especialistas (Google ADK), permisos consultados vía `permissions_service.py`
- Cada agente tiene tools scoped — NUNCA cargar tools de ACCIÓN/ESCRITURA de otro dominio en un agente que no corresponde
- El orquestador es el único componente que conoce los 3 dominios, **con una única excepción**: `services/cross_domain_reads.py`. Vive fuera de `agents/`, es exclusivamente de LECTURA (nunca escritura), y solo el orquestador lo invoca para inyectar tools de lectura cruzada al ensamblar el agente de un dominio (ver `docs/architecture.md`). Ningún `tools.py` de dominio lo importa directamente.
- Lectura cruzada entre dominios (solo lectura) se gobierna con `assert_can_read` + `CROSS_DOMAIN_READERS` (`permissions_service.py`) — eje de permiso separado de `assert_can_perform`/`DOMAIN_ACTIONS`, que sigue gobernando exclusivamente las acciones/escritura dentro del dominio propio del operador
- El orquestador es un dispatcher determinístico (no un LLM/`sub_agents` de ADK): el ruteo lo decide `ROLE_DOMAIN` (fijo, 1:1), no una interpretación de intención
- **Identidad vs. autorización, dos ejes separados**: FastAPI emite y verifica su propio JWT (`services/auth_service.py`, HS256, `JWT_SECRET_KEY`) — responde "quién es". `permissions_service.py` sigue respondiendo "qué puede hacer" a partir del `operator_id` que sale de ahí; su interfaz pública no cambia. Next.js/Auth.js nunca decodifica ese JWT, solo lo transporta dentro de su propia sesión cifrada (ver `docs/architecture.md`, sección "Auth").
- **Hosting split, no es arbitrario**: `apps/web` (Next.js) va a Vercel, `apps/api` (FastAPI + Google ADK) va a Railway — porque los Runners de ADK se pre-construyen una sola vez al boot (`main.py::lifespan`) con conexión persistente a Postgres, incompatible con funciones serverless. El navegador nunca llama directo a Railway: pasa siempre por el proxy BFF (`apps/web/app/api/backend/[...path]/route.ts`).

### Reglas duras
- Ningún tool nuevo se agrega a un agente sin verificar `permissions_service.py`
- No mezclar lógica de negocio de un dominio (ej. cálculo de stock) dentro de otro agente — la lectura cruzada autorizada vía `cross_domain_reads.py` no viola esto: la lógica de consulta vive una sola vez, en `services/*_queries.py`, nunca duplicada
- `services/cross_domain_reads.py` nunca expone un verbo de mutación (`registrar_`, `crear_`, `actualizar_`, `eliminar_`) — es solo lectura, sin excepción
- Toda acción de un agente que modifica datos (crear orden, registrar movimiento) debe loguearse con operator_id + rol + timestamp
- `operator_id` en cualquier endpoint HTTP protegido sale exclusivamente de `Depends(get_current_operator)` (`security/dependencies.py`) — nunca de un path/query/body param del cliente; es el mecanismo que impide que un operador se haga pasar por otro

### No tocar sin confirmación
- `permissions_service.py` — cambios acá afectan a los 3 agentes
- `tools.py` de cada agente — agregar un tool sin auditar el permiso correspondiente es el vector de riesgo #1
- `services/cross_domain_reads.py` — es la única puerta de lectura cruzada entre dominios; cualquier cambio acá afecta el modelo de permisos de los 3 agentes
- `services/auth_service.py` / `security/dependencies.py` — cambios acá afectan de dónde sale `operator_id` en toda la API, upstream de `permissions_service.py`
