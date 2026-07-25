from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.config import get_settings
from app.core.pipeline import detect_code

router = APIRouter(prefix="/ocr", tags=["fase-1-ocr"])

ALLOWED = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/octet-stream",
}


@router.post("")
async def ocr_detect(
    file: UploadFile = File(...),
    rotations: bool = Query(True, description="Probar rotaciones 90/270"),
) -> dict:
    """Detecta código (ZGRU / Serial / patrones) sin persistir registro."""
    settings = get_settings()
    ct = (file.content_type or "").lower()
    if ct not in ALLOWED and not (file.filename or "").lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp")
    ):
        raise HTTPException(status_code=400, detail="Formato no soportado.")

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío.")
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Máximo {settings.max_upload_mb} MB.")

    try:
        result = detect_code(data, try_rotations=rotations)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Respuesta controlada si no hay detección (nunca 500)
    return {
        "codigo": result["codigo"],
        "tipo": result["tipo"] or "MANUAL",
        "confianza": result["confianza"],
        "orientacion": result["orientacion"],
        "bbox": result["bbox"],
        "fuente": result["fuente"],
        "rotacion": result["rotacion"],
        "sin_deteccion": result["sin_deteccion"],
        "bloques": result["bloques"],
        "mensaje": (
            "Sin código detectado. Ingrese el valor manualmente."
            if result["sin_deteccion"]
            else "Código propuesto. Confirme o corrija."
        ),
    }


@router.get("/ping")
def ocr_ping() -> dict[str, str]:
    return {"status": "ok", "phase": "1", "engine": "rapidocr+rules"}
