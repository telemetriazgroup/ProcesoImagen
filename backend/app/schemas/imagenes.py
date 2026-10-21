from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ImagenPropuestaOut(BaseModel):
    imagen_id: uuid.UUID
    codigo_propuesto: str | None = None
    tipo: str = "MANUAL"
    confianza: float | None = None
    orientacion: str | None = None
    bbox: list[Any] = Field(default_factory=list)
    sin_deteccion: bool = True
    mensaje: str
    url_imagen: str
    url_thumb: str | None = None
    fuente: str | None = None
    observaciones: str | None = None
    tiempo_proceso_s: float | None = None
    pasos: list[str] = Field(default_factory=list)
    creado_en: datetime | None = None

    model_config = {"from_attributes": True}
