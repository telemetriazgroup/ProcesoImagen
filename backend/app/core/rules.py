"""Motor de reglas ZGRU / Serial No (Fase 1)."""

from typing import Any


def extract_code(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Placeholder Fase 0.

    Retorno esperado:
    {
      "codigo": "ZGRU12345",
      "tipo": "ZGRU" | "SERIAL",
      "confianza": 0.95,
      "orientacion": "horizontal" | "vertical",
      "bbox": [...]
    }
    """
    _ = blocks
    return None
