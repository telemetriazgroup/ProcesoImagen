"""Almacenamiento de imágenes con UUID y miniaturas."""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.config import get_settings

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    _HEIF_OK = True
except Exception:  # noqa: BLE001 — HEIC opcional en entornos sin libheif
    _HEIF_OK = False

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/octet-stream",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


@dataclass
class StoredImage:
    imagen_id: uuid.UUID
    ruta_imagen: str
    ruta_thumb: str | None
    abs_path: Path
    content_type: str


def _guess_ext(filename: str | None, content_type: str) -> str:
    name = (filename or "").lower()
    for ext in ALLOWED_EXTENSIONS:
        if name.endswith(ext):
            return ".jpg" if ext in {".heic", ".heif"} else ext
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    return ".jpg"


def validate_upload(file: UploadFile, data: bytes) -> None:
    settings = get_settings()
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío.")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Máximo {settings.max_upload_mb} MB.")

    ct = (file.content_type or "").lower()
    name = (file.filename or "").lower()
    ext_ok = any(name.endswith(e) for e in ALLOWED_EXTENSIONS)
    if ct not in ALLOWED_CONTENT_TYPES and not ext_ok:
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Use JPEG, PNG, WebP o HEIC.",
        )
    if name.endswith((".heic", ".heif")) and not _HEIF_OK:
        raise HTTPException(
            status_code=400,
            detail="HEIC no disponible en este servidor. Convierta a JPEG/PNG.",
        )


def _open_image(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        return img
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Imagen ilegible o corrupta.") from exc


def save_upload(file: UploadFile, data: bytes) -> StoredImage:
    """Valida, normaliza (HEIC→JPEG), guarda original + thumb con UUID."""
    validate_upload(file, data)
    settings = get_settings()
    root = Path(settings.storage_path)
    originals = root / "originals"
    thumbs = root / "thumbs"
    originals.mkdir(parents=True, exist_ok=True)
    thumbs.mkdir(parents=True, exist_ok=True)

    imagen_id = uuid.uuid4()
    ct = (file.content_type or "").lower()
    name = (file.filename or "").lower()
    is_heic = name.endswith((".heic", ".heif")) or "heic" in ct or "heif" in ct

    img = _open_image(data)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")

    if is_heic:
        ext = ".jpg"
        out_ct = "image/jpeg"
        dest = originals / f"{imagen_id}{ext}"
        img.save(dest, format="JPEG", quality=92)
    else:
        ext = _guess_ext(file.filename, ct)
        out_ct = {
            ".png": "image/png",
            ".webp": "image/webp",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }.get(ext, "image/jpeg")
        dest = originals / f"{imagen_id}{ext}"
        if ext in {".jpg", ".jpeg"}:
            img.save(dest, format="JPEG", quality=92)
        elif ext == ".png":
            img.save(dest, format="PNG")
        else:
            img.save(dest, format="WEBP", quality=90)

    thumb_path: Path | None = None
    try:
        thumb = img.copy()
        thumb.thumbnail((480, 480))
        thumb_path = thumbs / f"{imagen_id}.jpg"
        thumb.convert("RGB").save(thumb_path, format="JPEG", quality=85)
    except Exception:  # noqa: BLE001
        thumb_path = None

    rel_img = f"originals/{dest.name}"
    rel_thumb = f"thumbs/{thumb_path.name}" if thumb_path else None
    return StoredImage(
        imagen_id=imagen_id,
        ruta_imagen=rel_img,
        ruta_thumb=rel_thumb,
        abs_path=dest,
        content_type=out_ct,
    )


def resolve_storage_path(relative: str) -> Path:
    root = Path(get_settings().storage_path).resolve()
    path = (root / relative).resolve()
    if not str(path).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Ruta de imagen inválida.")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Archivo de imagen no encontrado.")
    return path
