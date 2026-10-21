"""Pipeline Fase 1 iteración 4: geometría Serial→derecha y columna vertical×7."""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from app.core.ocr import rotate_bgr, run_ocr_bgr
from app.core.preprocess import decode_image, preprocess_variant, resize_max, side_strips
from app.core.roi import (
    crop_below_zgru,
    crop_right_of_serial,
    crop_vertical_column,
    detect_digit_columns,
    enlarge,
    find_serial_labels,
    find_zgru_labels,
)
from app.core.rules import (
    _SERIAL_INLINE_RE,
    extract_chip,
    extract_code,
    extract_modulo,
    extract_serial_from_right_roi,
    extract_seven_from_vertical_roi,
)


def _digits_of(codigo: str) -> str:
    if codigo.startswith("ZGRU"):
        return re.sub(r"\D", "", codigo[4:])
    return re.sub(r"\D", "", codigo)


def _merge_blocks(blocks_lists: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for blocks in blocks_lists:
        for b in blocks:
            texto = str(b.get("texto") or "").strip()
            if not texto:
                continue
            bbox = b.get("bbox") or []
            if bbox:
                x = int(float(bbox[0][0]) // 20)
                y = int(float(bbox[0][1]) // 20)
            else:
                x = y = 0
            key = (texto.upper(), x, y)
            if key in seen:
                continue
            seen.add(key)
            merged.append(b)
    return merged


def _ocr_variants(image_bgr: np.ndarray, variants: list[str]) -> list[dict[str, Any]]:
    lists: list[list[dict[str, Any]]] = []
    for variant in variants:
        lists.append(run_ocr_bgr(preprocess_variant(image_bgr, variant)))
    return _merge_blocks(lists)


def _rank(cand: dict[str, Any], *, geometric: bool = False, roi: str | None = None) -> tuple:
    tipo = str(cand.get("tipo") or "")
    codigo = str(cand.get("codigo") or "")
    fuente = str(cand.get("fuente") or "")
    digits = _digits_of(codigo)
    is_seven = tipo == "ZGRU" and len(digits) == 7
    is_zgru = codigo.startswith("ZGRU") and len(digits) in (7, 8)
    serial_roi = "roi_derecha" in fuente or fuente == "regla_serial_roi_derecha"
    serial_line = "serial" in fuente and tipo == "SERIAL"
    strong_prefix = tipo == "SERIAL" and codigo.startswith(("E0", "CIM", "MMAU", "MNBU"))
    short_serial = tipo == "SERIAL" and codigo.isdigit() and 4 <= len(codigo) <= 6
    zgru_label_col = "zgru_columna" in fuente or (roi == "zgru_columna" and is_zgru)
    # Ensamblados/columnas genéricas son más frágiles que un bloque 7 limpio
    weak_seven = is_seven and (
        "ensamblado" in fuente or "columna_7" in (roi or "") or "borde" in (roi or "")
    )

    # Prefijos de serie reales siempre ganan (CIM/E0…), aunque venga del OCR global
    if strong_prefix:
        priority = 9
    elif serial_roi and (short_serial or strong_prefix):
        priority = 8
    elif zgru_label_col and is_zgru:
        priority = 7
    elif is_zgru and not weak_seven:
        priority = 6
    elif is_seven and not weak_seven:
        priority = 5
    elif serial_line or short_serial:
        priority = 5
    elif is_seven or is_zgru:
        priority = 3
    elif serial_roi:
        priority = 3
    elif tipo == "SERIAL":
        priority = 2
    elif tipo == "ZGRU":
        priority = 1
    else:
        priority = 0

    return (
        priority,
        float(cand.get("score") or 0),
        float(cand.get("confianza") or 0),
        1 if geometric else 0,
    )


def _consider(
    best: dict[str, Any] | None,
    cand: dict[str, Any] | None,
    *,
    geometric: bool,
    blocks: list[dict[str, Any]],
    meta: dict[str, Any],
    updates: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if cand is None:
        return best, meta
    prev_geom = bool(meta.get("geometric"))
    cand_roi = (updates or {}).get("roi", meta.get("roi"))
    if best is None or _rank(cand, geometric=geometric, roi=cand_roi) > _rank(
        best, geometric=prev_geom, roi=meta.get("roi")
    ):
        new_meta = {
            "blocks": blocks,
            "geometric": geometric,
            "rotacion": meta.get("rotacion", 0),
            "desde_borde": meta.get("desde_borde", False),
            "roi": meta.get("roi"),
        }
        if updates:
            new_meta.update(updates)
        return cand, new_meta
    return best, meta


def detect_chip(
    image_bytes: bytes,
    *,
    try_rotations: bool = True,
) -> dict[str, Any]:
    """Lectura de IMEI cuando el pedido es de chip. No usa las reglas de ZGRU ni de serie."""
    original = resize_max(decode_image(image_bytes), max_side=1800)
    pasos: list[str] = ["Caso CHIP: IMEI de tarjeta o chip. ZGRU y serie no entran."]
    blocks = _ocr_variants(original, ["default", "strong_clahe"])
    cand = extract_chip(blocks)
    rotacion = 0
    completo = bool(cand and str(cand.get("codigo") or "").startswith("8951"))
    if try_rotations and not completo:
        pasos.append("Sin IMEI completo en horizontal; giro 90/270")
        for degrees in (90, 270):
            extra = _ocr_variants(rotate_bgr(original, degrees), ["default", "strong_clahe"])
            blocks = _merge_blocks([blocks, extra])
            cand = extract_chip(blocks)
            rotacion = degrees
            if cand and str(cand.get("codigo") or "").startswith("8951"):
                pasos.append(f"   → rot={degrees}: {cand.get('codigo')}")
                break
    if cand and cand.get("codigo"):
        pasos.append(f"Resultado CHIP: {cand.get('codigo')} · fuente={cand.get('fuente')}")
    else:
        pasos.append("Sin IMEI de chip")
    return {
        "codigo": cand.get("codigo") if cand else None,
        "tipo": "CHIP",
        "confianza": cand.get("confianza") if cand else None,
        "orientacion": cand.get("orientacion") if cand else None,
        "bbox": cand.get("bbox") if cand else [],
        "fuente": cand.get("fuente") if cand else None,
        "rotacion": rotacion,
        "bloques": blocks,
        "sin_deteccion": not bool(cand and cand.get("codigo")),
        "desde_borde": False,
        "roi": "chip",
        "pasos": pasos,
        "observaciones": "\n".join(pasos),
        "numeros": list(cand.get("numeros") or []) if cand else [],
        "fragmentos": list(cand.get("fragmentos") or []) if cand else [],
    }


def detect_modulo(
    image_bytes: bytes,
    *,
    try_rotations: bool = True,
) -> dict[str, Any]:
    """Etiqueta negra ZTRACK-V2. El SN es el código. El IMEI queda en la lista de la señal."""
    original = resize_max(decode_image(image_bytes), max_side=1800)
    pasos: list[str] = ["Caso MÓDULO: etiqueta ZTRACK-V2. El SN busca el equipo y el IMEI queda para la señal."]
    sn = ""
    imei = ""
    modelo = ""
    numeros: list[str] = []
    sns: list[str] = []
    blocks: list[dict[str, Any]] = []
    confianza = None
    bbox: list[Any] = []
    fuente = None
    orientacion = None
    rotacion = 0
    for degrees in (0, 90, 270) if try_rotations else (0,):
        imagen = original if degrees == 0 else rotate_bgr(original, degrees)
        leidos = _ocr_variants(imagen, ["default", "strong_clahe"])
        cand = extract_modulo(leidos)
        if not cand:
            continue
        blocks = _merge_blocks([blocks, leidos])
        if cand.get("sn") and not sn:
            sn = str(cand["sn"])
            rotacion = degrees
        if cand.get("imei") and not imei:
            imei = str(cand["imei"])
            rotacion = degrees
        if cand.get("modelo") and not modelo:
            modelo = str(cand["modelo"])
        for valor in cand.get("numeros") or []:
            if valor not in numeros:
                numeros.append(str(valor))
        for valor in cand.get("sns") or []:
            if valor not in sns:
                sns.append(str(valor))
        confianza = cand.get("confianza")
        bbox = cand.get("bbox") or bbox
        fuente = cand.get("fuente")
        orientacion = cand.get("orientacion")
        pasos.append(f"   → rot={degrees}: SN={cand.get('sn') or '—'} IMEI={cand.get('imei') or '—'}")
        if sn and imei:
            break
    if sn or imei:
        pasos.append(f"Resultado MÓDULO: SN={sn or '—'} IMEI={imei or '—'}")
    else:
        pasos.append("Sin SN ni IMEI de módulo")
    return {
        "codigo": sn or None,
        "tipo": "MODULO",
        "confianza": confianza,
        "orientacion": orientacion,
        "bbox": bbox,
        "fuente": fuente if sn or imei else None,
        "rotacion": rotacion,
        "bloques": blocks,
        "sin_deteccion": not bool(sn or imei),
        "desde_borde": False,
        "roi": "modulo",
        "pasos": pasos,
        "observaciones": "\n".join(pasos),
        "sn": sn,
        "imei": imei,
        "modelo": modelo,
        "numeros": numeros,
        "sns": sns,
    }


def detect_code(
    image_bytes: bytes,
    *,
    steps: list[str] | None = None,
    try_rotations: bool = True,
) -> dict[str, Any]:
    """
    Flujo iteración 4:
    1) OCR global horizontal.
    2) Si hay Serial → recortar banda horizontal a la DERECHA, ampliar, OCR (códigos cortos).
    3) Si hay ZGRU → recortar columna debajo, ampliar, buscar 7 dígitos.
    4) Columnas verticales de dígitos → recortar, ampliar, rotar, agrupar de 7.
    5) Fallback rotaciones / bordes.
    """
    _ = steps
    original = resize_max(decode_image(image_bytes), max_side=1800)
    pasos: list[str] = ["Preprocess: resize max 1800px"]

    best: dict[str, Any] | None = None
    meta: dict[str, Any] = {
        "blocks": [],
        "geometric": False,
        "rotacion": 0,
        "desde_borde": False,
        "roi": None,
    }

    # --- 1) Pasada horizontal global ---
    pasos.append("1. OCR horizontal (default + strong_clahe)")
    blocks_h = _ocr_variants(original, ["default", "strong_clahe"])
    cand = extract_code(blocks_h, modo="horizontal")
    if cand:
        pasos.append(
            f"   → candidato horizontal: {cand.get('codigo')} ({cand.get('fuente')})"
        )
    best, meta = _consider(
        best,
        cand,
        geometric=False,
        blocks=blocks_h,
        meta=meta,
        updates={"rotacion": 0},
    )

    # --- 2) Serial → línea horizontal → texto a la DERECHA (ampliado) ---
    serial_labels = find_serial_labels(blocks_h)
    if serial_labels:
        pasos.append(f"2. Label Serial detectado ({len(serial_labels)}); ROI derecha ampliado")
    for label in serial_labels:
        label_txt = str(label.get("texto") or "")
        # Si el valor ya viene inline ("Serial No CIM…"), no recortar a la derecha
        if _SERIAL_INLINE_RE.search(label_txt) and re.search(
            r"(?:CIM|E0|MMAU|MNBU|[A-Z]*\d{4,})", label_txt, re.I
        ):
            pasos.append("   → valor inline en el mismo bloque Serial (sin ROI)")
            continue
        band = crop_right_of_serial(original, label)
        if band is None:
            continue
        band_big = enlarge(band, scale=2.4)
        roi_blocks = _ocr_variants(band_big, ["strong_clahe", "default", "binary"])
        serial_cand = extract_serial_from_right_roi(roi_blocks)
        if serial_cand:
            pasos.append(
                f"   → ROI Serial derecha: {serial_cand.get('codigo')}"
            )
        best, meta = _consider(
            best,
            serial_cand,
            geometric=True,
            blocks=roi_blocks,
            meta=meta,
            updates={"rotacion": 0, "roi": "serial_derecha"},
        )

    # --- 3) ZGRU → columna vertical debajo → ampliar → 7 dígitos ---
    # Solo si aún no hay ZGRU+7 limpio del OCR global (el ROI no debe pisarlo)
    have_zgru7 = bool(
        best
        and str(best.get("codigo") or "").startswith("ZGRU")
        and len(_digits_of(str(best.get("codigo") or ""))) == 7
        and float(best.get("confianza") or 0) >= 0.75
    )
    zgru_labels = find_zgru_labels(blocks_h)
    if zgru_labels and not have_zgru7:
        pasos.append(f"3. Prefijo ZGRU ({len(zgru_labels)}); columna debajo ×7")
    if not have_zgru7:
        for label in zgru_labels:
            col = crop_below_zgru(original, label)
            if col is None:
                continue
            for rot in (0, 90, 270):
                view = col if rot == 0 else rotate_bgr(col, rot)
                view = enlarge(view, scale=2.6)
                roi_blocks = _ocr_variants(view, ["strong_clahe", "binary", "default"])
                seven = extract_seven_from_vertical_roi(roi_blocks)
                if seven and not str(seven.get("codigo") or "").startswith("ZGRU"):
                    digs = _digits_of(str(seven.get("codigo") or ""))
                    if len(digs) == 7:
                        seven = dict(seven)
                        seven["codigo"] = f"ZGRU{digs}"
                        seven["fuente"] = "regla_zgru_columna_roi"
                        seven["score"] = float(seven.get("score") or 0) + 8
                if seven:
                    pasos.append(
                        f"   → columna ZGRU rot={rot}: {seven.get('codigo')}"
                    )
                best, meta = _consider(
                    best,
                    seven,
                    geometric=True,
                    blocks=roi_blocks,
                    meta=meta,
                    updates={"rotacion": rot, "roi": "zgru_columna"},
                )

    # --- 4) Columnas verticales de dígitos (solo si no hay Serial/ZGRU usable) ---
    def _is_strong_serial(c: dict[str, Any] | None) -> bool:
        if not c or c.get("tipo") != "SERIAL":
            return False
        code = str(c.get("codigo") or "")
        fuente = str(c.get("fuente") or "")
        return bool(
            code.startswith(("E0", "CIM", "MMAU", "MNBU"))
            or "roi_derecha" in fuente
            or "serial_inline" in fuente
            or "serial_misma_linea" in fuente
            or (code.isdigit() and 4 <= len(code) <= 6)
        )

    strong_serial = _is_strong_serial(best)
    # Si hay label Serial y ya tenemos serial usable, no inventar 7 dígitos
    if find_serial_labels(blocks_h) and strong_serial:
        pass
    elif not strong_serial and not (
        best
        and str(best.get("codigo") or "").startswith("ZGRU")
        and len(_digits_of(str(best.get("codigo") or ""))) == 7
        and float(best.get("confianza") or 0) >= 0.85
    ):
        cols = detect_digit_columns(blocks_h, min_fragments=3)[:3]
        if cols:
            pasos.append(f"4. Columnas verticales de dígitos ({len(cols)})")
        for _x, col_blocks in cols:
            col = crop_vertical_column(original, col_blocks)
            if col is None:
                continue
            for rot, scale in ((90, 2.8), (270, 2.8)):
                view = enlarge(rotate_bgr(col, rot), scale=scale)
                roi_blocks = _ocr_variants(view, ["strong_clahe", "default"])
                seven = extract_seven_from_vertical_roi(roi_blocks)
                if seven:
                    pasos.append(f"   → columna_7 rot={rot}: {seven.get('codigo')}")
                best, meta = _consider(
                    best,
                    seven,
                    geometric=True,
                    blocks=roi_blocks,
                    meta=meta,
                    updates={"rotacion": rot, "roi": "columna_7"},
                )

    # --- 5) Fallback vertical: rotaciones + bordes ---
    # Solo se omite con Serial fuerte. Los 7 dígitos débiles/ensamblados SÍ rotan.
    need_fallback = not strong_serial
    if best is not None and not strong_serial:
        fuente = str(best.get("fuente") or "")
        conf = float(best.get("confianza") or 0)
        code = str(best.get("codigo") or "")
        digs = _digits_of(code)
        # ZGRU con prefijo leído limpio y alta confianza: suficiente
        if (
            code.startswith("ZGRU")
            and len(digs) == 7
            and "prefijo" in fuente
            and conf >= 0.9
            and "ensamblado" not in fuente
        ):
            need_fallback = False

    if try_rotations and need_fallback:
        pasos.append("5. Fallback rotación 90/270 + crops de borde")
        for degrees in (90, 270):
            img = rotate_bgr(original, degrees)
            blocks = _ocr_variants(img, ["default", "strong_clahe"])
            cand = extract_code(blocks, modo="vertical")
            if cand:
                cand = dict(cand)
                cand["orientacion"] = "vertical"
                pasos.append(f"   → rot={degrees}: {cand.get('codigo')}")
            best, meta = _consider(
                best,
                cand,
                geometric=False,
                blocks=blocks,
                meta=meta,
                updates={"rotacion": degrees},
            )
        for _name, strip in side_strips(original, fraction=0.30):
            for degrees in (90, 270):
                img = enlarge(rotate_bgr(strip, degrees), scale=2.2)
                blocks = _ocr_variants(img, ["strong_clahe", "default"])
                seven = extract_seven_from_vertical_roi(blocks)
                if seven:
                    pasos.append(
                        f"   → borde {_name} rot={degrees}: {seven.get('codigo')}"
                    )
                best, meta = _consider(
                    best,
                    seven,
                    geometric=True,
                    blocks=blocks,
                    meta=meta,
                    updates={"rotacion": degrees, "desde_borde": True, "roi": "borde"},
                )

    if best:
        pasos.append(
            f"Resultado final: {best.get('codigo')} · fuente={best.get('fuente')} · "
            f"roi={meta.get('roi')} · rot={meta.get('rotacion', 0)}"
        )
    else:
        pasos.append("Sin detección de código")

    return {
        "codigo": best.get("codigo") if best else None,
        "tipo": best.get("tipo") if best else None,
        "confianza": best.get("confianza") if best else None,
        "orientacion": best.get("orientacion") if best else None,
        "bbox": best.get("bbox") if best else [],
        "fuente": best.get("fuente") if best else None,
        "rotacion": meta.get("rotacion", 0),
        "bloques": meta.get("blocks") or [],
        "sin_deteccion": best is None,
        "desde_borde": bool(meta.get("desde_borde")),
        "roi": meta.get("roi"),
        "pasos": pasos,
        "observaciones": "\n".join(pasos),
    }
