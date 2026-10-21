from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.config import get_settings
from app.core.pipeline import detect_chip, detect_code, detect_modulo

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
    caso: str = Query("", description="chip lee el IMEI. modulo lee SN e IMEI de ZTRACK. Vacío conserva contenedor y serie."),
) -> dict:
    """Detecta código (ZGRU / Serial / chip / módulo) sin persistir registro."""
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

    caso_limpio = caso.strip().lower()
    try:
        if caso_limpio == "chip":
            result = detect_chip(data, try_rotations=rotations)
        elif caso_limpio in {"modulo", "modem"}:
            result = detect_modulo(data, try_rotations=rotations)
        else:
            result = detect_code(data, try_rotations=rotations)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Respuesta controlada si no hay detección (nunca 500)
    respuesta = {
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
            "Sin etiqueta de módulo. No leí el SN ni el IMEI."
            if caso_limpio in {"modulo", "modem"} and result["sin_deteccion"]
            else "Etiqueta de módulo. El SN busca el equipo y el IMEI queda para la señal."
            if caso_limpio in {"modulo", "modem"}
            else "Sin IMEI de chip. La foto no alcanzó para leer la tarjeta."
            if caso_limpio == "chip" and result["sin_deteccion"]
            else "Sin código detectado. Ingrese el valor manualmente."
            if result["sin_deteccion"]
            else "IMEI de chip propuesto. Confirme o corrija."
            if caso_limpio == "chip"
            else "Código propuesto. Confirme o corrija."
        ),
    }
    if caso_limpio == "chip":
        respuesta["numeros"] = result.get("numeros") or []
        respuesta["fragmentos"] = result.get("fragmentos") or []
    if caso_limpio in {"modulo", "modem"}:
        respuesta["sn"] = result.get("sn") or ""
        respuesta["imei"] = result.get("imei") or ""
        respuesta["modelo"] = result.get("modelo") or ""
        respuesta["numeros"] = result.get("numeros") or []
        respuesta["sns"] = result.get("sns") or []
    return respuesta


@router.get("/ping")
def ocr_ping() -> dict[str, str]:
    return {"status": "ok", "phase": "1", "engine": "rapidocr+rules"}
