from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.pipeline import detect_chip, detect_code, detect_modulo
from app.core.rules import canonicalize_code
from app.db import get_db
from app.models.imagen import Imagen
from app.schemas.imagenes import ImagenPropuestaOut
from app.services.storage import resolve_storage_path, save_upload

router = APIRouter(prefix="/imagenes", tags=["fase-2-imagenes"])


def _urls(imagen_id: uuid.UUID, has_thumb: bool) -> tuple[str, str | None]:
    base = f"/api/imagenes/{imagen_id}/archivo"
    return base, f"{base}?thumb=1" if has_thumb else None


def _propuesta_from_row(row: Imagen, pasos: list[str] | None = None) -> ImagenPropuestaOut:
    url, url_thumb = _urls(row.id, bool(row.ruta_thumb))
    sin = bool(row.sin_deteccion)
    return ImagenPropuestaOut(
        imagen_id=row.id,
        codigo_propuesto=None if sin else row.codigo_ocr,
        tipo=row.tipo_deteccion or "MANUAL",
        confianza=row.confianza,
        orientacion=row.orientacion,
        bbox=row.bbox or [],
        sin_deteccion=sin,
        mensaje=(
            "Sin IMEI de chip. La foto no alcanzó para leer la tarjeta."
            if sin and (row.tipo_deteccion == "CHIP" or (row.fuente or "").startswith("regla_chip"))
            else "Sin código detectado. Ingrese el valor manualmente."
            if sin
            else "IMEI de chip propuesto. Confirme o corrija."
            if row.tipo_deteccion == "CHIP"
            else "Código propuesto. Confirme o corrija."
        ),
        url_imagen=url,
        url_thumb=url_thumb,
        fuente=row.fuente,
        observaciones=row.observaciones,
        tiempo_proceso_s=row.tiempo_proceso_s,
        pasos=pasos
        or ([ln for ln in (row.observaciones or "").splitlines() if ln] if row.observaciones else []),
        creado_en=row.creado_en,
    )


@router.post("", response_model=ImagenPropuestaOut, status_code=201)
async def subir_imagen(
    file: UploadFile = File(...),
    rotations: bool = Query(True, description="Probar rotaciones 90/270 en OCR"),
    caso: str = Query("", description="chip lee el IMEI. modulo lee SN e IMEI de ZTRACK. Vacío conserva contenedor y serie."),
    db: Session = Depends(get_db),
) -> ImagenPropuestaOut:
    """Sube imagen, ejecuta OCR y guarda propuesta (no crea registro definitivo)."""
    data = await file.read()
    stored = save_upload(file, data)
    ocr_bytes = stored.abs_path.read_bytes()

    t0 = time.perf_counter()
    try:
        caso_limpio = caso.strip().lower()
        if caso_limpio == "chip":
            result = detect_chip(ocr_bytes, try_rotations=rotations)
        elif caso_limpio in {"modulo", "modem"}:
            result = detect_modulo(ocr_bytes, try_rotations=rotations)
        else:
            result = detect_code(ocr_bytes, try_rotations=rotations)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — respuesta controlada
        raise HTTPException(
            status_code=400, detail=f"No se pudo procesar la imagen: {exc}"
        ) from exc
    elapsed = round(time.perf_counter() - t0, 3)

    codigo = result.get("codigo")
    if codigo:
        codigo = canonicalize_code(str(codigo))
    tipo = result.get("tipo") or ("MANUAL" if result.get("sin_deteccion") else "OTRO")
    es_modulo = caso.strip().lower() in {"modulo", "modem"}
    sin = bool(result.get("sin_deteccion")) if es_modulo else bool(result.get("sin_deteccion") or not codigo)
    pasos = list(result.get("pasos") or [])
    observaciones = result.get("observaciones") or "\n".join(pasos)
    if es_modulo and result.get("imei"):
        observaciones = f"IMEI {result.get('imei')}\n{observaciones}"

    row = Imagen(
        id=stored.imagen_id,
        ruta_imagen=stored.ruta_imagen,
        ruta_thumb=stored.ruta_thumb,
        codigo_ocr=codigo,
        tipo_deteccion=tipo if not sin else "MANUAL",
        confianza=result.get("confianza"),
        bbox=result.get("bbox") or [],
        orientacion=result.get("orientacion"),
        sin_deteccion=sin,
        fuente=result.get("fuente"),
        observaciones=observaciones,
        tiempo_proceso_s=elapsed,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _propuesta_from_row(row, pasos=pasos)


@router.get("/{imagen_id}", response_model=ImagenPropuestaOut)
def detalle_imagen(imagen_id: uuid.UUID, db: Session = Depends(get_db)) -> ImagenPropuestaOut:
    row = db.get(Imagen, imagen_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    return _propuesta_from_row(row)


@router.get("/{imagen_id}/archivo")
def servir_archivo(
    imagen_id: uuid.UUID,
    thumb: bool = Query(False),
    db: Session = Depends(get_db),
) -> FileResponse:
    row = db.get(Imagen, imagen_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    relative = row.ruta_thumb if thumb and row.ruta_thumb else row.ruta_imagen
    path = resolve_storage_path(relative)
    media = "image/jpeg"
    if path.suffix.lower() == ".png":
        media = "image/png"
    elif path.suffix.lower() == ".webp":
        media = "image/webp"
    return FileResponse(path, media_type=media, filename=path.name)
