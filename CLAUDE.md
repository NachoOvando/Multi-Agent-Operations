## Proyecto: Agentes operativos (Compras / Almacén / Planificación)

### Arquitectura
- Orquestador + 3 agentes especialistas (Google ADK), permisos consultados vía `permissions_service.py`
- Cada agente tiene tools scoped — NUNCA cargar tools de ACCIÓN/ESCRITURA de otro dominio en un agente que no corresponde
- El orquestador es el único componente que conoce los 3 dominios, **con una única excepción**: `services/cross_domain_reads.py`. Vive fuera de `agents/`, es exclusivamente de LECTURA (nunca escritura), y solo el orquestador lo invoca para inyectar tools de lectura cruzada al ensamblar el agente de un dominio (ver `docs/architecture.md`). Ningún `tools.py` de dominio lo importa directamente.
- Lectura cruzada entre dominios (solo lectura) se gobierna con `assert_can_read` + `CROSS_DOMAIN_READERS` (`permissions_service.py`) — eje de permiso separado de `assert_can_perform`/`DOMAIN_ACTIONS`, que sigue gobernando exclusivamente las acciones/escritura dentro del dominio propio del operador
- El orquestador es un dispatcher determinístico (no un LLM/`sub_agents` de ADK): el ruteo lo decide `ROLE_DOMAIN` (fijo, 1:1), no una interpretación de intención

### Reglas duras
- Ningún tool nuevo se agrega a un agente sin verificar `permissions_service.py`
- No mezclar lógica de negocio de un dominio (ej. cálculo de stock) dentro de otro agente — la lectura cruzada autorizada vía `cross_domain_reads.py` no viola esto: la lógica de consulta vive una sola vez, en `services/*_queries.py`, nunca duplicada
- `services/cross_domain_reads.py` nunca expone un verbo de mutación (`registrar_`, `crear_`, `actualizar_`, `eliminar_`) — es solo lectura, sin excepción
- Toda acción de un agente que modifica datos (crear orden, registrar movimiento) debe loguearse con operator_id + rol + timestamp

### No tocar sin confirmación
- `permissions_service.py` — cambios acá afectan a los 3 agentes
- `tools.py` de cada agente — agregar un tool sin auditar el permiso correspondiente es el vector de riesgo #1
- `services/cross_domain_reads.py` — es la única puerta de lectura cruzada entre dominios; cualquier cambio acá afecta el modelo de permisos de los 3 agentes
