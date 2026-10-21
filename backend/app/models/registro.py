from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class RegistroEquipo(Base):
    __tablename__ = "registros_equipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    imagen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imagenes.id"), nullable=False, unique=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tipo_deteccion: Mapped[str] = mapped_column(String(20), nullable=False)
    codigo_ocr: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confianza: Mapped[float | None] = mapped_column(Float, nullable=True)
    validado_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ruta_imagen: Mapped[str] = mapped_column(Text, nullable=False)
    orientacion: Mapped[str | None] = mapped_column(String(12), nullable=True)
    fuente: Mapped[str | None] = mapped_column(String(80), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    tiempo_proceso_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    imagen = relationship("Imagen", back_populates="registro")
