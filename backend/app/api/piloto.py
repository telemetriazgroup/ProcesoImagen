from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.core.piloto_pipeline import analizar_imagen
from app.schemas.piloto import ValidacionRequest, ValidacionUpdateRequest
from app.services import feedback as feedback_svc

router = APIRouter(prefix="/piloto", tags=["piloto-0.5"])

ALLOWED_CT = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/octet-stream",
}


def _enrich_urls(payload: dict) -> dict:
    settings = get_settings()
    base = f"{settings.api_prefix}/piloto/runs/{payload['run_id']}"
    for paso in payload.get("pasos", []):
        paso["imagen_url"] = f"{base}/{paso['archivo']}"
    return payload


@router.post("/analizar")
async def analizar(file: UploadFile = File(...)) -> dict:
    """Sube una imagen y devuelve el pipeline paso a paso + propuesta de código."""
    settings = get_settings()
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CT and not (file.filename or "").lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp")
    ):
        raise HTTPException(status_code=400, detail="Formato no soportado. Use JPEG/PNG/WebP.")

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Imagen demasiado grande (máx. {settings.max_upload_mb} MB).",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío.")

    try:
        resultado = analizar_imagen(data, Path(settings.storage_path))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _enrich_urls(resultado.to_dict())


@router.post("/validar")
def validar(body: ValidacionRequest) -> dict:
    """Confirma o corrige el texto OCR y alimenta el dataset de Fase 0."""
    settings = get_settings()
    try:
        registro = feedback_svc.guardar_validacion(
            storage_path=Path(settings.storage_path),
            dataset_path=Path(settings.dataset_path),
            run_id=body.run_id,
            codigo_correcto=body.codigo_correcto,
            tipo=body.tipo,
            orientacion=body.orientacion,
            dificultad=body.dificultad,
            notas=body.notas,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    metricas = feedback_svc.metricas_feedback(Path(settings.dataset_path))
    return {
        "ok": True,
        "mensaje": (
            "Validación guardada. Imagen y código correctos incorporados al dataset Fase 0."
            if registro["acierto"]
            else "Corrección humana guardada. El dataset Fase 0 usará el código corregido."
        ),
        "validacion": registro,
        "metricas": metricas,
    }


@router.get("/validaciones")
def listar_validaciones(limit: int = 200) -> dict:
    settings = get_settings()
    items = feedback_svc.listar_validaciones(Path(settings.dataset_path), limit=limit)
    return {"items": items, "metricas": feedback_svc.metricas_feedback(Path(settings.dataset_path))}


@router.get("/validaciones/{validacion_id}")
def obtener_validacion(validacion_id: str) -> dict:
    settings = get_settings()
    try:
        item = feedback_svc.obtener_validacion(Path(settings.dataset_path), validacion_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return item


@router.put("/validaciones/{validacion_id}")
def actualizar_validacion(validacion_id: str, body: ValidacionUpdateRequest) -> dict:
    """Edita una prueba/validación ya hecha en Fase 0.5."""
    settings = get_settings()
    try:
        registro = feedback_svc.actualizar_validacion(
            storage_path=Path(settings.storage_path),
            dataset_path=Path(settings.dataset_path),
            validacion_id=validacion_id,
            codigo_correcto=body.codigo_correcto,
            tipo=body.tipo,
            orientacion=body.orientacion,
            dificultad=body.dificultad,
            notas=body.notas,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "ok": True,
        "mensaje": "Prueba actualizada. Dataset Fase 0 sincronizado.",
        "validacion": registro,
        "metricas": feedback_svc.metricas_feedback(Path(settings.dataset_path)),
    }


@router.delete("/validaciones/{validacion_id}")
def eliminar_validacion(validacion_id: str) -> dict:
    """Elimina una prueba del historial y del ground truth."""
    settings = get_settings()
    try:
        eliminado = feedback_svc.eliminar_validacion(
            storage_path=Path(settings.storage_path),
            dataset_path=Path(settings.dataset_path),
            validacion_id=validacion_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "ok": True,
        "mensaje": "Prueba eliminada del dataset Fase 0.",
        "eliminado": eliminado,
        "metricas": feedback_svc.metricas_feedback(Path(settings.dataset_path)),
    }


@router.get("/metricas")
def metricas() -> dict:
    settings = get_settings()
    return feedback_svc.metricas_feedback(Path(settings.dataset_path))


@router.get("/runs/{run_id}")
def detalle_run(run_id: str) -> dict:
    settings = get_settings()
    try:
        reporte = feedback_svc.load_reporte(Path(settings.storage_path), run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _enrich_urls(reporte)


@router.get("/runs/{run_id}/{filename}")
def obtener_paso(run_id: str, filename: str) -> FileResponse:
    settings = get_settings()
    safe_name = Path(filename).name
    path = Path(settings.storage_path) / "piloto" / run_id / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Imagen de paso no encontrada.")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/dataset/{filename}")
def imagen_dataset(filename: str) -> FileResponse:
    settings = get_settings()
    safe_name = Path(filename).name
    path = Path(settings.dataset_path) / "images" / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Imagen de dataset no encontrada.")
    return FileResponse(path, media_type="image/jpeg")
