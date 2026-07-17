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
