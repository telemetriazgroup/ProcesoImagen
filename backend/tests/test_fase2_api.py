"""Integración Fase 2: subir → confirmar → listar → archivo."""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# DB de prueba: Postgres si hay DATABASE_URL_TEST, si no se salta
TEST_DB = os.getenv(
    "DATABASE_URL_TEST",
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://procesoimagen:procesoimagen@localhost:5438/procesoimagen",
    ),
)


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (120, 80), (220, 220, 220)).save(buf, format="JPEG")
    return buf.getvalue()


def _db_available() -> bool:
    try:
        eng = create_engine(TEST_DB, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL no disponible")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DB)
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    from app.config import get_settings

    get_settings.cache_clear()

    from app.db import Base, get_db
    from app.main import app
    from fastapi.testclient import TestClient

    engine = create_engine(TEST_DB, pool_pre_ping=True)
    # Esquema aislado por run
    schema = f"test_fase2_{uuid.uuid4().hex[:8]}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET search_path TO "{schema}"'))
        Base.metadata.create_all(bind=conn)

    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def _get_db():
        db = TestingSession()
        try:
            db.execute(text(f'SET search_path TO "{schema}"'))
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db

    # Mock OCR: determinista y rápido
    def fake_detect(data: bytes, *, try_rotations: bool = True):
        return {
            "codigo": "CIM1077293",
            "tipo": "SERIAL",
            "confianza": 0.91,
            "orientacion": "horizontal",
            "bbox": [[10, 10], [100, 10], [100, 40], [10, 40]],
            "fuente": "test",
            "rotacion": 0,
            "sin_deteccion": False,
            "bloques": [],
        }

    monkeypatch.setattr("app.api.imagenes.detect_code", fake_detect)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()
    get_settings.cache_clear()


def test_flujo_subir_confirmar_listar(client):
    files = {"file": ("placa.jpg", _jpeg_bytes(), "image/jpeg")}
    r = client.post("/api/imagenes", files=files)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["codigo_propuesto"] == "CIM1077293"
    assert body["sin_deteccion"] is False
    imagen_id = body["imagen_id"]

    img = client.get(body["url_imagen"])
    assert img.status_code == 200
    assert img.headers["content-type"].startswith("image/")

    conf = client.post(
        "/api/registros",
        json={"imagen_id": imagen_id, "codigo": "CIM1077293"},
    )
    assert conf.status_code == 201, conf.text
    reg = conf.json()
    assert reg["codigo"] == "CIM1077293"
    assert reg["validado_manual"] is False
    assert reg["tipo_deteccion"] == "SERIAL"
    registro_id = reg["id"]

    detalle = client.get(f"/api/registros/{registro_id}")
    assert detalle.status_code == 200
    assert detalle.json()["codigo"] == "CIM1077293"

    lista = client.get("/api/registros", params={"codigo": "CIM"})
    assert lista.status_code == 200
    assert lista.json()["total"] >= 1


def test_sin_deteccion_ingreso_manual(client, monkeypatch):
    def no_detect(data: bytes, *, try_rotations: bool = True):
        return {
            "codigo": None,
            "tipo": None,
            "confianza": None,
            "orientacion": None,
            "bbox": [],
            "fuente": None,
            "rotacion": 0,
            "sin_deteccion": True,
            "bloques": [],
        }

    monkeypatch.setattr("app.api.imagenes.detect_code", no_detect)
    files = {"file": ("vacia.jpg", _jpeg_bytes(), "image/jpeg")}
    r = client.post("/api/imagenes", files=files)
    assert r.status_code == 201
    body = r.json()
    assert body["sin_deteccion"] is True
    assert body["codigo_propuesto"] is None

    conf = client.post(
        "/api/registros",
        json={"imagen_id": body["imagen_id"], "codigo": "ZGRU1234567", "tipo": "MANUAL"},
    )
    assert conf.status_code == 201
    reg = conf.json()
    assert reg["codigo"] == "ZGRU1234567"
    assert reg["validado_manual"] is True
    assert reg["tipo_deteccion"] == "MANUAL"


def test_formato_invalido(client):
    files = {"file": ("x.txt", b"hola", "text/plain")}
    r = client.post("/api/imagenes", files=files)
    assert r.status_code == 400
