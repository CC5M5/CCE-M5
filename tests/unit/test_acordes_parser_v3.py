"""Tests para src/parsers/acordes_parser_v3.py."""

from __future__ import annotations

from src.parsers import acordes_parser_v3 as ap3


def test_limpiar_texto_cancion() -> None:
    texto = "<b>Am</b>\nescuchar\nvolver a lista de canciones\nLetra"
    resultado = ap3.limpiar_texto_cancion(texto)
    assert "escuchar" not in resultado
    assert "volver" not in resultado
    assert "Letra" in resultado


def test_limpiar_texto_preservando_espacios() -> None:
    texto = "<b>Am</b>\nvolver a lista\nLinea"
    resultado = ap3.limpiar_texto_preservando_espacios(texto)
    assert "volver" not in resultado
    assert "Linea" in resultado


def test_acorde_posicionado_negativo() -> None:
    try:
        ap3.AcordePosicionado("Am", -1)
    except ValueError:
        pass
    else:
        raise AssertionError("Debería rechazar posición negativa")


def test_es_linea_de_acordes() -> None:
    parser = ap3.AcordesParser()
    assert parser.es_linea_de_acordes("Am G C D") is True
    assert parser.es_linea_de_acordes("Esta es una linea de letra") is False
    assert parser.es_linea_de_acordes("") is False


def test_extraer_acordes_de_linea() -> None:
    parser = ap3.AcordesParser()
    acordes = parser.extraer_acordes_de_linea("Am    G        C")
    assert len(acordes) == 3
    assert acordes[0].acorde == "Am"
    assert acordes[0].posicion == 0
    assert acordes[1].acorde == "G"


def test_parsear_cancion_completa() -> None:
    parser = ap3.AcordesParser()
    resultado = parser.parsear_cancion_completa("Am    G\nAve Maria purisima")
    assert any(linea.tipo == "acordes_letra" for linea in resultado)


def test_parsear_cancion_completa_vacia() -> None:
    parser = ap3.AcordesParser()
    resultado = parser.parsear_cancion_completa("")
    assert len(resultado) == 0


def test_detectar_tono() -> None:
    parser = ap3.AcordesParser()
    estructura = parser.parsear_cancion_completa("Am\nAve\nAm\nMaria")
    tono = parser.detectar_tono(estructura)
    assert tono == "Am"


def test_reconoce_septima_mayor_minuscula() -> None:
    """Reconoce la notación m7M / mM7 / M7 / 7M para séptima mayor."""
    parser = ap3.AcordesParser()
    linea = "Sol            Si7     Mim7M        Do   Dom   Sol"
    assert parser.es_linea_de_acordes(linea) is True
    acordes = parser.extraer_acordes_de_linea(linea)
    assert [a.acorde for a in acordes] == ["Sol", "Si7", "Mim7M", "Do", "Dom", "Sol"]


def test_generar_html_visual() -> None:
    parser = ap3.AcordesParser()
    estructura = parser.parsear_cancion_completa("Am\nAve Maria")
    html = parser.generar_html_visual(estructura)
    assert "Am" in html
    assert "Ave Maria" in html


def test_notacion_inglesa() -> None:
    parser = ap3.AcordesParser()
    acordes = parser.extraer_acordes_de_linea("C Am G/B")
    assert [a.acorde for a in acordes] == ["C", "Am", "G/B"]


def test_normalizar_acorde() -> None:
    parser = ap3.AcordesParser()
    assert parser.normalizar_acorde("am") == "Am"
    assert parser.normalizar_acorde("sol7") == "Sol7"


def test_generar_html_completo() -> None:
    parser = ap3.AcordesParser()
    estructura = parser.parsear_cancion_completa("Am\nAve Maria")
    html = parser.generar_html_completo(estructura)
    assert "Am" in html
    assert "Ave Maria" in html


def test_es_texto_mayuscula() -> None:
    parser = ap3.AcordesParser()
    assert parser._es_texto_mayuscula("TODO MAYUS") is True
    assert parser._es_texto_mayuscula("Todo mixto") is False
