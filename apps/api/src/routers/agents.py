"""Router HTTP de entrada al orquestador. Sin lógica de negocio ni SQL acá —
delega toda la lógica real a `agents/orchestrator.py::handle_query`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.src.agents.orchestrator import handle_query
from apps.api.src.db.session import get_db
from apps.api.src.schemas.agents import MessageRequest, MessageResponse
from apps.api.src.security.dependencies import CurrentOperator, get_current_operator
from apps.api.src.services.permissions_service import (
    PermissionDeniedError,
    UnknownOperatorError,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/messages", response_model=MessageResponse)
async def post_message(
    body: MessageRequest,
    operator: CurrentOperator = Depends(get_current_operator),
    session: Session = Depends(get_db),
) -> MessageResponse:
    """Envía una consulta al agente especialista del dominio del operador
    autenticado.

    `operator_id` sale exclusivamente de `Depends(get_current_operator)` —
    nunca de un path/body param (ver security/dependencies.py). El
    orquestador resuelve el dominio del operador y despacha al Runner de ADK
    correspondiente; el chequeo de permisos por acción sigue ocurriendo
    dentro de cada tool (assert_can_perform/assert_can_read), sin cambios.
    """
    try:
        reply = await handle_query(operator.operator_id, body.query, session)
    except UnknownOperatorError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado",
        ) from exc

    return MessageResponse(reply=reply)
