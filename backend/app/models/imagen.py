from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Imagen(Base):
    __tablename__ = "imagenes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ruta_imagen: Mapped[str] = mapped_column(Text, nullable=False)
    ruta_thumb: Mapped[str | None] = mapped_column(Text, nullable=True)
    codigo_ocr: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tipo_deteccion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confianza: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    orientacion: Mapped[str | None] = mapped_column(String(12), nullable=True)
    sin_deteccion: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fuente: Mapped[str | None] = mapped_column(String(80), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    tiempo_proceso_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    registro = relationship("RegistroEquipo", back_populates="imagen", uselist=False)
