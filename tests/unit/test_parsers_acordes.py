"""Tests para src/parsers/acordes_parser.py y acordes_parser_v2.py."""

from __future__ import annotations

import pytest

from src.parsers import acordes_parser as ap
from src.parsers import acordes_parser_v2 as ap2


class TestAcordesParser:
    def test_detectar_linea_de_acordes(self) -> None:
        parser = ap.AcordesParser()
        assert parser.detectar_acordes_en_linea("SOL   Lam        RE7")
        assert not parser.detectar_acordes_en_linea("PREPARAD EL CAMINO AL SEÑOR")
        assert not parser.detectar_acordes_en_linea("")

    def test_separar_letra_y_acordes(self) -> None:
        parser = ap.AcordesParser()
        texto = "SOL\nPREPARAD EL CAMINO\nLam\nAL SEÑOR"
        resultado = parser.separar_letra_y_acordes(texto)
        assert "PREPARAD EL CAMINO" in resultado["letra"]
        assert "SOL" in resultado["acordes"]
        assert "Lam" in resultado["acordes_lista"]

    def test_detectar_tono(self) -> None:
        parser = ap.AcordesParser()
        assert parser.detectar_tono("SOL Lam RE7 SOL SOL") == "SOL"
        assert parser.detectar_tono("") == "No detectado"

    def test_detectar_momento_liturgico(self) -> None:
        parser = ap.AcordesParser()
        assert parser.detectar_momento_liturgico("Aleluya de la X", "") == "aleluya"
        assert parser.detectar_momento_liturgico("Salmo responsorial", "") == "salmo"
        assert parser.detectar_momento_liturgico("Canción de paz", "") == "paz"
        assert parser.detectar_momento_liturgico("Canción general", "") == "general"


class TestAcordesParserV2:
    def test_parsear_linea_letra(self) -> None:
        parser = ap2.AcordesParser()
        assert parser.parsear_linea_con_acordes("PREPARAD EL CAMINO") == {
            "tipo": "letra",
            "texto": "PREPARAD EL CAMINO",
        }

    def test_parsear_linea_acordes(self) -> None:
        parser = ap2.AcordesParser()
        resultado = parser.parsear_linea_con_acordes("SOL   Lam        RE7")
        assert resultado["tipo"] == "acordes"
        assert {a["acorde"] for a in resultado["acordes"]} == {"SOL", "Lam", "RE7"}

    def test_parsear_linea_mixta(self) -> None:
        parser = ap2.AcordesParser()
        resultado = parser.parsear_linea_con_acordes("SOL      PREPARAD EL CAMINO")
        assert resultado["tipo"] == "mixta"
        assert resultado["letra"] == "PREPARAD EL CAMINO"
        assert resultado["acordes"][0]["acorde"] == "SOL"

    def test_parsear_cancion_completa(self) -> None:
        parser = ap2.AcordesParser()
        texto = "SOL\nPREPARAD EL CAMINO\nLam\nAL SEÑOR"
        estructura = parser.parsear_cancion_completa(texto)
        assert len(estructura) == 4
        assert estructura[0]["tipo"] == "acordes"

    def test_generar_html_visual(self) -> None:
        parser = ap2.AcordesParser()
        estructura = parser.parsear_cancion_completa("SOL\nPREPARAD EL CAMINO")
        html = parser.generar_html_visual(estructura)
        assert "cancion-con-acordes" in html
        assert "linea-acordes" in html
        assert "letra-solo" in html

    def test_detectar_tono_v2(self) -> None:
        parser = ap2.AcordesParser()
        estructura = parser.parsear_cancion_completa("SOL\nPREPARAD\nSOL\nCAMINO\nLam")
        assert parser.detectar_tono(estructura) == "SOL"

    def test_notacion_inglesa(self) -> None:
        parser = ap2.AcordesParser()
        resultado = parser.parsear_linea_con_acordes("G   Am")
        assert resultado["tipo"] == "acordes"
        assert {a["acorde"] for a in resultado["acordes"]} == {"G", "Am"}
