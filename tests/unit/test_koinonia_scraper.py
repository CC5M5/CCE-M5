"""Tests para src/scrapers/koinonia_scraper.py."""

from __future__ import annotations

from src.scrapers import koinonia_scraper as ks


class TestKoinoniaParser:
    def test_parse_lecturas(self) -> None:
        html = '''
        <h1>Domingo I de Adviento</h1>
        <h2>Primera lectura</h2>
        <p>Is 5,1-7</p>
        <p>Texto de la primera lectura.</p>
        <h2>Salmo</h2>
        <p>"Antífona del salmo" Sal 79,9.12</p>
        <p>Texto del salmo.</p>
        <h2>Evangelio</h2>
        <p>Mt 21,33-43</p>
        <p>Texto del evangelio.</p>
        '''
        parser = ks.KoinoniaParser()
        resultado = parser.parse(html, "20260101")
        assert resultado["fecha"] == "2026-01-01"
        assert resultado["celebracion"] == "Domingo I de Adviento"
        assert resultado["primera_lectura_libro"] == "Is"
        assert resultado["evangelio_libro"] == "Mt"
        assert resultado["temporada"] == "adviento"
        assert resultado["color_liturgico"] == "violeta"

    def test_extraer_cita_y_libro(self) -> None:
        parser = ks.KoinoniaParser()
        resultado = parser._extraer_cita_y_libro("Is 5,1-7")
        assert resultado["libro"] == "Is"
        assert resultado["cita"] == "5,1-7"

    def test_extraer_antifona(self) -> None:
        parser = ks.KoinoniaParser()
        assert parser._extraer_antifona('"Dichoso el pueblo" texto') == "Dichoso el pueblo"
        assert parser._extraer_antifona("sin comillas") is None

    def test_normalizar_fecha(self) -> None:
        parser = ks.KoinoniaParser()
        assert parser._normalizar_fecha("20260101") == "2026-01-01"


class TestKoinoniaClient:
    def test_context_manager(self) -> None:
        with ks.KoinoniaClient() as client:
            assert client is not None
