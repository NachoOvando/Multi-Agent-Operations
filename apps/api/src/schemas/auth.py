"""Contratos Pydantic del endpoint de auth (`routers/auth.py`).

Consumidos por el subagente frontend-especialista contra
`POST /api/auth/login` — ver resumen de contrato entregado al cierre del
slice para el shape exacto.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=200)


class OperatorSummary(BaseModel):
    operator_id: str
    role: str
    domain: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    operator: OperatorSummary
