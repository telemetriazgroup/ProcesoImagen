"""Pipeline piloto Fase 0.5 — procesamiento visual paso a paso.

No aplica reglas ZGRU/Serial: detecta texto y números genéricos.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

_NUMBER_RE = re.compile(r"\d+")


@dataclass
class Paso:
    id: str
    titulo: str
    descripcion: str
    archivo: str


@dataclass
class BloqueOCR:
    texto: str
    confianza: float
    bbox: list[list[float]]
    es_numero: bool


@dataclass
class ResultadoPiloto:
    run_id: str
    motor_ocr: str
    pasos: list[Paso] = field(default_factory=list)
    bloques: list[BloqueOCR] = field(default_factory=list)
    numeros_detectados: list[str] = field(default_factory=list)
    texto_completo: str = ""
    error_ocr: str | None = None
    codigo_propuesto: str = ""
    confianza_propuesta: float = 0.0
    validacion: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "motor_ocr": self.motor_ocr,
            "pasos": [asdict(p) for p in self.pasos],
            "bloques": [asdict(b) for b in self.bloques],
            "numeros_detectados": self.numeros_detectados,
            "texto_completo": self.texto_completo,
            "error_ocr": self.error_ocr,
            "codigo_propuesto": self.codigo_propuesto,
            "confianza_propuesta": self.confianza_propuesta,
            "validacion": self.validacion,
        }


def _decode_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen (use JPEG/PNG).")
    return img


def _save_bgr(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def _save_gray(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def _resize_max(image: np.ndarray, max_side: int = 1600) -> np.ndarray:
    h, w = image.shape[:2]
    side = max(h, w)
    if side <= max_side:
        return image
    scale = max_side / side
    return cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def _run_rapidocr(image_bgr: np.ndarray) -> tuple[list[BloqueOCR], str | None]:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        return [], f"RapidOCR no instalado: {exc}"

    engine = RapidOCR()
    # RapidOCR acepta ndarray BGR/RGB según versión; pass path-like via numpy
    result, _ = engine(image_bgr)
    bloques: list[BloqueOCR] = []
    if not result:
        return [], None

    for item in result:
        # item: [bbox, text, score]
        bbox_raw, texto, score = item[0], item[1], float(item[2])
        bbox = [[float(p[0]), float(p[1])] for p in bbox_raw]
        texto = str(texto).strip()
        if not texto:
            continue
        es_numero = bool(_NUMBER_RE.search(texto))
        bloques.append(
            BloqueOCR(
                texto=texto,
                confianza=round(score, 4),
                bbox=bbox,
                es_numero=es_numero,
            )
        )
    return bloques, None


def _draw_overlay(image_bgr: np.ndarray, bloques: list[BloqueOCR], only_numbers: bool = False) -> np.ndarray:
    out = image_bgr.copy()
    for b in bloques:
        if only_numbers and not b.es_numero:
            continue
        pts = np.array(b.bbox, dtype=np.int32)
        color = (40, 180, 80) if b.es_numero else (80, 160, 220)
        cv2.polylines(out, [pts], isClosed=True, color=color, thickness=2)
        x, y = int(pts[0][0]), max(int(pts[0][1]) - 6, 14)
        label = f"{b.texto} ({b.confianza:.2f})"
        cv2.putText(
            out,
            label,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
    return out


def _extract_numbers(bloques: list[BloqueOCR]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for b in bloques:
        for match in _NUMBER_RE.findall(b.texto):
            if match not in seen:
                seen.add(match)
                found.append(match)
    return found


def _proponer_codigo(bloques: list[BloqueOCR], numeros: list[str]) -> tuple[str, float]:
    """Elige el mejor candidato para validación humana."""
    numeric_blocks = [b for b in bloques if b.es_numero]
    if numeric_blocks:
        def score(b: BloqueOCR) -> tuple[int, float]:
            digits = "".join(_NUMBER_RE.findall(b.texto))
            return (len(digits), b.confianza)

        best = max(numeric_blocks, key=score)
        return best.texto.strip(), best.confianza
    if numeros:
        longest = max(numeros, key=len)
        return longest, 0.0
    if bloques:
        best = max(bloques, key=lambda b: b.confianza)
        return best.texto.strip(), best.confianza
    return "", 0.0


def analizar_imagen(image_bytes: bytes, storage_root: Path) -> ResultadoPiloto:
    """Ejecuta el pipeline piloto y persiste imágenes intermedias."""
    run_id = str(uuid.uuid4())
    out_dir = Path(storage_root) / "piloto" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    resultado = ResultadoPiloto(run_id=run_id, motor_ocr="rapidocr")

    original = _resize_max(_decode_image(image_bytes))
    _save_bgr(out_dir / "00_original.jpg", original)
    resultado.pasos.append(
        Paso(
            id="00_original",
            titulo="Original",
            descripcion="Imagen recibida (redimensionada si supera 1600 px en el lado mayor).",
            archivo="00_original.jpg",
        )
    )

    gris = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    _save_gray(out_dir / "01_gris.jpg", gris)
    resultado.pasos.append(
        Paso(
            id="01_gris",
            titulo="Escala de grises",
            descripcion="Elimina color para estabilizar el contraste antes del OCR.",
            archivo="01_gris.jpg",
        )
    )

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    contraste = clahe.apply(gris)
    _save_gray(out_dir / "02_clahe.jpg", contraste)
    resultado.pasos.append(
        Paso(
            id="02_clahe",
            titulo="CLAHE (contraste)",
            descripcion="Mejora contraste local: útil en placas con reflejos o sombra.",
            archivo="02_clahe.jpg",
        )
    )

    denoise = cv2.bilateralFilter(contraste, d=7, sigmaColor=50, sigmaSpace=50)
    _save_gray(out_dir / "03_denoise.jpg", denoise)
    resultado.pasos.append(
        Paso(
            id="03_denoise",
            titulo="Denoise",
            descripcion="Filtro bilateral: reduce ruido preservando bordes de caracteres.",
            archivo="03_denoise.jpg",
        )
    )

    binaria = cv2.adaptiveThreshold(
        denoise,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )
    _save_gray(out_dir / "04_binaria.jpg", binaria)
    resultado.pasos.append(
        Paso(
            id="04_binaria",
            titulo="Binarización",
            descripcion="Umbral adaptativo. Referencia visual; el OCR usa la imagen CLAHE en color.",
            archivo="04_binaria.jpg",
        )
    )

    # OCR sobre versión de alto contraste en 3 canales
    ocr_input = cv2.cvtColor(contraste, cv2.COLOR_GRAY2BGR)
    bloques, err = _run_rapidocr(ocr_input)
    resultado.bloques = bloques
    resultado.error_ocr = err
    resultado.numeros_detectados = _extract_numbers(bloques)
    resultado.texto_completo = " | ".join(b.texto for b in bloques)
    resultado.motor_ocr = "rapidocr" if err is None else "ninguno"
    propuesto, conf = _proponer_codigo(bloques, resultado.numeros_detectados)
    resultado.codigo_propuesto = propuesto
    resultado.confianza_propuesta = round(float(conf), 4)

    overlay = _draw_overlay(original, bloques, only_numbers=False)
    _save_bgr(out_dir / "05_ocr_overlay.jpg", overlay)
    resultado.pasos.append(
        Paso(
            id="05_ocr_overlay",
            titulo="OCR + cajas",
            descripcion="Texto detectado con confianza. Verde = contiene dígitos; azul = solo letras/símbolos.",
            archivo="05_ocr_overlay.jpg",
        )
    )

    numeros_overlay = _draw_overlay(original, bloques, only_numbers=True)
    _save_bgr(out_dir / "06_numeros.jpg", numeros_overlay)
    resultado.pasos.append(
        Paso(
            id="06_numeros",
            titulo="Solo números",
            descripcion="Bloques que contienen al menos un dígito (filtro del piloto 0.5).",
            archivo="06_numeros.jpg",
        )
    )

    reporte_path = out_dir / "reporte.json"
    reporte_path.write_text(
        json.dumps(resultado.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return resultado
