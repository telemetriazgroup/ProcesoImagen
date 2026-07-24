from typing import Literal

from pydantic import BaseModel, Field

TipoDet = Literal["ZGRU", "SERIAL", "OTRO", "MANUAL"]
Orientacion = Literal["horizontal", "vertical", "n/a"]
Dificultad = Literal["normal", "dificil"]


class ValidacionRequest(BaseModel):
    run_id: str
    codigo_correcto: str = Field(..., min_length=1, max_length=80)
    tipo: TipoDet = "OTRO"
    orientacion: Orientacion = "n/a"
    dificultad: Dificultad = "normal"
    notas: str = ""
    # True = el usuario acepta el código propuesto tal cual (mismo valor en codigo_correcto)
    confirmar_propuesto: bool = False


class ValidacionUpdateRequest(BaseModel):
    codigo_correcto: str = Field(..., min_length=1, max_length=80)
    tipo: TipoDet = "OTRO"
    orientacion: Orientacion = "n/a"
    dificultad: Dificultad = "normal"
    notas: str = ""
