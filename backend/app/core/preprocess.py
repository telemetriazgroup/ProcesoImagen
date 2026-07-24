"""Preprocesamiento OpenCV (Fase 1).

Pasos previstos (activables por config):
- escala de grises
- CLAHE (contraste)
- corrección de inclinación
- redimensionado
"""


def preprocess_image(image_bytes: bytes, steps: list[str] | None = None) -> bytes:
    """Placeholder Fase 0: retorna la imagen sin cambios."""
    _ = steps
    return image_bytes
