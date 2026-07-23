"""Autenticación (identidad) — eje distinto y previo a `permissions_service.py`
(autorización). Este módulo responde "quién es" (usuario + password -> JWT);
`permissions_service.py` sigue respondiendo "qué puede hacer" a partir del
`operator_id` que sale de acá. No se toca `permissions_service.py` en este
slice ni se duplica su lógica.

Principio de seguridad central (ver plan de auth): FastAPI emite y verifica
su propio JWT con `PyJWT` (HS256, `JWT_SECRET_KEY`). Next.js/Auth.js nunca
decodifica este token — solo lo reenvía como `Authorization: Bearer <token>`.
Acá adentro es el único lugar del backend que conoce `JWT_SECRET_KEY`.

Hash de passwords con el paquete `bcrypt` directo (no `passlib`, que tiene un
conflicto conocido con `bcrypt>=4.1` — ver requirements.txt).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.src.db.models import Operator
from apps.api.src.services.permissions_service import Role

_ALGORITHM = "HS256"
_DEFAULT_EXPIRES_MINUTES = 480

# Hash "señuelo" contra el que se compara cuando el username no existe, para
# que `authenticate_operator` tarde aproximadamente lo mismo exista o no el
# usuario (mitiga enumeración de usernames por timing). Se calcula una sola
# vez, perezosamente (bcrypt es intencionalmente costoso).
_dummy_hash_cache: str | None = None


class InvalidCredentialsError(Exception):
    """Usuario o password incorrectos.

    Mensaje siempre genérico hacia el caller — nunca revela cuál de los dos
    falló (mismo espíritu fail-closed que `UnknownOperatorError` en
    permissions_service.py).
    """


class InvalidTokenError(Exception):
    """El token es inexistente, está mal formado, expiró o su firma no es válida."""


@dataclass(frozen=True)
class TokenClaims:
    operator_id: str
    role: str


def hash_password(password: str) -> str:
    """Hashea una password en texto plano con bcrypt (cost factor default)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Compara una password en texto plano contra un hash bcrypt.

    Fail-closed: cualquier hash mal formado se trata como "no coincide", nunca
    como error que propague detalles internos.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _get_dummy_hash() -> str:
    global _dummy_hash_cache
    if _dummy_hash_cache is None:
        _dummy_hash_cache = hash_password("dummy-password-for-timing-safety")
    return _dummy_hash_cache


def authenticate_operator(username: str, password: str, session: Session) -> Operator:
    """Verifica username + password. Fail-closed: si el username no existe o
    la password no coincide, levanta `InvalidCredentialsError` con el mismo
    mensaje genérico en ambos casos (no distinguir "usuario inexistente" de
    "password incorrecta" hacia el cliente).
    """
    operator = session.scalar(select(Operator).where(Operator.username == username))
    stored_hash = operator.password_hash if operator is not None else _get_dummy_hash()

    if not verify_password(password, stored_hash) or operator is None:
        raise InvalidCredentialsError("usuario o contraseña incorrectos")

    return operator


def _jwt_secret_key() -> str:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY no está configurada. Definila como variable de entorno "
            "(nunca hardcodeada en el código)."
        )
    return secret


def _jwt_expires_minutes() -> int:
    raw = os.environ.get("JWT_EXPIRES_MINUTES")
    if not raw:
        return _DEFAULT_EXPIRES_MINUTES
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError("JWT_EXPIRES_MINUTES debe ser un entero (minutos).") from exc


def issue_access_token(operator: Operator) -> tuple[str, datetime]:
    """Emite un JWT HS256 con claims `{sub: operator_id, role, iat, exp}`.

    Devuelve `(token, expires_at)` — `expires_at` en UTC, para que el caller
    (routers/auth.py) lo exponga en `LoginResponse.expires_at` sin tener que
    volver a decodificar el token que acaba de emitir.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=_jwt_expires_minutes())

    claims = {
        "sub": operator.operator_id,
        "role": operator.role,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(claims, _jwt_secret_key(), algorithm=_ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> TokenClaims:
    """Decodifica y valida un JWT emitido por `issue_access_token`.

    Fail-closed: cualquier fallo de firma/formato/expiración, claims
    incompletos, o un claim `role` que no sea un `Role` conocido, levanta
    `InvalidTokenError` — nunca se asume un operador/rol por default.
    """
    try:
        payload = jwt.decode(token, _jwt_secret_key(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("token inválido o expirado") from exc

    operator_id = payload.get("sub")
    role = payload.get("role")
    if not operator_id or not role:
        raise InvalidTokenError("token con claims incompletos")

    try:
        Role(role)
    except ValueError as exc:
        raise InvalidTokenError("token con un rol desconocido") from exc

    return TokenClaims(operator_id=operator_id, role=role)
