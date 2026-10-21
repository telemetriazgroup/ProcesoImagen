from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RegistroCreate(BaseModel):
    imagen_id: uuid.UUID
    codigo: str = Field(..., min_length=1, max_length=50)
    tipo: str | None = Field(
        default=None,
        description="ZGRU | SERIAL | CHIP | OTRO | MANUAL. Si se omite, se infiere.",
    )


class RegistroOut(BaseModel):
    id: int
    imagen_id: uuid.UUID
    codigo: str
    tipo_deteccion: str
    codigo_ocr: str | None = None
    confianza: float | None = None
    validado_manual: bool
    ruta_imagen: str
    orientacion: str | None = None
    fuente: str | None = None
    observaciones: str | None = None
    tiempo_proceso_s: float | None = None
    usuario_id: int | None = None
    creado_en: datetime
    url_imagen: str
    url_thumb: str | None = None

    model_config = {"from_attributes": True}


class RegistroListOut(BaseModel):
    total: int
    items: list[RegistroOut]
