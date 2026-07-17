"""Router HTTP de entrada al orquestador. Sin lógica de negocio ni SQL acá.

TODO: agregar el endpoint real (ej. POST /api/agents/{operator_id}/messages)
que reciba la consulta del operador y delegue en
agents/orchestrator.py::handle_query — una vez que el orquestador esté
conectado a google-adk (ver TODOs en orchestrator.py).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/agents", tags=["agents"])
