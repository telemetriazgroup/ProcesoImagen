import io

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.services.storage import save_upload, validate_upload


def _jpeg_bytes(color=(40, 120, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(buf, format="JPEG")
    return buf.getvalue()


def test_validate_reject_empty():
    f = UploadFile(filename="x.jpg", file=io.BytesIO(b""), headers={"content-type": "image/jpeg"})
    with pytest.raises(HTTPException) as ei:
        validate_upload(f, b"")
    assert ei.value.status_code == 400


def test_validate_reject_bad_format():
    f = UploadFile(
        filename="x.pdf", file=io.BytesIO(b"%PDF"), headers={"content-type": "application/pdf"}
    )
    with pytest.raises(HTTPException) as ei:
        validate_upload(f, b"%PDF-1.4")
    assert ei.value.status_code == 400


def test_save_upload_creates_files(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    from app.config import get_settings

    get_settings.cache_clear()
    data = _jpeg_bytes()
    f = UploadFile(
        filename="placa.jpg", file=io.BytesIO(data), headers={"content-type": "image/jpeg"}
    )
    stored = save_upload(f, data)
    assert stored.abs_path.is_file()
    assert (tmp_path / stored.ruta_imagen).is_file()
    assert stored.ruta_thumb is not None
    assert (tmp_path / stored.ruta_thumb).is_file()
    get_settings.cache_clear()
