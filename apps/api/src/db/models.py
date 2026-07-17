"""Modelos SQLAlchemy.

`Operator` es la fuente de verdad temporal de operator_id -> role mientras Auth.js
no exista. Cuando Auth.js esté listo, esta tabla puede seguir usándose como la
tabla de roles de la app (Auth.js valida identidad; esta tabla mapea esa
identidad a un rol de dominio) — permissions_service.py no depende de esa
decisión, solo de que exista un Operator con operator_id + role.
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
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
