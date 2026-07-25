"""Motor OCR Fase 1 — RapidOCR (ONNX / PP-OCR)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import cv2
import numpy as np

from app.core.preprocess import decode_image, preprocess_bgr


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _bbox_angle(bbox: list[list[float]]) -> float:
    if len(bbox) < 2:
        return 0.0
    x1, y1 = bbox[0]
    x2, y2 = bbox[1]
    return float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))


def run_ocr_bgr(image_bgr: np.ndarray) -> list[dict[str, Any]]:
    engine = _engine()
    result, _ = engine(image_bgr)
    bloques: list[dict[str, Any]] = []
    if not result:
        return bloques
    for item in result:
        bbox_raw, texto, score = item[0], item[1], float(item[2])
        bbox = [[float(p[0]), float(p[1])] for p in bbox_raw]
        texto = str(texto).strip()
        if not texto:
            continue
        bloques.append(
            {
                "texto": texto,
                "bbox": bbox,
                "confianza": round(score, 4),
                "angulo": round(_bbox_angle(bbox), 2),
            }
        )
    return bloques


def run_ocr(
    image_bytes: bytes,
    *,
    preprocess: bool = True,
    steps: list[str] | None = None,
) -> list[dict[str, Any]]:
    bgr = decode_image(image_bytes)
    if preprocess:
        bgr = preprocess_bgr(bgr, steps=steps)
    return run_ocr_bgr(bgr)


def rotate_bgr(image_bgr: np.ndarray, degrees: int) -> np.ndarray:
    if degrees == 90:
        return cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE)
    if degrees == 180:
        return cv2.rotate(image_bgr, cv2.ROTATE_180)
    if degrees == 270:
        return cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image_bgr
