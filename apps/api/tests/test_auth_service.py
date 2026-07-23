"""Tests de `services/auth_service.py` — identidad (hash/verify, login, JWT).

No cubre `permissions_service.py` (ver test_permissions_service.py aparte) ni
los routers HTTP (fuera de este slice de tests, que se limita a los servicios
puntuales que el plan de auth agregó).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy.orm import Session

from apps.api.src.db.models import Operator
from apps.api.src.services.auth_service import (
    InvalidCredentialsError,
    InvalidTokenError,
    authenticate_operator,
    decode_access_token,
    hash_password,
    issue_access_token,
    verify_password,
)

_JWT_SECRET = "test-secret-key-not-for-production"


@pytest.fixture(autouse=True)
def _jwt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Todos los tests de este archivo corren con un JWT_SECRET_KEY conocido.

    `auth_service` falla rápido (RuntimeError) si la variable no está
    definida — este fixture evita repetir el setup en cada test.
    """
    monkeypatch.setenv("JWT_SECRET_KEY", _JWT_SECRET)
    monkeypatch.delenv("JWT_EXPIRES_MINUTES", raising=False)


# --- hash_password / verify_password -----------------------------------


def test_hash_password_does_not_return_plaintext() -> None:
    password = "mi-password-super-secreta"

    hashed = hash_password(password)

    assert hashed != password
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_verify_password_true_with_correct_password() -> None:
    password = "mi-password-super-secreta"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_false_with_incorrect_password() -> None:
    hashed = hash_password("mi-password-super-secreta")

    assert verify_password("otra-password", hashed) is False


def test_verify_password_false_with_malformed_hash_fail_closed() -> None:
    # Fail-closed: un hash mal formado nunca debe propagar la excepción de
    # bcrypt hacia el caller, ni tratarse como "coincide".
    assert verify_password("cualquier-password", "esto-no-es-un-hash-bcrypt") is False


# --- authenticate_operator -----------------------------------------------


def test_authenticate_operator_success(
    session: Session, operator: Operator, operator_password: str
) -> None:
    result = authenticate_operator(operator.username, operator_password, session)

    assert result.operator_id == operator.operator_id
    assert result.username == operator.username


def test_authenticate_operator_wrong_password_raises_invalid_credentials(
    session: Session, operator: Operator
) -> None:
    with pytest.raises(InvalidCredentialsError):
        authenticate_operator(operator.username, "password-incorrecta", session)


def test_authenticate_operator_unknown_username_raises_invalid_credentials(
    session: Session,
) -> None:
    with pytest.raises(InvalidCredentialsError):
        authenticate_operator("usuario-que-no-existe", "cualquier-password", session)


def test_authenticate_operator_same_error_for_both_failure_modes(
    session: Session, operator: Operator
) -> None:
    # No debe distinguir "usuario inexistente" de "password incorrecta" hacia
    # el caller — mismo tipo de excepción y mismo mensaje en ambos casos.
    with pytest.raises(InvalidCredentialsError) as wrong_password_exc:
        authenticate_operator(operator.username, "password-incorrecta", session)

    with pytest.raises(InvalidCredentialsError) as unknown_user_exc:
        authenticate_operator("usuario-que-no-existe", "cualquier-password", session)

    assert str(wrong_password_exc.value) == str(unknown_user_exc.value)


# --- issue_access_token / decode_access_token -----------------------------


def test_issue_and_decode_access_token_roundtrip(operator: Operator) -> None:
    token, expires_at = issue_access_token(operator)

    claims = decode_access_token(token)

    assert claims.operator_id == operator.operator_id
    assert claims.role == operator.role
    assert isinstance(token, str)
    assert expires_at > datetime.now(timezone.utc)


def test_decode_access_token_expired_raises_invalid_token(operator: Operator) -> None:
    now = datetime.now(timezone.utc)
    expired_claims = {
        "sub": operator.operator_id,
        "role": operator.role,
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_claims, _JWT_SECRET, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        decode_access_token(expired_token)


def test_decode_access_token_wrong_secret_raises_invalid_token(operator: Operator) -> None:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": operator.operator_id,
        "role": operator.role,
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    token_signed_with_other_secret = jwt.encode(
        claims, "otro-secret-distinto-de-al-menos-32-bytes", algorithm="HS256"
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token_signed_with_other_secret)


def test_decode_access_token_malformed_raises_invalid_token() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("esto-no-es-un-jwt")


def test_decode_access_token_incomplete_claims_raises_invalid_token() -> None:
    token_without_role = jwt.encode({"sub": "op-test-1"}, _JWT_SECRET, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token_without_role)


def test_decode_access_token_unknown_role_raises_invalid_token() -> None:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "op-test-1",
        "role": "rol-que-no-existe",
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    token = jwt.encode(claims, _JWT_SECRET, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
