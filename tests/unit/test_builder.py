"""Tests para src/generators/presentacion/builder.py."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from src.generators.presentacion import builder as b


def test_formatear_fecha() -> None:
    assert b._formatear_fecha("2026-01-01") == "1 de enero de 2026"
    assert b._formatear_fecha("invalid") == "invalid"


def test_celebracion_from_fecha() -> None:
    assert b._celebracion_from_fecha("2026-01-01") == "Domingo"


def test_extraer_frase_evangelio() -> None:
    class Row:
        def __getitem__(self, key):
            if key == "evangelio_texto":
                return 'Texto inicial. "Esta es la frase representativa del evangelio" Final.'
            raise KeyError(key)
        def __contains__(self, key):
            return key == "evangelio_texto"

    frase = b._extraer_frase_evangelio(Row())
    assert "frase representativa" in frase


def test_extraer_frase_evangelio_corta() -> None:
    class Row:
        def __getitem__(self, key):
            return "Corto." if key == "evangelio_texto" else None
        def __contains__(self, key):
            return key == "evangelio_texto"

    frase = b._extraer_frase_evangelio(Row())
    assert frase.startswith("Corto.")


def test_cargar_catalogo_vacio(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(b, "ILUSTRACIONES_DIR", tmp_path)
    assert b._cargar_catalogo() == {}


def test_ilustracion_para_sin_catalogo(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(b, "ILUSTRACIONES_DIR", tmp_path)
    assert b._ilustracion_para("entrada", {}) == ""


def test_get_lectura_y_canciones(tmp_path: Path, monkeypatch) -> None:
    from src import db_manager

    schema_src = Path("/home/pciath/proyectos/CCE-M5-Web-Presentaciones/data/schema.sql")
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())
    db_path = tmp_path / "db.sqlite3"
    db_manager.init_database(db_path)
    monkeypatch.setattr(b, "DB_PATH", db_path)

    conn = db_manager.create_connection(db_path)
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO lecturas (fecha, domingo, temporada, color_liturgico, primera_lectura_texto, salmo_texto, evangelio_texto) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("2026-01-01", "Domingo 1", "ordinario", "verde", "texto", "salmo", "evangelio"),
        )
        lid = cur.lastrowid
        cur.execute(
            "INSERT INTO canciones (titulo, letra_sin_acordes) VALUES (?, ?)",
            ("Canción", "letra"),
        )
        cid = cur.lastrowid
    conn.close()

    lectura = b._get_lectura(lid)
    assert lectura is not None
    assert lectura["temporada"] == "ordinario"

    canciones = b._get_canciones({"entrada": cid})
    assert "entrada" in canciones
    assert canciones["entrada"]["titulo"] == "Canción"


def test_construir_slides(tmp_path: Path, monkeypatch) -> None:
    from src import db_manager

    schema_src = Path("/home/pciath/proyectos/CCE-M5-Web-Presentaciones/data/schema.sql")
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())
    db_path = tmp_path / "db.sqlite3"
    db_manager.init_database(db_path)
    monkeypatch.setattr(b, "DB_PATH", db_path)
    monkeypatch.setattr(b, "ILUSTRACIONES_DIR", tmp_path)

    conn = db_manager.create_connection(db_path)
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO canciones (titulo, letra_sin_acordes) VALUES (?, ?)",
            ("Entrada", "Amor y paz"),
        )
        cid = cur.lastrowid
    conn.close()

    class Lectura:
        def __getitem__(self, key):
            data = {
                "primera_lectura_texto": "Texto primera lectura.",
                "primera_lectura_libro": "Is",
                "primera_lectura_cita": "5,1-7",
                "salmo_texto": "Salmo texto.",
                "salmo_antifona": "Antifona",
                "evangelio_texto": 'Evangelio. "Frase"',
            }
            return data.get(key, "")

    slides = b._construir_slides(
        "2026-01-01",
        Lectura(),
        "Domingo",
        {"entrada": {"id": cid, "titulo": "Entrada", "letra_sin_acordes": "Amor"}},
        {"nombre": "verde", "hex": "#00FF00"},
    )
    assert len(slides) > 0
    assert slides[0].tipo == "portada"
