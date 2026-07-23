"""Router HTTP de autenticación. Sin lógica de negocio ni SQL acá — delega
toda la lógica real a `services/auth_service.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.src.db.session import get_db
from apps.api.src.schemas.auth import LoginRequest, LoginResponse, OperatorSummary
from apps.api.src.services.auth_service import (
    InvalidCredentialsError,
    authenticate_operator,
    issue_access_token,
)
from apps.api.src.services.permissions_service import ROLE_DOMAIN, Role

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, session: Session = Depends(get_db)) -> LoginResponse:
    """Login por usuario + password (sin auto-registro — las cuentas se
    provisionan con `scripts/create_operator.py`).

    Emite un JWT propio (HS256, firmado con `JWT_SECRET_KEY`) que se
    convierte en la única fuente válida de identidad para el resto de la API
    — ver `security/dependencies.py::get_current_operator`. Cualquier
    combinación usuario/password inválida devuelve el mismo 401 genérico
    (fail-closed, sin distinguir "usuario inexistente" de "password
    incorrecta").
    """
    try:
        operator = authenticate_operator(body.username, body.password, session)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        ) from exc

    access_token, expires_at = issue_access_token(operator)
    domain = ROLE_DOMAIN[Role(operator.role)]

    return LoginResponse(
        access_token=access_token,
        expires_at=expires_at,
        operator=OperatorSummary(
            operator_id=operator.operator_id,
            role=operator.role,
            domain=domain.value,
        ),
    )
