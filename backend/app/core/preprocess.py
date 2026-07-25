"""Preprocesamiento OpenCV configurable (Fase 1 — iteración 3)."""

from __future__ import annotations

from typing import Iterable

import cv2
import numpy as np

DEFAULT_STEPS = ("resize", "gray", "clahe", "denoise")


def decode_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen (use JPEG/PNG/WebP).")
    return img


def encode_image(image_bgr: np.ndarray, ext: str = ".jpg") -> bytes:
    ok, buf = cv2.imencode(ext, image_bgr)
    if not ok:
        raise ValueError("No se pudo codificar la imagen procesada.")
    return buf.tobytes()


def resize_max(image: np.ndarray, max_side: int = 1600) -> np.ndarray:
    h, w = image.shape[:2]
    side = max(h, w)
    if side <= max_side:
        return image
    scale = max_side / side
    return cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def sharpen(gray: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(gray, (0, 0), 1.2)
    return cv2.addWeighted(gray, 1.6, blur, -0.6, 0)


def preprocess_variant(image_bgr: np.ndarray, variant: str = "default") -> np.ndarray:
    """Variantes de preprocess para multipaso OCR."""
    img = resize_max(image_bgr, max_side=1800 if variant.startswith("hires") else 1600)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if variant in ("default", "hires"):
        gray = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)
        gray = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)
    elif variant == "strong_clahe":
        gray = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4)).apply(gray)
        gray = sharpen(gray)
    elif variant == "binary":
        gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 8
        )
    elif variant == "invert_binary":
        gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 8
        )
    else:
        gray = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)

    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def side_strips(image_bgr: np.ndarray, fraction: float = 0.28) -> list[tuple[str, np.ndarray]]:
    """Recortes laterales: códigos ZGRU verticales suelen estar en el borde."""
    _h, w = image_bgr.shape[:2]
    band = max(int(w * fraction), 80)
    return [
        ("left", image_bgr[:, :band]),
        ("right", image_bgr[:, w - band :]),
    ]


def correct_skew(gray: np.ndarray) -> np.ndarray:
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=60, maxLineGap=12)
    if lines is None:
        return gray
    angles: list[float] = []
    for line in lines[:40]:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) < 20:
            angles.append(angle)
    if not angles:
        return gray
    median = float(np.median(angles))
    if abs(median) < 0.8:
        return gray
    h, w = gray.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), median, 1.0)
    return cv2.warpAffine(
        gray, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    )


def preprocess_bgr(
    image_bgr: np.ndarray,
    steps: Iterable[str] | None = None,
) -> np.ndarray:
    active = list(steps) if steps is not None else list(DEFAULT_STEPS)
    img = image_bgr
    if "resize" in active:
        img = resize_max(img)

    if "gray" in active or "clahe" in active or "denoise" in active or "skew" in active:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        return img

    if "skew" in active:
        gray = correct_skew(gray)
    if "clahe" in active:
        gray = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)
    if "denoise" in active:
        gray = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)
    if "sharpen" in active:
        gray = sharpen(gray)

    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def preprocess_image(image_bytes: bytes, steps: list[str] | None = None) -> bytes:
    bgr = decode_image(image_bytes)
    processed = preprocess_bgr(bgr, steps=steps)
    return encode_image(processed)
