"""Integración PaddleOCR (Fase 1)."""

from typing import Any


def run_ocr(image_bytes: bytes) -> list[dict[str, Any]]:
    """Placeholder Fase 0: sin motor OCR aún.

    Retorno esperado Fase 1:
    [{"texto": str, "bbox": list, "confianza": float, "angulo": float}, ...]
    """
    _ = image_bytes
    return []
