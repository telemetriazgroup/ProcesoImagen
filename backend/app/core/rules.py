"""Motor de reglas Fase 1 (iteración 2).

Dominio:
- ZGRU / OTRO: en vertical casi nunca aparece el prefijo; el código son
  siempre **7 dígitos**. Si no hay ZGRU, detectar esos 7 números.
- SERIAL: el código está en la **misma línea horizontal** que la palabra
  Serial / Serial No / Serial number (siempre horizontal).
"""

from __future__ import annotations

import math
import re
from typing import Any, Literal

Modo = Literal["auto", "horizontal", "vertical"]

_DIGIT_MAP = str.maketrans(
    {
        "O": "0",
        "o": "0",
        "Q": "0",
        "D": "0",
        "I": "1",
        "l": "1",
        "L": "1",
        "|": "1",
        "S": "5",
        "s": "5",
        "B": "8",
        "G": "6",
    }
)

_ZGRU_RE = re.compile(r"Z\s*G\s*R\s*U[\s\-]*([0-9OIlSB]{4,})", re.IGNORECASE)
_SERIAL_LABEL_TOKEN_RE = re.compile(
    r"serial(?:\s*(?:number|no\.?|n\.?))?",
    re.IGNORECASE,
)
_SERIAL_INLINE_RE = re.compile(
    r"serial(?:\s*(?:number|no\.?|n\.?))?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{3,})",
    re.IGNORECASE,
)
_PREFIX_RE = re.compile(
    r"\b((?:CIM|MMAU|MNBU|SC|E0(?:F|GM|GO|G)?|EO(?:F|GM|GO|G)?)[A-Z0-9\-]{3,})\b",
    re.IGNORECASE,
)
_SEVEN_DIGITS_RE = re.compile(r"(?<!\d)([0-9OIlSB]{7})(?!\d)")
_EIGHT_DIGITS_RE = re.compile(r"(?<!\d)([0-9OIlSB]{8})(?!\d)")
_DIGITS_RE = re.compile(r"[0-9OIlSB]{5,10}")
_STOP_SUBSTR = ("CAPACITY", "PHASE", "VOLTAGE", "CURRENT", "REFRIGER", "CAMB", "TEL", "FAX")
_STOP_CODES = {
    "NUMBER",
    "SERIAL",
    "MODEL",
    "POWER",
    "PHASE",
    "INPUT",
    "OUTPUT",
    "CAPACITY",
    "R134A",
    "R404A",
    "R410A",
    "R407C",
    "R22",
}


def normalize_code(text: str) -> str:
    return re.sub(r"[\s\-_]+", "", text.strip().upper())


def normalize_digits(text: str) -> str:
    return text.translate(_DIGIT_MAP)


def canonicalize_code(text: str) -> str:
    t = normalize_code(text)
    t = re.sub(r"^EO(GO|GM|F|G)", r"E0\1", t)
    t = re.sub(r"^E06M", "E0GM", t)
    return t


def normalize_alnum_code(text: str) -> str:
    text = canonicalize_code(text)
    for prefix in ("ZGRU", "CIM", "MMAU", "MNBU", "E0GM", "E0GO", "E0F", "E0G", "E0", "SC"):
        if text.startswith(prefix):
            rest = re.sub(r"[^A-Z0-9]", "", normalize_digits(text[len(prefix) :]))
            return prefix + rest
    if sum(ch.isdigit() or ch in "OILSB" for ch in text) >= max(4, int(len(text) * 0.75)):
        return re.sub(r"\D", "", normalize_digits(text))
    return re.sub(r"[^A-Z0-9]", "", text)


def _block_center(block: dict[str, Any]) -> tuple[float, float, float, float]:
    bbox = block.get("bbox") or []
    if not bbox:
        return 0.0, 0.0, 0.0, 0.0
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0


def _candidate(
    codigo: str,
    tipo: str,
    confianza: float,
    bbox: list | None,
    fuente: str,
    score: float,
    orientacion: str = "horizontal",
) -> dict[str, Any]:
    return {
        "codigo": codigo,
        "tipo": tipo,
        "confianza": round(float(confianza), 4),
        "orientacion": orientacion,
        "bbox": bbox or [],
        "fuente": fuente,
        "score": score,
    }


def _only_digits(text: str) -> str:
    return re.sub(r"\D", "", normalize_digits(text))


def _looks_like_phone(texto: str, digits: str = "") -> bool:
    t = texto.upper()
    if re.search(r"\+\d{1,3}|WHATSAPP|ATENCION|\bTEL\b|\bFAX\b|\b51\s*9\d{8}\b", t):
        return True
    # +51 905464451 / 51-905464451
    if re.search(r"(?:^|[^\d])51[\s\-]?9\d{8}(?:[^\d]|$)", t):
        return True
    d = digits or _only_digits(texto)
    # Móviles PE: 9 dígitos empezando por 9; o 11 con prefijo 51
    if len(d) == 9 and d.startswith("9"):
        return True
    if len(d) >= 11 and d.startswith("51"):
        return True
    if len(d) >= 12:
        return True
    return False


def _fix_zgru_prefix(raw: str) -> str | None:
    m = _ZGRU_RE.search(raw)
    if not m:
        text = normalize_code(raw).replace("ZGR0", "ZGRU")
        m2 = re.search(r"ZGRU([0-9OIlSB]{4,})", text, re.I)
        if not m2:
            return None
        digits = _only_digits(m2.group(1))
    else:
        digits = _only_digits(m.group(1))
    if len(digits) < 4:
        return None
    # Dominio: 7 dígitos (a veces 8 en placas). Si hay más, recortar a 7/8.
    if len(digits) > 8:
        digits = digits[:7] if digits.startswith("0") else digits[:8]
    return f"ZGRU{digits}"


def _rule_zgru_prefix(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in blocks:
        codigo = _fix_zgru_prefix(str(b.get("texto") or ""))
        if not codigo:
            continue
        digits = codigo[4:]
        conf = float(b.get("confianza") or 0)
        bonus = 10.0 if len(digits) == 7 else (6.0 if len(digits) == 8 else 0.0)
        out.append(
            _candidate(
                codigo,
                "ZGRU",
                conf,
                b.get("bbox"),
                "regla_zgru_prefijo",
                score=105 + conf + bonus,
            )
        )
    joined = " ".join(str(b.get("texto") or "") for b in blocks)
    codigo = _fix_zgru_prefix(joined)
    if codigo and not any(c["codigo"] == codigo for c in out):
        conf = max((float(b.get("confianza") or 0) for b in blocks), default=0.5)
        out.append(
            _candidate(
                codigo,
                "ZGRU",
                conf,
                blocks[0].get("bbox") if blocks else [],
                "regla_zgru_unido",
                score=102 + conf + (10.0 if len(codigo[4:]) == 7 else 0.0),
            )
        )

    # ZGRU en un bloque + columna de dígitos debajo (check digit en caja aparte)
    for zb in blocks:
        zt = str(zb.get("texto") or "")
        if not re.search(r"Z\s*G\s*R\s*U", zt, re.I):
            continue
        zx, zy, _, zh = _block_center(zb)
        below: list[tuple[float, str, dict[str, Any]]] = []
        for b in blocks:
            if b is zb:
                continue
            d = _only_digits(str(b.get("texto") or ""))
            if not d or len(d) > 8:
                continue
            if _looks_like_phone(str(b.get("texto") or ""), d):
                continue
            x, y, _, _ = _block_center(b)
            if abs(x - zx) > 55:
                continue
            if y < zy - zh * 0.2:
                continue
            below.append((y, d, b))
        if not below:
            continue
        below.sort(key=lambda t: t[0])
        seq = "".join(t[1] for t in below)
        # Preferir 7 dígitos; si hay 8 (7+check), tomar 7 u 8 según longitud
        for length in (7, 8):
            if len(seq) >= length:
                digits = seq[:length]
                if digits.isdigit():
                    conf = float(zb.get("confianza") or 0.8)
                    out.append(
                        _candidate(
                            f"ZGRU{digits}",
                            "ZGRU",
                            conf,
                            zb.get("bbox"),
                            "regla_zgru_columna",
                            score=112 + conf + (5.0 if length == 7 else 0.0),
                            orientacion="vertical",
                        )
                    )
    return out


def _rule_siete_digitos_zgru(
    blocks: list[dict[str, Any]],
    *,
    modo: Modo,
) -> list[dict[str, Any]]:
    """OTRO ≡ ZGRU sin prefijo: exactamente 7 dígitos (típico en vertical)."""
    out: list[dict[str, Any]] = []
    vertical_boost = 12.0 if modo == "vertical" else 4.0

    for b in blocks:
        texto = str(b.get("texto") or "")
        if _looks_like_phone(texto):
            continue
        for m in _SEVEN_DIGITS_RE.finditer(texto):
            digits = _only_digits(m.group(1))
            if len(digits) != 7:
                continue
            if _looks_like_phone(texto, digits):
                continue
            if len(set(digits)) == 1:
                continue  # 0000000 / 1111111
            conf = float(b.get("confianza") or 0)
            out.append(
                _candidate(
                    digits,
                    "ZGRU",
                    conf,
                    b.get("bbox"),
                    "regla_zgru_7digitos",
                    score=95 + conf + vertical_boost,
                    orientacion="vertical" if modo == "vertical" else "horizontal",
                )
            )
        # OCR a veces inserta 1 dígito de más (8→7 eliminando uno)
        for m in _EIGHT_DIGITS_RE.finditer(texto):
            eight = _only_digits(m.group(1))
            if len(eight) != 8 or _looks_like_phone(texto, eight):
                continue
            conf = float(b.get("confianza") or 0)
            for i in range(8):
                digits = eight[:i] + eight[i + 1 :]
                if len(set(digits)) == 1:
                    continue
                out.append(
                    _candidate(
                        digits,
                        "ZGRU",
                        conf * 0.9,
                        b.get("bbox"),
                        "regla_zgru_8a7",
                        score=88 + conf + vertical_boost,
                        orientacion="vertical" if modo == "vertical" else "horizontal",
                    )
                )

    # 7 dígitos + dígito en caja debajo → a veces el GT incluye el check (7)
    # o el OCR parte 0007807 + 3 → 0078073
    sevens: list[tuple[dict[str, Any], str]] = []
    ones: list[tuple[dict[str, Any], str]] = []
    for b in blocks:
        d = _only_digits(str(b.get("texto") or ""))
        if _looks_like_phone(str(b.get("texto") or ""), d):
            continue
        if len(d) == 7:
            sevens.append((b, d))
        elif len(d) == 1:
            ones.append((b, d))
    for b7, d7 in sevens:
        x7, y7, _, h7 = _block_center(b7)
        for b1, d1 in ones:
            x1, y1, _, _ = _block_center(b1)
            if abs(x1 - x7) > 50:
                continue
            if not (y1 > y7 and y1 - y7 <= h7 * 3.5):
                continue
            # Variante: últimos 6 de d7 + check → 7 (caso 0007807 + 3 → 0078073)
            cand7 = d7[1:] + d1 if d7.startswith("0") and len(d7) == 7 else None
            conf = float(b7.get("confianza") or 0)
            if cand7 and len(cand7) == 7:
                out.append(
                    _candidate(
                        cand7,
                        "ZGRU",
                        conf,
                        b7.get("bbox"),
                        "regla_zgru_checkdigit",
                        score=108 + conf + vertical_boost,
                        orientacion="vertical",
                    )
                )

    # Ensamblar fragmentos verticales (dígitos cortos apilados) → 7
    fragments: list[tuple[float, float, str, dict[str, Any]]] = []
    for b in blocks:
        texto = str(b.get("texto") or "").strip()
        if re.search(r"[A-Za-z]{3,}", texto) and not re.fullmatch(r"[0-9OIlSB\s\-]+", texto):
            continue
        digits = _only_digits(texto)
        if 1 <= len(digits) <= 4:
            x, y, _, _ = _block_center(b)
            fragments.append((y, x, digits, b))

    if fragments:
        # Columna vertical: ordenar por Y, misma X aprox.
        fragments.sort(key=lambda t: (t[0], t[1]))
        # Agrupar por proximidad en X
        groups: list[list[tuple[float, float, str, dict[str, Any]]]] = []
        for frag in fragments:
            placed = False
            for group in groups:
                if abs(frag[1] - group[0][1]) <= 40:
                    group.append(frag)
                    placed = True
                    break
            if not placed:
                groups.append([frag])

        for group in groups:
            group.sort(key=lambda t: t[0])
            seq = "".join(t[2] for t in group)
            # Ventanas exactas de 7
            for i in range(0, max(0, len(seq) - 6)):
                digits = seq[i : i + 7]
                if not digits.isdigit():
                    continue
                conf = float(group[0][3].get("confianza") or 0.7)
                out.append(
                    _candidate(
                        digits,
                        "ZGRU",
                        conf,
                        group[0][3].get("bbox"),
                        "regla_zgru_7_ensamblado",
                        score=92 + conf + vertical_boost,
                        orientacion="vertical",
                    )
                )

    # Completar 6 dígitos + dígito vecino → 7
    sixes: list[tuple[dict[str, Any], str]] = []
    ones: list[tuple[dict[str, Any], str]] = []
    for b in blocks:
        d = _only_digits(str(b.get("texto") or ""))
        if len(d) == 6:
            sixes.append((b, d))
        elif len(d) == 1:
            ones.append((b, d))
    for b6, d6 in sixes:
        x6, y6, _, h6 = _block_center(b6)
        for b1, d1 in ones:
            x1, y1, _, _ = _block_center(b1)
            # Vecino abajo/arriba (vertical) o a la derecha
            near_v = abs(x1 - x6) <= 45 and abs(y1 - y6) <= h6 * 2.5
            near_h = abs(y1 - y6) <= h6 * 0.6 and abs(x1 - x6) <= 120
            if not (near_v or near_h):
                continue
            digits = d6 + d1 if y1 >= y6 or x1 >= x6 else d1 + d6
            if len(digits) != 7:
                continue
            conf = float(b6.get("confianza") or 0)
            out.append(
                _candidate(
                    digits,
                    "ZGRU",
                    conf,
                    b6.get("bbox"),
                    "regla_zgru_6mas1",
                    score=90 + conf + vertical_boost,
                    orientacion="vertical" if near_v else "horizontal",
                )
            )

    return out


def _is_serial_label_text(texto: str) -> bool:
    t = texto.strip()
    if not _SERIAL_LABEL_TOKEN_RE.search(t):
        return False
    # Evitar frases largas que solo mencionan serial al pasar
    if any(s in t.upper() for s in _STOP_SUBSTR):
        return False
    return True


_DATE_SERIAL_RE = re.compile(
    r"^(?:0[1-9]|1[0-2])(?:20)?2[0-9]$|^(?:20)?2[0-9](?:0[1-9]|1[0-2])$"
)


def _looks_like_date_code(valor: str) -> bool:
    """Fechas de placa (06/2024 → 062024, 2025) no son serial."""
    if not valor.isdigit():
        return False
    if _DATE_SERIAL_RE.fullmatch(valor):
        return True
    # Años sueltos del OCR (2015, 02/2025 → 2025)
    if len(valor) == 4 and 2000 <= int(valor) <= 2035:
        return True
    if len(valor) == 6 and valor[:2] in {f"{m:02d}" for m in range(1, 13)} and valor[2:] in {
        "2023",
        "2024",
        "2025",
        "2026",
        "2027",
    }:
        return True
    # Mes/año incompleto tipo 0624
    if len(valor) == 4 and valor[:2] in {f"{m:02d}" for m in range(1, 13)} and valor[2:] in {
        "23",
        "24",
        "25",
        "26",
        "27",
    }:
        return True
    return False


def _clean_serial_value(raw: str, *, allow_short: bool = False) -> str | None:
    valor = normalize_alnum_code(raw)
    min_len = 4 if allow_short else 4
    if len(valor) < min_len or valor in _STOP_CODES:
        return None
    if any(s in valor for s in _STOP_SUBSTR):
        return None
    if not any(ch.isdigit() for ch in valor):
        return None
    if _looks_like_date_code(valor):
        return None
    # Refrigerante / gas de placa
    if re.fullmatch(r"R\d{2,4}[A-Z]?", valor):
        return None
    letters = sum(ch.isalpha() for ch in valor)
    digits = sum(ch.isdigit() for ch in valor)
    if letters >= 6 and letters > digits:
        return None
    # Rechazar basura tipo SCMC140V / modelos cortos sin patrón de serie
    if re.fullmatch(r"[A-Z]{2,}\d{0,3}[A-Z0-9]{0,3}", valor) and digits < 4:
        return None
    if valor.startswith("SC") and digits < 5 and not allow_short:
        return None
    # Modelos tipo SCU40 / SC2500713: no son el serial a la derecha del label
    if allow_short and re.fullmatch(r"SC[A-Z]?\d{4,}", valor):
        return None
    # Fuera del ROI: números cortos suelen ser ruido. En ROI derecha de Serial: sí.
    if valor.isdigit() and len(valor) < 6 and not allow_short:
        return None
    if allow_short and valor.isdigit() and len(valor) < 4:
        return None
    # Concatenaciones fecha+código (1006251077293)
    if valor.isdigit() and len(valor) > 10:
        return None
    return valor


def extract_serial_from_right_roi(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """ROI = banda a la derecha de Serial. Acepta códigos cortos (4–6)."""
    if not blocks:
        return None

    # Centro vertical del ROI ≈ línea de Serial
    ys = []
    for b in blocks:
        _x, y, _w, h = _block_center(b)
        ys.append(y)
    y_mid = sum(ys) / len(ys) if ys else 0.0

    candidates: list[dict[str, Any]] = []
    for b in blocks:
        texto = str(b.get("texto") or "")
        if _SERIAL_LABEL_TOKEN_RE.fullmatch(texto.strip()):
            continue
        # Recuperar CIM desde ID/JD…M1077293 en la misma línea
        m_cim = re.search(r"(?:ID|JD|SN).*?M([0-9OIlSB]{6,})", texto, re.I)
        if m_cim:
            digs = _only_digits(m_cim.group(1))
            if len(digs) >= 6:
                texto = f"CIM{digs}"
        valor = _clean_serial_value(texto, allow_short=True)
        if not valor:
            m = re.search(r"([A-Z0-9]{4,})", normalize_code(texto))
            if m:
                valor = _clean_serial_value(m.group(1), allow_short=True)
        if not valor:
            continue
        conf = float(b.get("confianza") or 0)
        x, y, _w, h = _block_center(b)
        # Prefijos reales de serie (no SC modelo)
        prefix_bonus = 8.0 if valor.startswith(("E0", "CIM", "MMAU", "MNBU")) else 0.0
        # En placas Carrier/Thermo: serial corto 4–5 dígitos; 6 dígitos suele ser modelo
        if valor.isdigit() and len(valor) in (4, 5):
            short_bonus = 7.0
        elif valor.isdigit() and len(valor) == 6:
            short_bonus = 2.0
        else:
            short_bonus = 0.0
        # Pegado a la línea horizontal de Serial (centro del ROI)
        y_pen = abs(y - y_mid) * 0.12
        candidates.append(
            _candidate(
                valor,
                "SERIAL",
                conf,
                b.get("bbox"),
                "regla_serial_roi_derecha",
                score=100 + conf + prefix_bonus + short_bonus + min(len(valor), 12) * 0.1
                - x * 0.0005
                - y_pen,
                orientacion="horizontal",
            )
        )
    if not candidates:
        return None
    # Preferir prefijo fuerte o serial corto 4–5; si no, 6 dígitos
    preferred = [
        c
        for c in candidates
        if str(c["codigo"]).startswith(("E0", "CIM", "MMAU", "MNBU"))
        or (str(c["codigo"]).isdigit() and len(str(c["codigo"])) in (4, 5))
    ]
    if not preferred:
        preferred = [
            c for c in candidates if str(c["codigo"]).isdigit() and len(str(c["codigo"])) == 6
        ]
    pool = preferred or candidates
    return max(pool, key=lambda c: float(c["score"]))


def extract_seven_from_vertical_roi(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """ROI = columna vertical ampliada. Busca/agrupa exactamente 7 dígitos."""
    cands = _rule_siete_digitos_zgru(blocks, modo="vertical")
    # También prefijo ZGRU si aparece en el ROI
    cands.extend(_rule_zgru_prefix(blocks))
    if not cands:
        return None
    # Solo 7 dígitos (o ZGRU+7)
    filtered = []
    for c in cands:
        code = str(c.get("codigo") or "")
        digs = _only_digits(code[4:] if code.startswith("ZGRU") else code)
        if len(digs) == 7 and len(set(digs)) > 1:
            filtered.append(c)
        elif code.startswith("ZGRU") and len(digs) in (7, 8):
            filtered.append(c)
    if not filtered:
        return None
    best = max(filtered, key=_rank_key)
    best = dict(best)
    best["fuente"] = str(best.get("fuente") or "") + "+roi_vertical"
    best["score"] = float(best.get("score") or 0) + 15
    best["orientacion"] = "vertical"
    return best


def _same_horizontal_line(
    label: dict[str, Any],
    other: dict[str, Any],
    *,
    y_tol_ratio: float = 0.55,
) -> bool:
    """True si other está en la misma línea horizontal que label."""
    _lx, ly, _lw, lh = _block_center(label)
    _ox, oy, _ow, oh = _block_center(other)
    tol = max(lh, oh, 12.0) * y_tol_ratio
    return abs(oy - ly) <= tol


def _rule_serial_misma_linea(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """El código de serie está en la misma línea horizontal que 'Serial…'."""
    out: list[dict[str, Any]] = []

    for label in blocks:
        texto = str(label.get("texto") or "")
        if not _is_serial_label_text(texto):
            continue

        # 1) Valor en el mismo bloque, a la derecha del label
        m = _SERIAL_INLINE_RE.search(texto)
        if m:
            # Evitar capturar la palabra NUMBER
            valor = _clean_serial_value(m.group(1))
            if valor and valor not in {"NUMBER", "SERIAL"}:
                conf = float(label.get("confianza") or 0)
                out.append(
                    _candidate(
                        valor,
                        "SERIAL",
                        conf,
                        label.get("bbox"),
                        "regla_serial_inline",
                        score=110 + conf,
                        orientacion="horizontal",
                    )
                )

        lx, ly, lw, lh = _block_center(label)
        best: dict[str, Any] | None = None
        best_key: tuple = (-1.0, -1.0)

        for other in blocks:
            if other is label:
                continue
            if not _same_horizontal_line(label, other, y_tol_ratio=0.9):
                continue
            ox, oy, ow, oh = _block_center(other)
            # Preferir a la derecha del label (misma línea)
            if ox + ow * 0.2 < lx:
                continue
            valor = _clean_serial_value(str(other.get("texto") or ""), allow_short=True)
            if not valor:
                continue
            conf = float(other.get("confianza") or 0)
            dist_x = max(0.0, ox - (lx + lw / 2))
            prefix_bonus = 5.0 if valor.startswith(("E0", "CIM", "MMAU", "MNBU")) else 0.0
            short_bonus = 4.0 if valor.isdigit() and 4 <= len(valor) <= 6 else 0.0
            length_bonus = min(len(valor), 12) * 0.1
            key = (prefix_bonus + short_bonus + conf + length_bonus, -dist_x, -abs(oy - ly))
            if key > best_key:
                best_key = key
                best = _candidate(
                    valor,
                    "SERIAL",
                    conf,
                    other.get("bbox"),
                    "regla_serial_misma_linea",
                    score=108 + conf + prefix_bonus + short_bonus + length_bonus - dist_x * 0.002,
                    orientacion="horizontal",
                )
        if best:
            out.append(best)

        # 2) Columna a la DERECHA del label Serial (valor puede estar un poco arriba/abajo)
        if best is None:
            best2 = None
            best_key2: tuple = (-1e18, 0.0)
            for other in blocks:
                if other is label:
                    continue
                ox, oy, ow, oh = _block_center(other)
                if ox <= lx + lw * 0.3:
                    continue
                # Hasta ~2.2× altura del label en vertical (columna derecha)
                if abs(oy - ly) > max(lh, oh, 14.0) * 2.2:
                    continue
                valor = _clean_serial_value(str(other.get("texto") or ""), allow_short=True)
                if not valor:
                    continue
                conf = float(other.get("confianza") or 0)
                dist_y = abs(oy - ly)
                prefix_bonus = 5.0 if valor.startswith(("E0", "CIM", "MMAU", "MNBU")) else 0.0
                short_bonus = 4.0 if valor.isdigit() and 4 <= len(valor) <= 6 else 0.0
                key2 = (prefix_bonus + short_bonus + conf - dist_y * 0.05, -dist_y)
                if key2 > best_key2:
                    best_key2 = key2
                    best2 = _candidate(
                        valor,
                        "SERIAL",
                        conf,
                        other.get("bbox"),
                        "regla_serial_derecha",
                        score=100 + conf + prefix_bonus + short_bonus - dist_y * 0.05,
                        orientacion="horizontal",
                    )
            if best2:
                out.append(best2)

    return out


def _rule_prefix_codes(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in blocks:
        texto = str(b.get("texto") or "")
        if re.search(r"tel|fax", texto, re.I):
            continue
        for m in _PREFIX_RE.finditer(texto):
            codigo = normalize_alnum_code(m.group(1))
            if any(s in codigo for s in _STOP_SUBSTR):
                continue
            conf = float(b.get("confianza") or 0)
            out.append(
                _candidate(
                    codigo,
                    "SERIAL",
                    conf,
                    b.get("bbox"),
                    "regla_prefijo",
                    score=86 + conf + min(len(codigo), 16) * 0.05,
                    orientacion="horizontal",
                )
            )
        # ID…M1077293 → CIM…
        m_tail = re.search(r"(?:ID|SN).*?M([0-9OIlSB]{6,})", texto, re.I)
        if m_tail:
            digits = _only_digits(m_tail.group(1))
            if len(digits) >= 6:
                conf = float(b.get("confianza") or 0)
                out.append(
                    _candidate(
                        f"CIM{digits}",
                        "SERIAL",
                        conf,
                        b.get("bbox"),
                        "regla_cim_desde_id",
                        score=84 + conf,
                        orientacion="horizontal",
                    )
                )
    return out


def _rule_digits_fallback(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fallback débil: solo 5–6 dígitos (lectura incompleta). Nunca 8+."""
    out: list[dict[str, Any]] = []
    for b in blocks:
        texto = str(b.get("texto") or "")
        if re.search(r"tel|fax|http|www|\(\d{2,}\)", texto, re.I):
            continue
        for m in _DIGITS_RE.finditer(texto):
            digits = _only_digits(m.group(0))
            if len(digits) not in (5, 6):
                continue  # 7 lo maneja regla ZGRU; 8+ suele ser ruido
            conf = float(b.get("confianza") or 0)
            out.append(
                _candidate(
                    digits,
                    "ZGRU",
                    conf,
                    b.get("bbox"),
                    "regla_digitos_fallback",
                    score=28 + conf + (2.0 if len(digits) == 6 else 0.0),
                )
            )
    return out


def _rank_key(c: dict[str, Any]) -> tuple:
    tipo_rank = {"SERIAL": 3, "ZGRU": 2, "OTRO": 1}
    code = str(c.get("codigo") or "")
    # SERIAL gana en horizontal; 7 dígitos ZGRU muy fuertes
    siete = 1 if (c.get("tipo") == "ZGRU" and len(re.sub(r"\D", "", code)) == 7) else 0
    if code.startswith("ZGRU") and len(code) >= 11:
        siete = 1
    prefix = 1 if code.startswith(("E0", "CIM", "MMAU", "MNBU", "ZGRU")) else 0
    return (
        tipo_rank.get(str(c.get("tipo")), 0),
        prefix,
        siete,
        float(c.get("score") or 0),
        float(c.get("confianza") or 0),
    )


_CHIP_MARCA = re.compile(r"alai|alaisecure|suma\s*m[oó]vil", re.IGNORECASE)


def _bloques_de_digitos(blocks: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    partes: list[tuple[str, dict[str, Any]]] = []
    for bloque in blocks:
        bruto = str(bloque.get("texto") or "").strip()
        digitos = re.sub(r"\D", "", bruto)
        if not digitos:
            continue
        letras = re.sub(r"[\d\s.\-:/]", "", bruto)
        if letras:
            continue
        partes.append((digitos, bloque))
    return partes


def extract_chip(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """IMEI de tarjeta o chip. No clasifica contenedor ni serie."""
    if not blocks:
        return None
    imeis: list[tuple[str, dict[str, Any]]] = []
    fragmentos: list[tuple[str, dict[str, Any]]] = []
    es_tarjeta = False

    def anotar_imei(codigo: str, bloque: dict[str, Any]) -> None:
        if 14 <= len(codigo) <= 22 and codigo.startswith("8951") and all(item[0] != codigo for item in imeis):
            imeis.append((codigo, bloque))

    def anotar_fragmento(codigo: str, bloque: dict[str, Any]) -> None:
        if codigo.startswith("8951") or not (8 <= len(codigo) <= 13):
            return
        if len(codigo) == 9 and codigo.startswith("9"):
            return
        if len(codigo) >= 11 and codigo.startswith("51"):
            return
        if all(item[0] != codigo for item in fragmentos):
            fragmentos.append((codigo, bloque))

    for bloque in blocks:
        texto = str(bloque.get("texto") or "")
        if _CHIP_MARCA.search(texto):
            es_tarjeta = True
        digitos = re.sub(r"\D", "", texto)
        for hallazgo in re.finditer(r"8951\d{10,18}", digitos):
            anotar_imei(hallazgo.group(0), bloque)
        anotar_fragmento(digitos, bloque)

    partes = _bloques_de_digitos(blocks)
    for indice, (digitos, bloque) in enumerate(partes):
        if digitos.startswith("8951") and len(digitos) < 14:
            junto = digitos
            for siguiente, _origen in partes[indice + 1 :]:
                if len(junto) >= 19:
                    break
                junto += siguiente
            anotar_imei(junto, bloque)
        if not digitos.startswith("8951") and indice + 1 < len(partes):
            anotar_fragmento(digitos + partes[indice + 1][0], bloque)

    if not imeis and not fragmentos and not es_tarjeta:
        return None

    numeros = [codigo for codigo, _bloque in imeis]
    pistas = [codigo for codigo, _bloque in fragmentos]
    if imeis:
        codigo, bloque = sorted(imeis, key=lambda item: (len(item[0]) == 19, len(item[0]), float(item[1].get("confianza") or 0)), reverse=True)[0]
        fuente = "regla_chip_imei"
    else:
        codigo, bloque = sorted(fragmentos, key=lambda item: (len(item[0]), float(item[1].get("confianza") or 0)), reverse=True)[0] if fragmentos else ("", blocks[0])
        fuente = "regla_chip_fragmento" if codigo else "regla_chip_tarjeta"
    if not codigo:
        return {
            "codigo": None,
            "tipo": "CHIP",
            "confianza": None,
            "orientacion": "horizontal",
            "bbox": [],
            "fuente": fuente,
            "score": 0,
            "numeros": [],
            "fragmentos": [],
            "es_tarjeta": es_tarjeta,
        }
    candidato = _candidate(
        codigo,
        "CHIP",
        float(bloque.get("confianza") or 0.5),
        bloque.get("bbox"),
        fuente,
        score=120 if fuente == "regla_chip_imei" else 80,
    )
    candidato["numeros"] = numeros
    candidato["fragmentos"] = pistas
    candidato["es_tarjeta"] = es_tarjeta or bool(numeros)
    return candidato


_MODELO_MODULO = re.compile(r"ZTRACK\s*-?\s*V\s*2", re.I)
_SN_MODULO = re.compile(r"005010\d{12,16}")
_IMEI_MODULO = re.compile(r"86\d{13}")


def _anotar_unico(lista: list[str], valor: str) -> None:
    if valor and valor not in lista:
        lista.append(valor)


def _sn_de(valor: str) -> str:
    digitos = _only_digits(valor)
    hallazgo = _SN_MODULO.search(digitos)
    if not hallazgo:
        return ""
    sn = hallazgo.group(0)
    return sn if 18 <= len(sn) <= 22 else ""


def _imei_de(valor: str) -> str:
    digitos = _only_digits(valor)
    if digitos.startswith("005010") or digitos.startswith("8951"):
        return ""
    hallazgo = _IMEI_MODULO.search(digitos)
    if not hallazgo:
        return ""
    imei = hallazgo.group(0)
    return imei if len(imei) == 15 and not imei.startswith("8951") else ""


def extract_modulo(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Etiqueta ZTRACK-V2. El SN busca el módulo. El IMEI queda para la señal."""
    if not blocks:
        return None
    textos = [str(bloque.get("texto") or "") for bloque in blocks]
    junto = "\n".join(textos)
    modelo = "ZTRACK-V2" if _MODELO_MODULO.search(junto) else ""
    sns: list[str] = []
    imeis: list[str] = []

    for hallazgo in re.finditer(r"SN[:\s.\-]*([0-9OILSB]{16,24})", junto, re.I):
        _anotar_unico(sns, _sn_de(hallazgo.group(1)))
    for hallazgo in re.finditer(r"IMEI[:\s.\-]*([0-9OILSB]{14,18})", junto, re.I):
        _anotar_unico(imeis, _imei_de(hallazgo.group(1)))
    for bloque in blocks:
        bruto = str(bloque.get("texto") or "")
        _anotar_unico(sns, _sn_de(bruto))
        _anotar_unico(imeis, _imei_de(bruto))

    partes = _bloques_de_digitos(blocks)
    for indice, (digitos, _bloque) in enumerate(partes):
        if digitos.startswith("005010") and len(digitos) < 18:
            junto_sn = digitos
            for siguiente, _origen in partes[indice + 1 :]:
                if len(junto_sn) >= 20 or siguiente.startswith(("86", "8951", "115")):
                    break
                if len(junto_sn) + len(siguiente) > 22:
                    break
                junto_sn += siguiente
            _anotar_unico(sns, _sn_de(junto_sn))
        if digitos.startswith("86") and len(digitos) < 15:
            junto_imei = digitos
            for siguiente, _origen in partes[indice + 1 :]:
                if len(junto_imei) >= 15 or siguiente.startswith(("005", "8951")):
                    break
                if len(junto_imei) + len(siguiente) > 15:
                    break
                junto_imei += siguiente
            _anotar_unico(imeis, _imei_de(junto_imei))

    sns = [sn for sn in sns if sn]
    imeis = [imei for imei in imeis if imei]
    if not sns and not imeis:
        return None
    sn = sns[0] if sns else ""
    imei = imeis[0] if imeis else ""
    fuente = "regla_modulo_sn_imei" if sn and imei else "regla_modulo_sn" if sn else "regla_modulo_imei"
    candidato = _candidate(
        sn or imei,
        "MODULO",
        float(blocks[0].get("confianza") or 0.5),
        blocks[0].get("bbox"),
        fuente,
        score=130 if sn and imei else 90,
    )
    candidato["codigo"] = sn or None
    candidato["sn"] = sn
    candidato["imei"] = imei
    candidato["modelo"] = modelo
    candidato["numeros"] = imeis
    candidato["sns"] = sns
    return candidato


def extract_code(
    blocks: list[dict[str, Any]],
    *,
    modo: Modo = "auto",
) -> dict[str, Any] | None:
    if not blocks:
        return None

    candidates: list[dict[str, Any]] = []
    # Orden de prioridad de dominio
    candidates.extend(_rule_serial_misma_linea(blocks))
    candidates.extend(_rule_zgru_prefix(blocks))
    candidates.extend(_rule_siete_digitos_zgru(blocks, modo=modo))
    candidates.extend(_rule_prefix_codes(blocks))
    candidates.extend(_rule_digits_fallback(blocks))

    if not candidates:
        return None

    best_by_code: dict[str, dict[str, Any]] = {}
    for c in candidates:
        c = dict(c)
        if c.get("tipo") == "SERIAL":
            c["codigo"] = canonicalize_code(c["codigo"])
        elif str(c.get("codigo") or "").startswith("ZGRU"):
            c["codigo"] = canonicalize_code(c["codigo"])
        key = canonicalize_code(c["codigo"])
        prev = best_by_code.get(key)
        if prev is None or _rank_key(c) > _rank_key(prev):
            best_by_code[key] = c

    codes = list(best_by_code.values())
    filtered: list[dict[str, Any]] = []
    for c in codes:
        code = canonicalize_code(c["codigo"])
        dominated = False
        for other in codes:
            other_code = canonicalize_code(other["codigo"])
            if (
                other_code != code
                and other_code.endswith(code)
                and len(other_code) == 7
                and len(code) < 7
                and c.get("tipo") == other.get("tipo") == "ZGRU"
            ):
                dominated = True
                break
            if other_code != code and other_code.startswith(code) and other.get("tipo") == c.get("tipo"):
                # Preferir el más largo solo si no rompe el patrón de 7
                if not (len(code) == 7 and len(other_code) > 7 and c.get("tipo") == "ZGRU"):
                    dominated = True
                    break
        if not dominated:
            filtered.append(c)
    if not filtered:
        filtered = codes

    # En modo vertical: preferir ZGRU de 7 dígitos sobre SERIAL ruidoso
    if modo == "vertical":
        siete = [
            c
            for c in filtered
            if c.get("tipo") == "ZGRU"
            and (
                len(_only_digits(c.get("codigo") or "")) == 7
                or (
                    str(c.get("codigo") or "").startswith("ZGRU")
                    and len(_only_digits(str(c.get("codigo"))[4:])) == 7
                )
            )
        ]
        if siete:
            filtered = siete

    # En modo horizontal: preferir SERIAL si existe
    if modo == "horizontal":
        serials = [c for c in filtered if c.get("tipo") == "SERIAL"]
        if serials:
            filtered = serials

    best = max(filtered, key=_rank_key)
    bbox = best.get("bbox") or []
    if len(bbox) >= 2 and best.get("orientacion") == "horizontal":
        x1, y1 = bbox[0]
        x2, y2 = bbox[1]
        ang = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
        if 60 <= ang <= 120:
            best["orientacion"] = "vertical"
    return best


def codes_match(pred: str | None, truth: str | None) -> bool:
    if not pred or not truth:
        return False
    a = canonicalize_code(pred)
    b = canonicalize_code(truth)
    if a == b:
        return True
    if b.startswith("ZGRU") and a == b[4:]:
        return True
    if a.startswith("ZGRU") and b == a[4:]:
        return True
    # OTRO (7/8 dígitos) ↔ ZGRU+dígitos
    da, db = _only_digits(a), _only_digits(b)
    if len(da) in (7, 8) and len(db) in (7, 8) and da == db:
        return True
    if b.startswith("ZGRU") and da == b[4:] and len(da) in (7, 8):
        return True
    if a.startswith("ZGRU") and db == a[4:] and len(db) in (7, 8):
        return True
    # E0G0000849 ↔ E0GO000849 (G/GO confusión frecuente)
    if re.fullmatch(r"E0G0?\d{6,8}", a) and re.fullmatch(r"E0G0?\d{6,8}", b):
        if _only_digits(a) == _only_digits(b):
            return True
    for prefix in ("MMAU", "MNBU", "CIM", "SC"):
        if b.startswith(prefix) and a == b[len(prefix) :]:
            return True
        if a.startswith(prefix) and b == a[len(prefix) :]:
            return True
    return False
