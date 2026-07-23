"""Punto de entrada FastAPI del backend.

Monta `routers/auth.py` (login) y `routers/agents.py` (mensajería). El
`lifespan` pre-construye los 3 Runner de Google ADK (uno por dominio, vía
`agents/orchestrator.py::get_runner_for_domain`, ya lazy-cacheada) al boot —
no por request — porque el tool-set final de cada dominio es estático (ver
docstring de orchestrator.py). Pre-construirlos acá evita latencia en el
primer request y hace fallar el boot rápido si `DATABASE_URL`/ADK están mal
configurados, en vez de fallar recién en el primer mensaje de un operador.

Correr con: `uvicorn apps.api.src.main:app --reload` desde la raíz del repo
(los imports son absolutos, `from apps.api.src...` — ver railway.json en la
raíz para el equivalente de producción).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.src.agents.orchestrator import get_runner_for_domain
from apps.api.src.routers import agents, auth
from apps.api.src.services.permissions_service import Domain


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    for domain in Domain:
        get_runner_for_domain(domain)
    yield


app = FastAPI(
    title="Agentes operativos — Compras / Almacén / Planificación",
    lifespan=lifespan,
)

# CORS: origen único desde env (fail-closed — sin ALLOWED_ORIGIN configurada,
# no se permite ningún origen de browser, nunca "*" por default). Auth es
# Bearer (no cookie), por eso allow_credentials=False.
_allowed_origin = os.environ.get("ALLOWED_ORIGIN")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_allowed_origin] if _allowed_origin else [],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)

app.include_router(auth.router)
app.include_router(agents.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Healthcheck de Railway (`railway.json`). Sin auth — no expone datos."""
    return {"status": "ok"}
