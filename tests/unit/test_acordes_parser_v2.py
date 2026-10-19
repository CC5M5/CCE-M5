"""Tests para src/parsers/acordes_parser_v2.py."""

from __future__ import annotations

from src.parsers.acordes_parser_v2 import AcordesParser


def test_parsear_linea_vacia() -> None:
    parser = AcordesParser()
    assert parser.parsear_linea_con_acordes("") is None
    assert parser.parsear_linea_con_acordes("   ") is None


def test_parsear_linea_letra() -> None:
    parser = AcordesParser()
    resultado = parser.parsear_linea_con_acordes("Solo letra sin acordes")
    assert resultado["tipo"] == "letra"
    assert resultado["texto"] == "Solo letra sin acordes"


def test_parsear_linea_acordes_puros() -> None:
    parser = AcordesParser()
    resultado = parser.parsear_linea_con_acordes("Do Re Mi")
    assert resultado["tipo"] == "acordes"
    assert [a["acorde"] for a in resultado["acordes"]] == ["Do", "Re", "Mi"]


def test_parsear_linea_mixta() -> None:
    parser = AcordesParser()
    resultado = parser.parsear_linea_con_acordes("Do       Re  cantemos todos juntos")
    assert resultado["tipo"] == "mixta"
    assert "cantemos" in resultado["letra"]
    assert len(resultado["acordes"]) == 2


def test_parsear_cancion_completa() -> None:
    parser = AcordesParser()
    texto = "[Intro]\nDo Re\nLínea de letra\nMi Fa Sol"
    resultado = parser.parsear_cancion_completa(texto)
    assert len(resultado) == 4
    tipos = [r["tipo"] for r in resultado]
    assert "letra" in tipos
    assert "acordes" in tipos


def test_generar_html_visual() -> None:
    parser = AcordesParser()
    estructura = [
        {"tipo": "letra", "texto": "Línea"},
        {"tipo": "acordes", "acordes": [{"acorde": "Do"}]},
        {"tipo": "mixta", "acordes": [{"acorde": "Re", "posicion": 0}], "letra": "letra"},
    ]
    html = parser.generar_html_visual(estructura)
    assert "cancion-con-acordes" in html
    assert "Do" in html
    assert "letra-inferior" in html


def test_detectar_tono() -> None:
    parser = AcordesParser()
    estructura = [
        {"tipo": "acordes", "acordes": [{"acorde": "Do"}, {"acorde": "Do"}, {"acorde": "Re"}]},
    ]
    assert parser.detectar_tono(estructura) == "Do"


def test_detectar_tono_vacio() -> None:
    parser = AcordesParser()
    assert parser.detectar_tono([]) == "No detectado"
