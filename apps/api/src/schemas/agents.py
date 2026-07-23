"""Contratos Pydantic del endpoint de mensajería (`routers/agents.py`).

`operator_id` deliberadamente NO forma parte de `MessageRequest` — sale
exclusivamente de `Depends(get_current_operator)` (ver
security/dependencies.py). Aceptarlo acá como campo del body sería reabrir el
gap de identidad que este slice cierra.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    reply: str
