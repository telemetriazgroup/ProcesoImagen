#!/usr/bin/env python3
"""Evaluación Fase 1: recorre ground_truth y mide precisión del pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.pipeline import detect_code  # noqa: E402
from app.core.rules import codes_match, normalize_code  # noqa: E402


def load_gt(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalúa OCR+reglas contra dataset Fase 0")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "dataset",
        help="Carpeta dataset (images + ground_truth.csv)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "reportes",
        help="Directorio de reportes",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limitar N imágenes (0=todas)")
    parser.add_argument("--no-rotations", action="store_true")
    args = parser.parse_args()

    gt_path = args.dataset / "ground_truth.csv"
    images_dir = args.dataset / "images"
    if not gt_path.is_file():
        print(f"No existe {gt_path}", file=sys.stderr)
        return 1

    rows = load_gt(gt_path)
    if args.limit > 0:
        rows = rows[: args.limit]

    results: list[dict] = []
    by_tipo: dict[str, list[bool]] = defaultdict(list)
    by_orient: dict[str, list[bool]] = defaultdict(list)
    by_dif: dict[str, list[bool]] = defaultdict(list)
    times: list[float] = []

    print(f"Evaluando {len(rows)} imágenes…")
    for i, row in enumerate(rows, 1):
        nombre = row["nombre_archivo"]
        truth = row["codigo_correcto"]
        tipo = row.get("tipo") or "OTRO"
        orient = row.get("orientacion") or "n/a"
        dif = row.get("dificultad") or "normal"
        img_path = images_dir / nombre
        if not img_path.is_file():
            results.append(
                {
                    "nombre_archivo": nombre,
                    "codigo_correcto": truth,
                    "codigo_pred": None,
                    "ok": False,
                    "causa": "imagen_faltante",
                    "tipo": tipo,
                }
            )
            by_tipo[tipo].append(False)
            continue

        t0 = time.perf_counter()
        try:
            det = detect_code(
                img_path.read_bytes(),
                try_rotations=not args.no_rotations,
            )
            elapsed = time.perf_counter() - t0
            times.append(elapsed)
            pred = det.get("codigo")
            ok = codes_match(pred, truth)
            causa = None
            if not ok:
                if det.get("sin_deteccion"):
                    causa = "sin_deteccion"
                elif pred and normalize_code(pred) != normalize_code(truth):
                    causa = "regla_o_ocr_incorrecto"
                else:
                    causa = "desconocida"
            item = {
                "nombre_archivo": nombre,
                "codigo_correcto": truth,
                "codigo_pred": pred,
                "tipo_gt": tipo,
                "tipo_pred": det.get("tipo"),
                "fuente": det.get("fuente"),
                "confianza": det.get("confianza"),
                "rotacion": det.get("rotacion"),
                "ok": ok,
                "causa": causa,
                "segundos": round(elapsed, 3),
                "orientacion": orient,
                "dificultad": dif,
            }
        except Exception as exc:  # noqa: BLE001 — reporte de evaluación
            elapsed = time.perf_counter() - t0
            times.append(elapsed)
            ok = False
            item = {
                "nombre_archivo": nombre,
                "codigo_correcto": truth,
                "codigo_pred": None,
                "ok": False,
                "causa": f"error:{exc}",
                "tipo_gt": tipo,
                "segundos": round(elapsed, 3),
            }
        results.append(item)
        by_tipo[tipo].append(ok)
        by_orient[orient].append(ok)
        by_dif[dif].append(ok)
        mark = "OK" if ok else "FAIL"
        print(f"[{i}/{len(rows)}] {mark} {nombre} truth={truth} pred={item.get('codigo_pred')}")

    def rate(flags: list[bool]) -> float | None:
        return round(sum(flags) / len(flags), 4) if flags else None

    summary = {
        "fecha": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "aciertos": sum(1 for r in results if r.get("ok")),
        "precision_global": rate([bool(r.get("ok")) for r in results]),
        "precision_por_tipo": {k: rate(v) for k, v in sorted(by_tipo.items())},
        "precision_por_orientacion": {k: rate(v) for k, v in sorted(by_orient.items())},
        "precision_por_dificultad": {k: rate(v) for k, v in sorted(by_dif.items())},
        "tiempo_medio_s": round(sum(times) / len(times), 3) if times else None,
        "tiempo_p95_s": round(sorted(times)[int(len(times) * 0.95) - 1], 3) if times else None,
        "fallos": [r for r in results if not r.get("ok")],
    }

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = args.out / f"eval_fase1_{stamp}.json"
    md_path = args.out / f"eval_fase1_{stamp}.md"
    latest_json = args.out / "eval_fase1_latest.json"
    latest_md = args.out / "eval_fase1_latest.md"

    payload = {"summary": summary, "results": results}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")

    md = [
        f"# Evaluación Fase 1 — {summary['fecha']}",
        "",
        f"- Total: **{summary['total']}**",
        f"- Aciertos: **{summary['aciertos']}**",
        f"- Precisión global: **{summary['precision_global']}**",
        f"- Tiempo medio: **{summary['tiempo_medio_s']} s**",
        f"- Tiempo p95: **{summary['tiempo_p95_s']} s**",
        "",
        "## Por tipo",
        "",
    ]
    for k, v in summary["precision_por_tipo"].items():
        md.append(f"- `{k}`: {v}")
    md.extend(["", "## Por orientación", ""])
    for k, v in summary["precision_por_orientacion"].items():
        md.append(f"- `{k}`: {v}")
    md.extend(["", "## Fallos", ""])
    for f in summary["fallos"][:80]:
        md.append(
            f"- `{f['nombre_archivo']}` truth=`{f.get('codigo_correcto')}` "
            f"pred=`{f.get('codigo_pred')}` causa=`{f.get('causa')}`"
        )
    if len(summary["fallos"]) > 80:
        md.append(f"- … y {len(summary['fallos']) - 80} más (ver JSON)")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    print("\n=== RESUMEN ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nReporte: {md_path}")
    print(f"JSON:    {json_path}")

    # Gate informativo (no falla el proceso; Fase 1 itera)
    prec = summary["precision_global"] or 0
    if prec >= 0.85:
        print("GATE: precisión global ≥ 85% — cumplido")
    else:
        print("GATE: precisión global < 85% — iterar reglas/preprocess")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
