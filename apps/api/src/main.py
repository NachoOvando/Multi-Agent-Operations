"""Punto de entrada FastAPI del backend.

Monta routers/agents.py. La construcción real de los 3 Runner de Google ADK
(uno por dominio, vía agents/orchestrator.py::get_runner_for_domain) ocurre
al boot de esta app — no por request — porque el tool-set final de cada
dominio es estático (ver docstring de orchestrator.py).

TODO: implementar el `lifespan` que pre-construye los Runners al arrancar,
una vez que google-adk esté instalado y agents/<dominio>/agent.py dejen de
ser stubs. Correr con: `uvicorn apps.api.src.main:app --reload` (una vez que
las dependencias de requirements.txt estén instaladas).
"""

from __future__ import annotations

from fastapi import FastAPI

from apps.api.src.routers import agents

app = FastAPI(title="Agentes operativos — Compras / Almacén / Planificación")

app.include_router(agents.router)
