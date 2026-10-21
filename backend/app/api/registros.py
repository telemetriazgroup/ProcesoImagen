from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.rules import canonicalize_code
from app.db import get_db
from app.models.imagen import Imagen
from app.models.registro import RegistroEquipo
from app.schemas.registros import RegistroCreate, RegistroListOut, RegistroOut

router = APIRouter(prefix="/registros", tags=["fase-2-registros"])

_VALID_TIPOS = {"ZGRU", "SERIAL", "CHIP", "OTRO", "MANUAL"}


def _infer_tipo(codigo: str, tipo_ocr: str | None, manual: bool) -> str:
    if manual and (not tipo_ocr or tipo_ocr == "MANUAL"):
        c = canonicalize_code(codigo)
        if c.startswith("ZGRU"):
            return "ZGRU"
        if c.startswith("8951") and c.isdigit() and 14 <= len(c) <= 22:
            return "CHIP"
        if c.startswith(("E0", "CIM", "MMAU", "MNBU", "SC")):
            return "SERIAL"
        return "MANUAL"
    if tipo_ocr and tipo_ocr in _VALID_TIPOS:
        return tipo_ocr
    return "MANUAL"


def _to_out(reg: RegistroEquipo, imagen: Imagen | None = None) -> RegistroOut:
    img = imagen or reg.imagen
    url = f"/api/imagenes/{reg.imagen_id}/archivo"
    url_thumb = f"{url}?thumb=1" if img and img.ruta_thumb else None
    return RegistroOut(
        id=reg.id,
        imagen_id=reg.imagen_id,
        codigo=reg.codigo,
        tipo_deteccion=reg.tipo_deteccion,
        codigo_ocr=reg.codigo_ocr,
        confianza=reg.confianza,
        validado_manual=reg.validado_manual,
        ruta_imagen=reg.ruta_imagen,
        orientacion=reg.orientacion,
        fuente=reg.fuente,
        observaciones=reg.observaciones,
        tiempo_proceso_s=reg.tiempo_proceso_s,
        usuario_id=reg.usuario_id,
        creado_en=reg.creado_en,
        url_imagen=url,
        url_thumb=url_thumb,
    )


@router.post("", response_model=RegistroOut, status_code=201)
def crear_registro(body: RegistroCreate, db: Session = Depends(get_db)) -> RegistroOut:
    """Confirma y persiste el registro (código final + imagen)."""
    imagen = db.get(Imagen, body.imagen_id)
    if imagen is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")

    existing = db.scalar(
        select(RegistroEquipo).where(RegistroEquipo.imagen_id == body.imagen_id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="Ya existe un registro para esta imagen."
        )

    codigo = canonicalize_code(body.codigo.strip())
    if not codigo:
        raise HTTPException(status_code=400, detail="El código no puede estar vacío.")

    ocr = canonicalize_code(imagen.codigo_ocr or "") if imagen.codigo_ocr else None
    validado_manual = ocr is None or codigo != ocr

    if body.tipo:
        tipo = body.tipo.upper()
        if tipo not in _VALID_TIPOS:
            raise HTTPException(status_code=400, detail=f"tipo inválido: {body.tipo}")
    else:
        tipo = _infer_tipo(codigo, imagen.tipo_deteccion, validado_manual)

    reg = RegistroEquipo(
        imagen_id=imagen.id,
        codigo=codigo,
        tipo_deteccion=tipo,
        codigo_ocr=imagen.codigo_ocr,
        confianza=imagen.confianza,
        validado_manual=validado_manual,
        ruta_imagen=imagen.ruta_imagen,
        orientacion=imagen.orientacion,
        fuente=imagen.fuente,
        observaciones=imagen.observaciones,
        tiempo_proceso_s=imagen.tiempo_proceso_s,
        usuario_id=None,
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return _to_out(reg, imagen)


@router.get("", response_model=RegistroListOut)
def listar_registros(
    codigo: str | None = Query(None, description="Búsqueda parcial por código"),
    tipo: str | None = Query(None),
    validado_manual: bool | None = Query(None),
    desde: datetime | None = Query(None),
    hasta: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> RegistroListOut:
    q = select(RegistroEquipo)
    count_q = select(func.count()).select_from(RegistroEquipo)

    if codigo:
        like = f"%{canonicalize_code(codigo)}%"
        q = q.where(RegistroEquipo.codigo.ilike(like))
        count_q = count_q.where(RegistroEquipo.codigo.ilike(like))
    if tipo:
        q = q.where(RegistroEquipo.tipo_deteccion == tipo.upper())
        count_q = count_q.where(RegistroEquipo.tipo_deteccion == tipo.upper())
    if validado_manual is not None:
        q = q.where(RegistroEquipo.validado_manual.is_(validado_manual))
        count_q = count_q.where(RegistroEquipo.validado_manual.is_(validado_manual))
    if desde is not None:
        q = q.where(RegistroEquipo.creado_en >= desde)
        count_q = count_q.where(RegistroEquipo.creado_en >= desde)
    if hasta is not None:
        q = q.where(RegistroEquipo.creado_en <= hasta)
        count_q = count_q.where(RegistroEquipo.creado_en <= hasta)

    total = int(db.scalar(count_q) or 0)
    rows = db.scalars(
        q.order_by(RegistroEquipo.creado_en.desc()).offset(offset).limit(limit)
    ).all()
    return RegistroListOut(total=total, items=[_to_out(r) for r in rows])


@router.get("/{registro_id}", response_model=RegistroOut)
def detalle_registro(registro_id: int, db: Session = Depends(get_db)) -> RegistroOut:
    reg = db.get(RegistroEquipo, registro_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    return _to_out(reg)
