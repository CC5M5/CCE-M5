"""Tests para src/scrapers/ciudadredonda_scraper.py."""

from __future__ import annotations

from pathlib import Path

from src.scrapers.ciudadredonda_scraper import (
    CiudadRedondaClient,
    CiudadRedondaParser,
    CiudadRedondaRepository,
)


class TestParser:
    def test_parse_calendar(self) -> None:
        html = '''
        <div id="mec-calendar-events-sec-20260101">
            <a href="/lecturas/2026-01-01/">Evangelio y Lecturas</a>
        </div>
        '''
        parser = CiudadRedondaParser()
        url = parser.parse_calendar(html, "2026-01-01")
        assert url == "https://www.ciudadredonda.org/lecturas/2026-01-01/"

    def test_parse_calendar_not_found(self) -> None:
        parser = CiudadRedondaParser()
        assert parser.parse_calendar("<html></body></html>", "2026-01-01") is None

    def test_parse_lecturas(self) -> None:
        html = '''
        <h1 class="mec-divi-simple-header">Evangelio y Lecturas de Domingo I de Adviento</h1>
        <h2>Primera lectura</h2>
        <p><b>Lectura del libro de Isaías (5,1-7):</b></p>
        <p>Texto de la primera lectura con palabras.</p>
        <h2>Salmo</h2>
        <p><b>Sal 79,9.12.13-14</b></p>
        <p>R/. Dios mio, restauranos.</p>
        <p>Estrofa del salmo <b>R/.</b></p>
        <h2>Evangelio</h2>
        <p><b>Lectura del santo evangelio según san Mateo (21,33-43):</b></p>
        <p>Texto del evangelio.</p>
        '''
        parser = CiudadRedondaParser()
        resultado = parser.parse_lecturas(html, "2026-01-01")
        assert resultado["celebracion"] == "Domingo I de Adviento"
        assert resultado["primera_lectura_cita"] == "Is 5,1-7"
        assert "Sal 79" in resultado["salmo_cita"]
        assert (resultado["salmo_antifona"] is None) or ("restauranos" in resultado["salmo_antifona"])
        assert resultado["evangelio_cita"] == "Mt 21,33-43"
        assert resultado["temporada"] == "adviento"
        assert resultado["color_liturgico"] == "violeta"

    def test_limpiar_cita(self) -> None:
        parser = CiudadRedondaParser()
        assert parser._limpiar_cita("Lectura del libro de Isaías (5,1-7):") == "Is 5,1-7"
        resultado = parser._limpiar_cita("Lectura de la carta del apóstol san Pablo a los Filipenses (4,6-9):")
        assert "4,6-9" in resultado
        # Fallback para citas sin libro reconocido
        assert "79" in parser._limpiar_cita("Sal 79,9.12.13-14")

    def test_detectar_temporada(self) -> None:
        parser = CiudadRedondaParser()
        from bs4 import BeautifulSoup
        # La regex busca "(\d+)[º°]?\s*domingo", es decir, nÚmero ANTES de "domingo"
        soup = BeautifulSoup("<p>3 domingo de Pascua</p>", "html.parser")
        res = parser._detectar_temporada(soup, "3 domingo de Pascua")
        assert res["temporada"] == "pascua"
        assert res["color_liturgico"] == "blanco"
        assert res["domingo"] == "Domingo 3"


class TestRepository:
    def test_guardar(self, tmp_path: Path) -> None:
        from src import db_manager

        db_path = tmp_path / "db.sqlite3"
        db_manager.init_database(db_path)
        repo = CiudadRedondaRepository(db_path)
        lecturas = {
            "fecha": "2026-01-01",
            "domingo": "Domingo 1",
            "temporada": "adviento",
            "ciclo": "A",
            "color_liturgico": "violeta",
            "celebracion": "Domingo I de Adviento",
            "primera_lectura_cita": "Is 5,1-7",
            "primera_lectura_texto": "texto",
            "salmo_cita": "Sal 79",
            "salmo_antifona": "antifona",
            "salmo_texto": "texto salmo",
            "segunda_lectura_cita": "",
            "segunda_lectura_texto": "",
            "evangelio_cita": "Mt 21,33-43",
            "evangelio_texto": "texto evangelio",
        }
        repo.guardar(lecturas)

        with db_manager.create_connection(db_path) as conn:
            row = conn.execute("SELECT * FROM lecturas WHERE fecha=?", ("2026-01-01",)).fetchone()
            assert row is not None
            assert row["celebracion"] == "Domingo I de Adviento"


class TestClient:
    def test_close(self) -> None:
        client = CiudadRedondaClient()
        client.close()
