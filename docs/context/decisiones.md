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

## Flujo fijo de subagentes de Claude Code para tareas full-stack: backend → frontend → validador

**Decisión**: se agregaron 3 subagentes nuevos en `.claude/agents/` — `backend-especialista.md`, `frontend-especialista.md`, `validador-resultados.md` — que se suman a los ya existentes `documentador.md` y `guardian-arquitectura.md`. Para cualquier tarea que toque backend y frontend juntos, el orden es fijo y no intercambiable: primero `backend-especialista` (scope `apps/api/src`, define la lógica, la seguridad, y el contrato de comunicación — endpoints, shapes de request/response, reglas de auth), después `frontend-especialista` (scope `apps/web`, implementa la UI adaptándose estrictamente a ese contrato, sin inventar shapes ni relajar la seguridad definida por el backend), y al final `validador-resultados` (solo lectura + Bash para tests/build existentes, nunca edita — igual que `guardian-arquitectura` en ese sentido — verifica que el contrato entre ambos lados sea consistente en el código real y que el resultado coincide con lo pedido).
**Motivo**: el backend es la fuente de verdad del contrato y de la seguridad del sistema (alineado con las reglas duras de `CLAUDE.md` sobre permisos y scoping de tools); si el frontend fuera primero, tendría que adivinar o inventar shapes de API, que es exactamente el error que el usuario quiere evitar. El orden fijo elimina esa ambigüedad estructuralmente, no por convención.
**Nota de diseño en `frontend-especialista.md`**: usa como referencia conceptual de UI/UX los principios de la librería `ui-ux-pro-max-skill` (GitHub, https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) — explícitamente aclarado como referencia de principios de diseño, no como dependencia instalada en el repo ni como comando/script disponible en el entorno.
**Descartado**: dejar que `frontend-especialista` corra en paralelo o antes que `backend-especialista` en tareas full-stack — se descartó porque invierte la relación fuente-de-verdad: el contrato (incluida la seguridad) lo define el backend, no la UI.
**Alcance de este subagente `documentador`**: esta entrada documenta la incorporación de los 3 subagentes de Claude Code y el flujo de trabajo que gobierna su orden de invocación — no implica ningún cambio en el estado real del código de la aplicación (`apps/api`, `apps/web`), por lo que `docs/context/estado-proyecto.md` no se modifica en esta sesión.

## Auth.js real reemplaza la tabla interina — se cierra la decisión previa

**Decisión**: se implementó login real por usuario + password (Slice 1 del plan `necesito-2-subagentes-greedy-lagoon.md`). Esto reemplaza (no solo extiende) la decisión previa "Auth.js: no existe todavía, tabla interina en Postgres" — esa entrada queda revertida/superada, no se edita retroactivamente, se deja constancia acá.
**Cómo se resolvió sin romper la interfaz pública de `permissions_service.py`**: tal como esa decisión anterior ya anticipaba, "solo cambia de dónde sale `operator_id`" — hoy sale de `Depends(get_current_operator)` (`security/dependencies.py`), que decodifica un JWT, en vez de venir de un parámetro de función sin verificar. `permissions_service.py` no se tocó.
**Motivo**: cerrar el gap de identidad real — antes `operator_id` era un parámetro de función que nadie verificaba; cualquiera que lo conociera podía hacerse pasar por otro operador porque no había capa HTTP de identidad.

## FastAPI emite y verifica su propio JWT — Next.js nunca lo decodifica

**Decisión**: el backend FastAPI (`services/auth_service.py`) emite y verifica su propio JWT (PyJWT, HS256, `JWT_SECRET_KEY` — solo lo conoce el backend). Next.js/Auth.js nunca decodifica ese token: lo recibe de `POST /api/auth/login`, lo guarda opaco dentro de su propia sesión cifrada de NextAuth (`session.backendToken`), y solo lo reenvía como `Authorization: Bearer <token>` en cada llamada posterior al backend.
**Motivo**: mantener un único punto de verdad para la identidad del backend, sin que el frontend necesite conocer el secreto de firma ni la lógica de expiración/claims — si mañana cambia el algoritmo o los claims del JWT del backend, Next.js no se entera ni necesita cambiar código, porque nunca lo interpreta, solo lo transporta.
**Descartado**: decodificar en Python el JWE que produce NextAuth (`session: {strategy: "jwt"}`) para que el backend confíe directamente en la sesión de NextAuth — se descartó porque acoplaría FastAPI al formato/secreto interno de Auth.js (una librería de Node), duplicando la superficie de confianza en dos stacks distintos en vez de tener una sola fuente de identidad (el backend) que el frontend simplemente transporta.

## Next.js va a Vercel, FastAPI+ADK va a Railway

**Decisión**: `apps/web` (Next.js) se hostea en Vercel; `apps/api` (FastAPI + Google ADK) se hostea en Railway.
**Motivo**: los `Runner` de Google ADK se construyen una sola vez al boot de la aplicación (`main.py::lifespan`) y usan `DatabaseSessionService` con conexión persistente a Postgres — incompatible con funciones serverless de Vercel, que no garantizan proceso persistente entre invocaciones. Railway sí ofrece un proceso long-running, compatible con ese patrón de boot-time construction que ya era parte del diseño previo del orquestador (ver decisión "El orquestador es un dispatcher determinístico").
**Consecuencia técnica documentada**: `railway.json` vive en la raíz del repo, no en `apps/api/`, porque los imports del backend son absolutos (`from apps.api.src...`) — el Root Directory de Railway debe ser la raíz del monorepo, no `apps/api`.
**Descartado**: un único hosting para ambas apps (ej. todo en Vercel con funciones serverless para el backend, o todo en Railway) — se descartó porque el frontend Next.js sí encaja bien en el modelo serverless de Vercel (sin estado persistente propio, todo el estado vive en la sesión de NextAuth + el backend), mientras que forzar el backend a serverless hubiera roto la premisa de Runners pre-construidos.

## Proxy BFF en vez de `rewrites()` de Next.js

**Decisión**: `apps/web/app/api/backend/[...path]/route.ts` es un Route Handler propio que actúa de BFF (Backend For Frontend) — lee la sesión de NextAuth server-side y reenvía el request al backend de Railway adjuntando `Authorization: Bearer <backendToken>` dinámicamente por sesión.
**Motivo**: `rewrites()` de `next.config.ts` (que tenía un TODO explícito antes de esta sesión) es una reescritura estática de URL sin acceso a la sesión del usuario en el momento de la request — no puede inyectar un header `Authorization` distinto por usuario. Un Route Handler sí corre código server-side por request, con acceso a `auth()`, lo que permite adjuntar el JWT correcto de cada sesión antes de reenviar.
**Consecuencia de seguridad relacionada**: como efecto directo de este diseño, el navegador nunca ve la URL de Railway ni el JWT del backend — toda esa información permanece server-side en Next.js. `BACKEND_API_URL` es server-only (nunca `NEXT_PUBLIC_*`), usada solo en `auth.ts` y en este proxy.
**Descartado**: `rewrites()` estático de Next.js (única alternativa nativa sin código propio) — se descartó por no poder inyectar el header de auth dinámico por sesión, que es un requisito duro dado el diseño de "backend emite su propio JWT".

## Endpoint de mensajería protegido: `operator_id` nunca sale de un param de cliente

**Decisión**: `POST /api/agents/messages` (antes un TODO vacío en `routers/agents.py`) obtiene `operator_id` exclusivamente de `Depends(get_current_operator)` — nunca de un path param, query param o campo del body. `MessageRequest` (schema del body) no incluye `operator_id`.
**Motivo**: cerrar explícitamente el vector de suplantación de identidad descrito en el plan — con un `operator_id` de cliente, cualquiera que conociera o adivinara el id de otro operador podía hacerse pasar por él y activar sus permisos de dominio. Con esto, la única forma de establecer identidad es un JWT válido emitido por el propio backend.
**Alcance no tocado**: `permissions_service.py::assert_can_perform`/`assert_can_read` siguen siendo el único punto real de autorización dentro de cada tool — este cambio es de autenticación (quién es), no reemplaza ni duplica la autorización (qué puede hacer).

## Pendiente explícito de verificación en runtime (no resuelto en esta sesión)

**Decisión**: se deja constancia de que dos verificaciones de runtime del Slice 1 no se pudieron ejercitar en vivo en esta sesión: (1) `alembic -c apps/api/alembic.ini upgrade head` contra una Postgres real, y (2) el boot real de `uvicorn apps.api.src.main:app` (con el `lifespan` nuevo pre-construyendo los 3 Runners). El código de ambos existe y fue relevado directamente (`apps/api/alembic/versions/0001_baseline_operators.py`, `0002_operator_auth_fields.py`, `apps/api/src/main.py::lifespan`), pero no runtime real.
**Motivo**: Docker no está disponible en el sandbox de desarrollo actual, y `docker-compose.yml` (Postgres local) depende de Docker para levantarse.
**Acción pendiente, no resuelta acá**: correr manualmente `docker compose up -d db && alembic -c apps/api/alembic.ini upgrade head` y arrancar `uvicorn` en un entorno con Docker antes de considerar el Slice 1 100% verificado en runtime — no alcanza con la verificación estática de código hecha en esta sesión.
**Alcance de `apps/api/tests/`**: también sigue sin existir el directorio de tests (`conftest.py`, `test_auth_service.py`, `test_permissions_service.py`) mencionado en el plan como parte del cierre del Slice 1 — se señaló explícitamente como "se está agregando ahora en un follow-up inmediato", pero al momento de este relevamiento el directorio no existe todavía en el repo.
