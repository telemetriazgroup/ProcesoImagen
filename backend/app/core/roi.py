"""Recortes geométricos para Serial (derecha) y códigos verticales (columna)."""

from __future__ import annotations

import re
from typing import Any

import cv2
import numpy as np

_SERIAL_RE = re.compile(r"serial(?:\s*(?:number|no\.?|n\.?))?", re.I)
_ZGRU_RE = re.compile(r"z\s*g\s*r\s*u", re.I)


def _bbox_xyxy(block: dict[str, Any]) -> tuple[int, int, int, int] | None:
    bbox = block.get("bbox") or []
    if not bbox:
        return None
    xs = [float(p[0]) for p in bbox]
    ys = [float(p[1]) for p in bbox]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def _center(block: dict[str, Any]) -> tuple[float, float, float, float]:
    box = _bbox_xyxy(block)
    if not box:
        return 0.0, 0.0, 0.0, 0.0
    x0, y0, x1, y1 = box
    return (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0


def enlarge(image_bgr: np.ndarray, scale: float = 2.2) -> np.ndarray:
    if scale <= 1.0:
        return image_bgr
    h, w = image_bgr.shape[:2]
    return cv2.resize(
        image_bgr,
        (max(1, int(w * scale)), max(1, int(h * scale))),
        interpolation=cv2.INTER_CUBIC,
    )


def _safe_crop(image_bgr: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> np.ndarray | None:
    h, w = image_bgr.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 - x0 < 12 or y1 - y0 < 12:
        return None
    return image_bgr[y0:y1, x0:x1].copy()


def find_serial_labels(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for b in blocks:
        texto = str(b.get("texto") or "")
        if _SERIAL_RE.search(texto):
            out.append(b)
    return out


def find_zgru_labels(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for b in blocks:
        texto = str(b.get("texto") or "")
        if _ZGRU_RE.search(texto):
            out.append(b)
    return out


def crop_right_of_serial(
    image_bgr: np.ndarray,
    serial_block: dict[str, Any],
    *,
    y_pad_ratio: float = 0.75,
    min_width: int = 80,
    max_width: int = 520,
) -> np.ndarray | None:
    """Banda horizontal: misma línea que Serial, texto a la DERECHA.

    Pad vertical moderado: suficiente para serial ligeramente descentrado,
    sin tragarse toda la placa.
    """
    box = _bbox_xyxy(serial_block)
    if not box:
        return None
    x0, y0, x1, y1 = box
    h, w = image_bgr.shape[:2]
    band_h = max(y1 - y0, 18)
    # Más margen hacia ARRIBA: en muchas placas el valor queda en columna
    # derecha ligeramente sobre la palabra Serial.
    pad_up = max(10, int(band_h * max(y_pad_ratio, 0.75) * 1.8))
    pad_down = max(8, int(band_h * y_pad_ratio))
    cy0 = max(0, y0 - pad_up)
    cy1 = min(h, y1 + pad_down)
    # Empieza justo al final del label Serial; ancho acotado (no toda la placa)
    cx0 = min(w - min_width, x1 + 2)
    cx1 = min(w, cx0 + max(min_width, max_width))
    return _safe_crop(image_bgr, cx0, cy0, cx1, cy1)


def crop_below_zgru(
    image_bgr: np.ndarray,
    zgru_block: dict[str, Any],
    *,
    x_pad: int = 35,
    max_height_ratio: float = 0.55,
) -> np.ndarray | None:
    """Columna bajo ZGRU siguiendo la línea vertical (7 dígitos hacia abajo)."""
    box = _bbox_xyxy(zgru_block)
    if not box:
        return None
    x0, y0, x1, y1 = box
    h, w = image_bgr.shape[:2]
    cx = (x0 + x1) // 2
    half = max((x1 - x0) // 2 + x_pad, 28)
    col_x0 = max(0, cx - half)
    col_x1 = min(w, cx + half)
    col_y0 = y1  # debajo del prefijo
    col_y1 = min(h, y1 + int(h * max_height_ratio))
    return _safe_crop(image_bgr, col_x0, col_y0, col_x1, col_y1)


def detect_digit_columns(
    blocks: list[dict[str, Any]],
    *,
    x_tol: float = 42.0,
    min_fragments: int = 3,
) -> list[tuple[float, list[dict[str, Any]]]]:
    """Agrupa bloques numéricos cortos en columnas verticales (misma X)."""
    frags: list[tuple[float, float, dict[str, Any]]] = []
    for b in blocks:
        texto = str(b.get("texto") or "").strip()
        digits = re.sub(r"\D", "", texto)
        if not digits:
            continue
        # Fragmentos o secuencias numéricas (no teléfonos largos)
        if len(digits) > 8:
            continue
        if re.search(r"[A-Za-z]{3,}", texto) and not re.fullmatch(r"[0-9OIlSB\s\-]+", texto, re.I):
            continue
        x, y, _, _ = _center(b)
        frags.append((x, y, b))

    if not frags:
        return []

    frags.sort(key=lambda t: t[0])
    groups: list[list[tuple[float, float, dict[str, Any]]]] = []
    for frag in frags:
        placed = False
        for g in groups:
            if abs(frag[0] - g[0][0]) <= x_tol:
                g.append(frag)
                placed = True
                break
        if not placed:
            groups.append([frag])

    columns: list[tuple[float, list[dict[str, Any]]]] = []
    for g in groups:
        if len(g) < min_fragments and not any(
            len(re.sub(r"\D", "", str(b.get("texto") or ""))) >= 5 for _, _, b in g
        ):
            continue
        g.sort(key=lambda t: t[1])  # arriba → abajo
        x_mean = sum(t[0] for t in g) / len(g)
        columns.append((x_mean, [t[2] for t in g]))
    # Preferir columnas más a la derecha (marco del contenedor) y con más fragmentos
    columns.sort(key=lambda c: (-len(c[1]), -c[0]))
    return columns


def crop_vertical_column(
    image_bgr: np.ndarray,
    column_blocks: list[dict[str, Any]],
    *,
    x_pad: int = 40,
    y_pad: int = 20,
) -> np.ndarray | None:
    """Recorta la columna vertical que contiene los dígitos agrupados."""
    boxes = [_bbox_xyxy(b) for b in column_blocks]
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes) - x_pad
    y0 = min(b[1] for b in boxes) - y_pad
    x1 = max(b[2] for b in boxes) + x_pad
    y1 = max(b[3] for b in boxes) + y_pad
    return _safe_crop(image_bgr, x0, y0, x1, y1)
