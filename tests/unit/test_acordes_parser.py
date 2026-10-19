"""Tests para src/parsers/acordes_parser.py (versión original)."""

from __future__ import annotations

from src.parsers.acordes_parser import AcordesParser


def test_detectar_acordes_en_linea() -> None:
    parser = AcordesParser()
    assert parser.detectar_acordes_en_linea("Do Re Mi") is True
    assert parser.detectar_acordes_en_linea("Do   Re") is True
    assert parser.detectar_acordes_en_linea("Esta es una línea de letra") is False
    assert parser.detectar_acordes_en_linea("") is False


def test_separar_letra_y_acordes() -> None:
    parser = AcordesParser()
    texto = "Do Re\nLínea de letra\nMi Fa"
    resultado = parser.separar_letra_y_acordes(texto)
    assert "Línea de letra" in resultado["letra"]
    assert "Do Re" in resultado["acordes"]
    assert "Mi Fa" in resultado["acordes"]
    assert "Do" in resultado["acordes_lista"]


def test_limpiar_acordes_de_linea() -> None:
    parser = AcordesParser()
    linea = "Do Re Mi Fa esta es la letra"
    limpia = parser._limpiar_acordes_de_linea(linea)
    assert "Do" not in limpia
    assert "esta es letra" in limpia


def test_detectar_tono() -> None:
    parser = AcordesParser()
    assert parser.detectar_tono("Do Re Do Mi") == "Do"
    assert parser.detectar_tono("") == "No detectado"


def test_detectar_momento_liturgico() -> None:
    parser = AcordesParser()
    assert parser.detectar_momento_liturgico("Entrada triunfal", "") == "entrada"
    assert parser.detectar_momento_liturgico("Misericordia", "") == "perdon"
    assert parser.detectar_momento_liturgico("Canción abc def ghi", "") == "general"
