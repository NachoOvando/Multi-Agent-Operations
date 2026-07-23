"""Dependencies de FastAPI relacionadas a identidad (autenticación).

`get_current_operator` es, desde este slice, la ÚNICA fuente válida de
`operator_id` en cualquier endpoint protegido — nunca un path/body param.
Cualquier router que necesite saber "quién hace la request" debe usar
`Depends(get_current_operator)`, nunca aceptar `operator_id` del cliente.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from apps.api.src.services.auth_service import InvalidTokenError, decode_access_token

_BEARER_PREFIX = "Bearer "


@dataclass(frozen=True)
class CurrentOperator:
    operator_id: str
    role: str


def get_current_operator(
    authorization: str | None = Header(default=None),
) -> CurrentOperator:
    """Lee el header `Authorization: Bearer <token>`, decodifica el JWT propio
    del backend (`services/auth_service.py`) y devuelve el operador
    autenticado. Fail-closed: cualquier ausencia/formato/token inválido
    levanta 401 — nunca se asume una identidad por default.
    """
    if not authorization or not authorization.startswith(_BEARER_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[len(_BEARER_PREFIX) :].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return CurrentOperator(operator_id=claims.operator_id, role=claims.role)
