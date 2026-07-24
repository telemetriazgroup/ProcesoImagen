"""Retroalimentación humana → dataset Fase 0.

Flujo:
1. Usuario revisa pasos OCR del piloto.
2. Confirma o corrige el código reconocido.
3. Se guarda auditoría en feedback.jsonl.
4. Se copia la imagen a dataset/images/ y se actualiza ground_truth.csv.
5. Las validaciones se pueden editar o eliminar desde la UI.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GT_FIELDS = [
    "nombre_archivo",
    "codigo_correcto",
    "tipo",
    "orientacion",
    "dificultad",
    "notas",
    "run_id",
    "codigo_ocr",
    "confianza_ocr",
    "acierto",
    "validado_en",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    return (slug[:max_len] or "sin_codigo").strip("_")


def _normalize_code(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().upper())


def load_reporte(storage_path: Path, run_id: str) -> dict[str, Any]:
    path = Path(storage_path) / "piloto" / run_id / "reporte.json"
    if not path.is_file():
        raise FileNotFoundError(f"No existe análisis para run_id={run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _feedback_path(dataset_path: Path) -> Path:
    return Path(dataset_path) / "feedback.jsonl"


def _gt_path(dataset_path: Path) -> Path:
    return Path(dataset_path) / "ground_truth.csv"


def _ensure_gt_header(gt_file: Path) -> None:
    if gt_file.exists() and gt_file.stat().st_size > 0:
        return
    gt_file.parent.mkdir(parents=True, exist_ok=True)
    with gt_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=GT_FIELDS)
        writer.writeheader()


def _read_all_feedback(dataset_path: Path) -> list[dict[str, Any]]:
    path = _feedback_path(Path(dataset_path))
    if not path.is_file():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


def _write_all_feedback(dataset_path: Path, items: list[dict[str, Any]]) -> None:
    path = _feedback_path(Path(dataset_path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def _write_ground_truth(gt_file: Path, rows: list[dict[str, str]]) -> None:
    gt_file.parent.mkdir(parents=True, exist_ok=True)
    with gt_file.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=GT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _read_ground_truth(gt_file: Path) -> list[dict[str, str]]:
    if not gt_file.exists() or gt_file.stat().st_size == 0:
        return []
    rows: list[dict[str, str]] = []
    with gt_file.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for existing in reader:
            rows.append({k: existing.get(k, "") or "" for k in GT_FIELDS})
    return rows


def _registro_to_gt_row(registro: dict[str, Any]) -> dict[str, str]:
    return {
        "nombre_archivo": str(registro.get("nombre_archivo") or ""),
        "codigo_correcto": str(registro.get("codigo_correcto") or ""),
        "tipo": str(registro.get("tipo") or "OTRO"),
        "orientacion": str(registro.get("orientacion") or "n/a"),
        "dificultad": str(registro.get("dificultad") or "normal"),
        "notas": str(registro.get("notas") or ""),
        "run_id": str(registro.get("run_id") or ""),
        "codigo_ocr": str(registro.get("codigo_ocr") or ""),
        "confianza_ocr": f"{float(registro.get('confianza_ocr') or 0):.4f}",
        "acierto": "true" if registro.get("acierto") else "false",
        "validado_en": str(registro.get("validado_en") or ""),
    }


def _sync_ground_truth_from_feedback(dataset_path: Path) -> None:
    """Reconstruye ground_truth.csv desde feedback.jsonl (fuente de verdad)."""
    items = _read_all_feedback(dataset_path)
    rows = [_registro_to_gt_row(i) for i in items]
    _write_ground_truth(_gt_path(Path(dataset_path)), rows)


def _upsert_ground_truth(gt_file: Path, row: dict[str, str]) -> None:
    _ensure_gt_header(gt_file)
    rows = _read_ground_truth(gt_file)
    kept: list[dict[str, str]] = []
    for existing in rows:
        same_file = existing["nombre_archivo"] and existing["nombre_archivo"] == row["nombre_archivo"]
        same_run = row["run_id"] and existing["run_id"] == row["run_id"]
        if same_file or same_run:
            continue
        kept.append(existing)
    kept.append(row)
    _write_ground_truth(gt_file, kept)


def _update_run_files(storage_path: Path, registro: dict[str, Any]) -> None:
    run_id = str(registro.get("run_id") or "")
    if not run_id:
        return
    run_dir = Path(storage_path) / "piloto" / run_id
    if not run_dir.is_dir():
        return
    (run_dir / "validacion.json").write_text(
        json.dumps(registro, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    reporte_path = run_dir / "reporte.json"
    if reporte_path.is_file():
        reporte = json.loads(reporte_path.read_text(encoding="utf-8"))
        reporte["validacion"] = {
            "id": registro.get("id"),
            "codigo_correcto": registro.get("codigo_correcto"),
            "acierto": registro.get("acierto"),
            "validado_en": registro.get("validado_en"),
            "nombre_archivo": registro.get("nombre_archivo"),
            "actualizado_en": registro.get("actualizado_en"),
        }
        reporte_path.write_text(
            json.dumps(reporte, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def guardar_validacion(
    *,
    storage_path: Path,
    dataset_path: Path,
    run_id: str,
    codigo_correcto: str,
    tipo: str = "OTRO",
    orientacion: str = "n/a",
    dificultad: str = "normal",
    notas: str = "",
) -> dict[str, Any]:
    reporte = load_reporte(storage_path, run_id)
    if reporte.get("validacion"):
        raise ValueError(
            "Este análisis ya fue validado. Edítalo desde el historial o analiza otra imagen."
        )

    codigo_ok = codigo_correcto.strip()
    if not codigo_ok:
        raise ValueError("El código correcto no puede estar vacío.")

    codigo_ocr = str(reporte.get("codigo_propuesto") or "").strip()
    confianza = float(reporte.get("confianza_propuesta") or 0.0)
    acierto = _normalize_code(codigo_ocr) == _normalize_code(codigo_ok)

    run_dir = Path(storage_path) / "piloto" / run_id
    original = run_dir / "00_original.jpg"
    if not original.is_file():
        raise FileNotFoundError("Falta la imagen original del análisis.")

    images_dir = Path(dataset_path) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    nombre_archivo = f"piloto_{run_id[:8]}_{_safe_slug(codigo_ok)}.jpg"
    destino = images_dir / nombre_archivo
    shutil.copy2(original, destino)

    validacion_id = str(uuid.uuid4())
    registro = {
        "id": validacion_id,
        "run_id": run_id,
        "validado_en": _now_iso(),
        "codigo_ocr": codigo_ocr,
        "codigo_correcto": codigo_ok,
        "acierto": acierto,
        "confianza_ocr": confianza,
        "tipo": tipo,
        "orientacion": orientacion,
        "dificultad": dificultad,
        "notas": notas,
        "nombre_archivo": nombre_archivo,
        "motor_ocr": reporte.get("motor_ocr"),
        "numeros_detectados": reporte.get("numeros_detectados", []),
        "texto_completo": reporte.get("texto_completo", ""),
        "ruta_dataset": str(destino.as_posix()),
    }

    dataset_path = Path(dataset_path)
    dataset_path.mkdir(parents=True, exist_ok=True)
    items = _read_all_feedback(dataset_path)
    items.append(registro)
    _write_all_feedback(dataset_path, items)
    _upsert_ground_truth(_gt_path(dataset_path), _registro_to_gt_row(registro))
    _update_run_files(storage_path, registro)
    return registro


def obtener_validacion(dataset_path: Path, validacion_id: str) -> dict[str, Any]:
    for item in _read_all_feedback(dataset_path):
        if item.get("id") == validacion_id:
            return item
    raise FileNotFoundError(f"Validación no encontrada: {validacion_id}")


def actualizar_validacion(
    *,
    storage_path: Path,
    dataset_path: Path,
    validacion_id: str,
    codigo_correcto: str,
    tipo: str = "OTRO",
    orientacion: str = "n/a",
    dificultad: str = "normal",
    notas: str = "",
) -> dict[str, Any]:
    codigo_ok = codigo_correcto.strip()
    if not codigo_ok:
        raise ValueError("El código correcto no puede estar vacío.")

    items = _read_all_feedback(dataset_path)
    idx = next((i for i, it in enumerate(items) if it.get("id") == validacion_id), None)
    if idx is None:
        raise FileNotFoundError(f"Validación no encontrada: {validacion_id}")

    actual = dict(items[idx])
    old_name = str(actual.get("nombre_archivo") or "")
    codigo_ocr = str(actual.get("codigo_ocr") or "")
    run_id = str(actual.get("run_id") or "")
    acierto = _normalize_code(codigo_ocr) == _normalize_code(codigo_ok)

    images_dir = Path(dataset_path) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    new_name = f"piloto_{run_id[:8]}_{_safe_slug(codigo_ok)}.jpg" if run_id else old_name
    old_path = images_dir / old_name if old_name else None
    new_path = images_dir / new_name

    if old_path and old_path.is_file():
        if new_name != old_name:
            if new_path.exists() and new_path.resolve() != old_path.resolve():
                new_path.unlink()
            old_path.rename(new_path)
    elif run_id:
        # Recuperar imagen desde el run si falta en dataset
        original = Path(storage_path) / "piloto" / run_id / "00_original.jpg"
        if original.is_file():
            shutil.copy2(original, new_path)

    actual.update(
        {
            "codigo_correcto": codigo_ok,
            "tipo": tipo,
            "orientacion": orientacion,
            "dificultad": dificultad,
            "notas": notas,
            "acierto": acierto,
            "nombre_archivo": new_name,
            "ruta_dataset": str(new_path.as_posix()),
            "actualizado_en": _now_iso(),
        }
    )
    items[idx] = actual
    _write_all_feedback(dataset_path, items)
    _sync_ground_truth_from_feedback(dataset_path)
    _update_run_files(storage_path, actual)
    return actual


def eliminar_validacion(
    *,
    storage_path: Path,
    dataset_path: Path,
    validacion_id: str,
    borrar_imagen: bool = True,
) -> dict[str, Any]:
    items = _read_all_feedback(dataset_path)
    idx = next((i for i, it in enumerate(items) if it.get("id") == validacion_id), None)
    if idx is None:
        raise FileNotFoundError(f"Validación no encontrada: {validacion_id}")

    eliminado = items.pop(idx)
    _write_all_feedback(dataset_path, items)
    _sync_ground_truth_from_feedback(dataset_path)

    if borrar_imagen:
        nombre = str(eliminado.get("nombre_archivo") or "")
        if nombre:
            img = Path(dataset_path) / "images" / nombre
            if img.is_file():
                img.unlink()

    # Marcar reporte del run como sin validación (el análisis sigue disponible)
    run_id = str(eliminado.get("run_id") or "")
    if run_id:
        reporte_path = Path(storage_path) / "piloto" / run_id / "reporte.json"
        if reporte_path.is_file():
            reporte = json.loads(reporte_path.read_text(encoding="utf-8"))
            reporte["validacion"] = None
            reporte_path.write_text(
                json.dumps(reporte, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        validacion_path = Path(storage_path) / "piloto" / run_id / "validacion.json"
        if validacion_path.is_file():
            validacion_path.unlink()

    return eliminado


def listar_validaciones(dataset_path: Path, limit: int = 200) -> list[dict[str, Any]]:
    items = _read_all_feedback(dataset_path)
    items_sorted = list(reversed(items))
    return items_sorted[:limit]


def metricas_feedback(dataset_path: Path) -> dict[str, Any]:
    items = _read_all_feedback(dataset_path)
    total = len(items)
    aciertos = sum(1 for i in items if i.get("acierto"))
    correcciones = total - aciertos
    confianzas = [float(i.get("confianza_ocr") or 0) for i in items]
    por_tipo: dict[str, int] = {}
    for i in items:
        t = str(i.get("tipo") or "OTRO")
        por_tipo[t] = por_tipo.get(t, 0) + 1
    return {
        "total_validados": total,
        "aciertos_ocr": aciertos,
        "correcciones_humanas": correcciones,
        "tasa_acierto_ocr": round(aciertos / total, 4) if total else None,
        "confianza_media_ocr": round(sum(confianzas) / total, 4) if total else None,
        "por_tipo": por_tipo,
        "dataset_images": total,
        "ground_truth": str(_gt_path(Path(dataset_path))),
        "feedback_log": str(_feedback_path(Path(dataset_path))),
    }
