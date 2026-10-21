from app.core.rules import codes_match, extract_code, normalize_code


def _b(texto: str, conf: float = 0.95, x: float = 10, y: float = 10, w: float = 80, h: float = 20) -> dict:
    return {
        "texto": texto,
        "confianza": conf,
        "bbox": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
        "angulo": 0.0,
    }


def test_zgru_basic():
    r = extract_code([_b("ZGRU0078073")])
    assert r is not None
    assert r["codigo"] == "ZGRU0078073"
    assert r["tipo"] == "ZGRU"


def test_zgru_with_space():
    r = extract_code([_b("ZGRU 6921076")])
    assert r is not None
    assert normalize_code(r["codigo"]) == "ZGRU6921076"


def test_siete_digitos_sin_prefijo_es_zgru():
    """OTRO/vertical: 7 dígitos sin ZGRU → se tratan como ZGRU."""
    r = extract_code([_b("8704672")], modo="vertical")
    assert r is not None
    assert r["codigo"] == "8704672"
    assert r["tipo"] == "ZGRU"


def test_serial_same_line_horizontal():
    label = _b("Serial number", x=10, y=40, w=100, h=22)
    value = _b("CIM1077293", x=160, y=42, w=120, h=22)
    r = extract_code([label, value], modo="horizontal")
    assert r is not None
    assert r["codigo"] == "CIM1077293"
    assert r["tipo"] == "SERIAL"
    assert "serial" in r["fuente"]


def test_serial_inline():
    r = extract_code([_b("Serial No: E0F1024682")], modo="horizontal")
    assert r is not None
    assert r["tipo"] == "SERIAL"
    assert "E0F1024682" in r["codigo"]


def test_serial_ignora_bloque_fuera_de_linea():
    label = _b("Serial No", x=10, y=40, w=80, h=20)
    wrong = _b("CAPACITY38", x=200, y=200, w=100, h=20)
    value = _b("E0GM019535", x=120, y=38, w=100, h=20)
    r = extract_code([label, wrong, value], modo="horizontal")
    assert r is not None
    assert r["codigo"] == "E0GM019535"


def test_cim_from_id_pattern():
    r = extract_code([_b("ID0625M1077293")], modo="horizontal")
    assert r is not None
    assert r["codigo"] == "CIM1077293"


def test_codes_match_zgru_and_seven():
    assert codes_match("ZGRU 6921076", "ZGRU6921076")
    assert codes_match("8704672", "ZGRU8704672")
    assert codes_match("ZGRU8704672", "8704672")


def test_codes_match_eo_e0():
    assert codes_match("E0GO000611", "EOGO000611")


def test_assemble_vertical_seven():
    # Fragmentos apilados en columna (misma X)
    blocks = [
        _b("87", x=50, y=10, w=20, h=15),
        _b("04", x=50, y=30, w=20, h=15),
        _b("672", x=52, y=50, w=20, h=15),
    ]
    r = extract_code(blocks, modo="vertical")
    assert r is not None
    assert r["codigo"] == "8704672"


def test_zgru_column_with_checkdigit():
    """ZGRU + 0007807 + dígito 3 en caja → 0078073."""
    blocks = [
        _b("ZGRU", x=100, y=10, w=30, h=40),
        _b("0007807", x=100, y=60, w=30, h=80),
        _b("3", x=102, y=150, w=20, h=20),
    ]
    r = extract_code(blocks, modo="vertical")
    assert r is not None
    assert r["codigo"] in ("ZGRU0078073", "0078073", "ZGRU0007807", "0007807")
    # Preferimos la variante con check digit
    assert "0078073" in r["codigo"] or r["codigo"].endswith("0007807")


def test_reject_phone_as_code():
    r = extract_code(
        [_b("+51 905464451"), _b("ATENCION AL CLIENTE")],
        modo="vertical",
    )
    assert r is None or not str(r.get("codigo", "")).endswith("905464451")


def test_serial_roi_acepta_codigo_corto():
    from app.core.rules import extract_serial_from_right_roi

    # ROI derecha de Serial: solo el valor (puede ser corto)
    r = extract_serial_from_right_roi([_b("84055", x=20, y=10)])
    assert r is not None
    assert r["codigo"] == "84055"
    assert r["tipo"] == "SERIAL"


def test_serial_roi_prefiere_corto_sobre_modelo():
    from app.core.rules import extract_serial_from_right_roi

    # Modelo/fecha en la banda vs serial corto real
    r = extract_serial_from_right_roi(
        [
            _b("810200", x=10, y=10),
            _b("84055", x=80, y=12),
            _b("06/2024", x=140, y=11),
            _b("SC2500713", x=40, y=10),
        ]
    )
    assert r is not None
    assert r["codigo"] == "84055"


def test_seven_from_vertical_roi():
    from app.core.rules import extract_seven_from_vertical_roi

    r = extract_seven_from_vertical_roi([_b("6564180")])
    assert r is not None
    assert r["codigo"] == "6564180"


def test_chip_no_entra_en_contenedor_ni_serie():
    r = extract_code([_b("8951029078500034060"), _b("alaisecure.com")])
    assert r is None or r["tipo"] != "CHIP"
    assert r is None or not str(r.get("codigo") or "").startswith("8951")


def test_chip_imei_de_la_tarjeta():
    from app.core.rules import extract_chip

    r = extract_chip([
        _b("8951029078500034060", x=40, y=20, w=20, h=180),
        _b("alaisecure.com APN alai"),
        _b("500034060", x=80, y=200, w=40, h=16),
    ])
    assert r is not None
    assert r["tipo"] == "CHIP"
    assert r["codigo"] == "8951029078500034060"
    assert "500034060" in r["fragmentos"]


def test_chip_recuadro_alai_sin_codigo_completo():
    from app.core.rules import extract_chip

    r = extract_chip([_b("alaisecure.com"), _b("APN: alai"), _b("500034060")])
    assert r is not None
    assert r["codigo"] == "500034060"
    assert r["fuente"] == "regla_chip_fragmento"


def test_modulo_separa_sn_e_imei_y_deja_fuera_el_chip():
    from app.core.rules import extract_modulo

    r = extract_modulo([
        _b("Model: ZTRACK-V2"),
        _b("Input: DC9-36V"),
        _b("IMEI: 869387065279656"),
        _b("SN: 00501026082100005690"),
        _b("Serial Param: 115200/N/8/1"),
        _b("8951029078500034060"),
    ])
    assert r is not None
    assert r["tipo"] == "MODULO"
    assert r["codigo"] == "00501026082100005690"
    assert r["sn"] == "00501026082100005690"
    assert r["imei"] == "869387065279656"
    assert r["modelo"] == "ZTRACK-V2"
    assert r["numeros"] == ["869387065279656"]
    assert "8951029078500034060" not in r["numeros"]


def test_modulo_junta_sn_e_imei_partidos():
    from app.core.rules import extract_modulo

    r = extract_modulo([
        _b("8693870653"),
        _b("34402"),
        _b("005010260821"),
        _b("00008811"),
    ])
    assert r is not None
    assert r["sn"] == "00501026082100008811"
    assert r["imei"] == "869387065334402"


def test_chip_suelto_partido():
    from app.core.rules import extract_chip

    r = extract_chip([_b("8951029078"), _b("50002327"), _b("9")])
    assert r is not None
    assert r["codigo"] == "8951029078500023279"
