#!/usr/bin/env python3
"""CLI Fase 0.5 — analiza una imagen y muestra el pipeline paso a paso."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.piloto_pipeline import analizar_imagen  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Piloto OCR paso a paso (Fase 0.5)")
    parser.add_argument("imagen", type=Path, help="Ruta a JPEG/PNG")
    parser.add_argument(
        "--storage",
        type=Path,
        default=ROOT / "storage",
        help="Directorio storage (default: ./storage)",
    )
    args = parser.parse_args()

    if not args.imagen.is_file():
        print(f"No existe: {args.imagen}", file=sys.stderr)
        return 1

    data = args.imagen.read_bytes()
    resultado = analizar_imagen(data, args.storage)
    out_dir = args.storage / "piloto" / resultado.run_id

    print(f"\n=== Piloto 0.5 · run_id={resultado.run_id} ===")
    print(f"Motor OCR: {resultado.motor_ocr}")
    if resultado.error_ocr:
        print(f"Aviso OCR: {resultado.error_ocr}")

    print("\nPasos:")
    for p in resultado.pasos:
        print(f"  [{p.id}] {p.titulo}")
        print(f"       {p.descripcion}")
        print(f"       → {out_dir / p.archivo}")

    print("\nBloques detectados:")
    if not resultado.bloques:
        print("  (ninguno)")
    for b in resultado.bloques:
        marca = "NUM" if b.es_numero else "TXT"
        print(f"  [{marca}] {b.texto!r}  conf={b.confianza}")

    print("\nNúmeros detectados:", ", ".join(resultado.numeros_detectados) or "(ninguno)")
    print(f"\nReporte JSON: {out_dir / 'reporte.json'}")
    print(json.dumps({"numeros": resultado.numeros_detectados, "texto": resultado.texto_completo}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
