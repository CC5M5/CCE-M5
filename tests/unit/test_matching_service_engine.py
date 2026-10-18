"""Tests para src/matching_engine.py MatchingService y MatchingEngine."""

from __future__ import annotations

from pathlib import Path

import pytest

from src import db_manager
from src.matching_engine import MatchingConfig, MatchingEngine, MatchingService


@pytest.fixture
def engine(tmp_path: Path) -> MatchingEngine:
    schema_src = Path("/home/pciath/proyectos/CCE-M5-Web-Presentaciones/data/schema.sql")
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())
    db_manager.init_database(tmp_path / "db.sqlite3")

    conn = db_manager.create_connection(tmp_path / "db.sqlite3")
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO lecturas (fecha, domingo, temporada, color_liturgico, celebracion, primera_lectura_texto, salmo_texto, evangelio_texto) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("2026-01-01", "Domingo 1", "ordinario", "verde", "Domingo ordinario", "amor paz", "texto", "amor hermanos"),
        )
        cur.execute(
            "INSERT INTO canciones (titulo, letra_sin_acordes, momento_liturgico) VALUES (?, ?, ?)",
            ("Canción Amor", "amor amor amor", "entrada"),
        )
        cur.execute(
            "INSERT INTO canciones (titulo, letra_sin_acordes, momento_liturgico) VALUES (?, ?, ?)",
            ("Canción Paz", "paz paz", "comunion"),
        )
    conn.close()

    config = MatchingConfig.from_dict({"db_path": str(tmp_path / "db.sqlite3"), "score_minimo": 0.0, "limite_resultados": 10})
    service = MatchingService(config)
    return MatchingEngine(tmp_path / "db.sqlite3")


def test_matching_engine_analizar_lectura(engine) -> None:
    resultado = engine.analizar_lectura(1)
    assert resultado is not None
    assert isinstance(resultado, list)


def test_matching_engine_analizar_cancion(engine) -> None:
    resultado = engine.analizar_cancion(1)
    assert resultado is not None
    assert any(item["tema"] == "amor" for item in resultado)


def test_matching_engine_calcular_match(engine) -> None:
    temas_lectura = [{"tema": "amor", "score": 1.0, "palabras": ["amor"]}]
    temas_cancion = [{"tema": "amor", "score": 1.0, "palabras": ["amor"]}]
    score = engine.calcular_match(temas_lectura, temas_cancion)
    assert 0.0 < score <= 1.0


def test_matching_engine_encontrar_canciones(engine) -> None:
    matches = engine.encontrar_canciones_para_lectura(1, limite=5, score_minimo=0.0)
    assert isinstance(matches, list)
    assert len(matches) > 0
    assert all("score" in m for m in matches)


def test_matching_service_guardar_match(engine, tmp_path: Path) -> None:
    engine.guardar_match(1, 1, 0.85, "entrada")

    conn = db_manager.create_connection(tmp_path / "db.sqlite3")
    with conn:
        row = conn.execute("SELECT * FROM matches WHERE lectura_id=? AND cancion_id=?", (1, 1)).fetchone()
        assert row is not None
        assert row["score"] == 0.85
    conn.close()


def test_matching_engine_extraer_temas_de_texto(engine) -> None:
    temas = engine.extraer_temas_de_texto("amor paz esperanza")
    assert isinstance(temas, list)
    assert any(t["tema"] == "amor" for t in temas)
