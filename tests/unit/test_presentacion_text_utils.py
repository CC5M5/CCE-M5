"""Tests para utilidades de texto del generador de presentaciones."""

from src.generators.presentacion.text_utils import (
    _apply_bold_html,
    _compactar_para_slide,
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
    assert _es_linea_solo_acordes("Esta es una línea de letra") is False
    assert _es_linea_solo_acordes("Do Re7 (texto)") is False


def test_unir_lineas():
    assert _unir_lineas("Quebranta el", "pan") == "Quebranta el pan"
    # Si la primera línea ya termina en espacio, se conserva tal cual.
    assert _unir_lineas("Quebranta el ", "pan") == "Quebranta el  pan"
    assert _unir_lineas("Amén.", "Amén.") == "Amén. Amén."


def test_formatear_cita():
    assert _formatear_cita("Marcos", "10, 17-27") == "Marcos 10, 17-27"
    assert _formatear_cita("Marcos", "Marcos 10, 17-27") == "Marcos 10, 17-27"
    assert _formatear_cita("", "10, 17-27") == "10, 17-27"
    assert _formatear_cita("Marcos", "") == ""


def test_escape_html():
    assert _escape_html("a < b & c > d \"") == "a &lt; b &amp; c &gt; d &quot;"


def test_apply_bold_html():
    assert _apply_bold_html("**Hola** mundo") == "<strong>Hola</strong> mundo"
    assert _apply_bold_html("sin negrita") == "sin negrita"


def test_paginar_texto():
    texto = "Oración uno. Oración dos. Oración tres. Oración cuatro. Oración cinco. Oración seis."
    paginas = _paginar_texto(texto, max_chars=30)
    # El paginador respeta oraciones completas; puede exceder max_chars para no cortar una oración.
    assert len(paginas) >= 2
    assert all("Oración" in p for p in paginas)
    assert any("." in p for p in paginas)


def test_texto_cancion_limpia_acordes():
    cancion = {
        "letra_sin_acordes": "",
        "letra_con_acordes": "Do  Re7\nQuebranta el pan\n|",
    }
    resultado = _texto_cancion(cancion)
    assert "Do" not in resultado
    assert "Re7" not in resultado
    assert "Quebranta el pan" in resultado


def test_compactar_para_slide():
    texto = "Línea uno\nLínea dos\n\nPárrafo dos\n\n\nPárrafo tres"
    compacto = _compactar_para_slide(texto)
    assert compacto == "Línea uno\nLínea dos\n\nPárrafo dos\n\nPárrafo tres"
    assert "\n\n\n" not in compacto
