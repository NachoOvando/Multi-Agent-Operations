"""Modelos SQLAlchemy.

`Operator` es la fuente de verdad de identidad + rol del backend. Desde el
Slice 1 de auth, FastAPI emite y verifica su propio JWT (ver
services/auth_service.py) — Next.js/Auth.js nunca decodifica ese token, solo
lo reenvía como Bearer (ver docs/architecture.md). `username`/`password_hash`
son los campos de login; `operator_id` sigue siendo la PK y sigue siendo la
única clave que conoce permissions_service.py (esta tabla mapea identidad a
rol de dominio; permissions_service.py no depende de cómo se autenticó esa
identidad, solo de que exista un Operator con operator_id + role).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Operator(Base):
    __tablename__ = "operators"

    operator_id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
