"""Tests para utilidades de texto del generador de presentaciones."""

from src.generators.presentacion.text_utils import (
    _apply_bold_html,
    _compactar_para_slide,
    _compactar_salmo_o_lectura,
    _es_linea_solo_acordes,
    _escape_html,
    _formatear_cita,
    _paginar_texto,
    _texto_cancion,
    _unir_lineas,
)


def test_es_linea_solo_acordes():
    assert _es_linea_solo_acordes("Do  Re7  Mi7") is True
    assert _es_linea_solo_acordes("Do Re7 Mi7") is True
    assert _es_linea_solo_acordes("Do# Reb Mi7") is True
    assert _es_linea_solo_acordes("Esta es una línea de letra") is False
    assert _es_linea_solo_acordes("Do Re7 (texto)") is False


def test_unir_lineas():
    assert _unir_lineas("Quebranta el", "pan") == "Quebranta el pan"
    # Si la primera línea ya termina en espacio, se conserva tal cual.
    assert _unir_lineas("Quebranta el ", "pan") == "Quebranta el  pan"
    assert _unir_lineas("Amén.", "Amén.") == "Amén. Amén."
    assert _unir_lineas("cami-", "no") == "camino"


def test_compactar_salmo_o_lectura():
    texto = "Bendice alma mía al Señor.\nBendice alma mía al Señor\ncontinúa la frase."
    resultado = _compactar_salmo_o_lectura(texto)
    assert "Bendice alma mía al Señor" in resultado
    assert ";" in resultado


def test_compactar_salmo_o_lectura_vacio():
    assert _compactar_salmo_o_lectura("") == ""
    assert _compactar_salmo_o_lectura("   \n\n  ") == ""


def test_compactar_salmo_o_lectura_guion():
    texto = "Línea-\nsegunda línea.\nOtra estrofa."
    resultado = _compactar_salmo_o_lectura(texto)
    assert "Líneasegunda línea" in resultado
    assert "Otra estrofa" in resultado


def test_formatear_cita():
    assert _formatear_cita("Marcos", "10, 17-27") == "Marcos 10, 17-27"
    assert _formatear_cita("Marcos", "Marcos 10, 17-27") == "Marcos 10, 17-27"
    assert _formatear_cita("", "10, 17-27") == "10, 17-27"
    assert _formatear_cita("Marcos", "") == ""


def test_escape_html():
    assert _escape_html('a < b & c > d "') == "a &lt; b &amp; c &gt; d &quot;"
    assert _escape_html("") == ""


def test_apply_bold_html():
    assert _apply_bold_html("**Hola** mundo") == "<strong>Hola</strong> mundo"
    assert _apply_bold_html("sin negrita") == "sin negrita"
    assert _apply_bold_html("**uno** **dos**") == "<strong>uno</strong> <strong>dos</strong>"


def test_paginar_texto():
    texto = "Oración uno. Oración dos. Oración tres. Oración cuatro. Oración cinco. Oración seis."
    paginas = _paginar_texto(texto, max_chars=30)
    # El paginador respeta oraciones completas; puede exceder max_chars para no cortar una oración.
    assert len(paginas) >= 2
    assert all("Oración" in p for p in paginas)
    assert any("." in p for p in paginas)


def test_paginar_texto_unico():
    assert _paginar_texto("corto") == ["corto"]


def test_paginar_texto_oraciones_largas():
    texto = "A. " * 300
    paginas = _paginar_texto(texto, max_chars=100)
    assert len(paginas) > 1
    assert all(len(p) <= 100 for p in paginas)


def test_texto_cancion_limpia_acordes():
    cancion = {
        "letra_sin_acordes": "",
        "letra_con_acordes": "Do  Re7\nQuebranta el pan\n|",
    }
    resultado = _texto_cancion(cancion)
    assert "Do" not in resultado
    assert "Re7" not in resultado
    assert "Quebranta el pan" in resultado


def test_texto_cancion_sin_letra():
    assert _texto_cancion({}) == ""


def test_texto_cancion_mantiene_mayusculas_largas():
    # La línea larga en mayúsculas debe quedar sola para que el post-proceso la marque.
    # Terminamos con signo de exclamación para forzar corte.
    cancion = {"letra_sin_acordes": "AAAAAAAAAA!\nlinea normal"}
    resultado = _texto_cancion(cancion)
    assert "**AAAAAAAAAA!**" in resultado


def test_texto_cancion_marca_estribillo_todos():
    cancion = {"letra_sin_acordes": "Todos\nAleluya hermanos"}
    resultado = _texto_cancion(cancion)
    assert "**Aleluya hermanos**" in resultado


def test_texto_cancion_limpia_basura_y_barras():
    cancion = {"letra_sin_acordes": "volver\n|\n—\nPREPARAD"}
    resultado = _texto_cancion(cancion)
    assert "volver" not in resultado
    assert "PREPARAD" in resultado


def test_texto_cancion_palabras_cortas():
    cancion = {"letra_sin_acordes": "El\ncamino\nDel\nSeñor"}
    resultado = _texto_cancion(cancion)
    assert "El camino" in resultado
    # "Del" se une con la siguiente línea corta pero "Señor" (>8 chars) la rompe.
    assert "Del" in resultado
    assert "Señor" in resultado


def test_texto_cancion_minuscula_une():
    cancion = {"letra_sin_acordes": "Amén\nque así sea"}
    resultado = _texto_cancion(cancion)
    assert "Amén que así sea" in resultado


def test_texto_cancion_terminador_separa():
    cancion = {"letra_sin_acordes": "Ven.\nCantad"}
    resultado = _texto_cancion(cancion)
    assert "Ven." in resultado
    assert "Cantad" in resultado


def test_compactar_para_slide():
    texto = "Línea uno\nLínea dos\n\nPárrafo dos\n\n\nPárrafo tres"
    compacto = _compactar_para_slide(texto)
    assert compacto == "Línea uno\nLínea dos\n\nPárrafo dos\n\nPárrafo tres"
    assert "\n\n\n" not in compacto


def test_compactar_para_slide_vacio():
    assert _compactar_para_slide("") == ""
    assert _compactar_para_slide("   \n\n  ") == ""
