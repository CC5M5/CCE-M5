"""Tests para src/auto_rebuild_presentaciones.py."""

from __future__ import annotations

import importlib
import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src import db_manager


@pytest.fixture
def arb_module(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))
    # Copiar schema.sql real al proyecto temporal
    schema_src = Path("/home/pciath/proyectos/CCE-M5-Web-Presentaciones/data/schema.sql")
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())
    importlib.reload(db_manager)
    from src import auto_rebuild_presentaciones as arb

    importlib.reload(arb)
    db_manager.init_database(arb.DB_PATH)
    return arb


def test_limpiar_letra_priorities(arb_module) -> None:
    arb = arb_module
    assert arb._limpiar_letra("<p>Hola</p>", None, None) == "Hola"
    assert arb._limpiar_letra(None, "letra limpia", None) == "letra limpia"
    assert arb._limpiar_letra(None, None, "con acordes") == "con acordes"
    assert arb._limpiar_letra(None, None, None) == ""


def test_canciones_asignadas(arb_module) -> None:
    arb = arb_module
    assert arb._canciones_asignadas(None) == {}
    assert arb._canciones_asignadas("invalid") == {}
    assert arb._canciones_asignadas('{"entrada": {"id": 5}, "comunion": 7, "paz": "9"}') == {
        "entrada": 5,
        "comunion": 7,
        "paz": 9,
    }
    assert arb._canciones_asignadas("[]") == {}


def test_crear_slides_para_cancion(arb_module) -> None:
    arb = arb_module
    conn = db_manager.create_connection(arb.DB_PATH)
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO canciones (titulo, html_visual, letra_sin_acordes, letra_con_acordes) VALUES (?, ?, ?, ?)",
            ("Aleluya", "<b>Aleluya</b>", "Aleluya", "Am\nAleluya"),
        )
        cid = cur.lastrowid
        cur.executemany(
            "INSERT INTO cancion_momentos (cancion_id, momento_liturgico) VALUES (?, ?)",
            [(cid, "entrada"), (cid, "comunion"), (cid, "acto_penitencial")],
        )
    conn.close()

    slides = arb.crear_slides_para_cancion(cid)
    assert len(slides) == 3
    momentos = {s[0] for s in slides}
    assert momentos == {"entrada", "comunion", "perdon"}

    # Idempotente
    slides2 = arb.crear_slides_para_cancion(cid)
    assert len(slides2) == 3


def test_encontrar_presentaciones_afectadas(arb_module) -> None:
    arb = arb_module
    conn = db_manager.create_connection(arb.DB_PATH)
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO canciones (titulo) VALUES (?)", ("Canción A",)
        )
        cid = cur.lastrowid
        future = (date.today() + timedelta(days=7)).isoformat()
        past = (date.today() - timedelta(days=7)).isoformat()
        cur.execute(
            "INSERT INTO presentaciones (fecha_domingo, canciones_json) VALUES (?, ?)",
            (future, json.dumps({"entrada": {"id": cid}})),
        )
        cur.execute(
            "INSERT INTO presentaciones (fecha_domingo, canciones_json) VALUES (?, ?)",
            (past, json.dumps({"entrada": {"id": cid}})),
        )
    conn.close()

    afectadas = arb.encontrar_presentaciones_afectadas(cid, solo_futuras=True)
    assert len(afectadas) == 1
    assert afectadas[0]["fecha_domingo"] == future

    todas = arb.encontrar_presentaciones_afectadas(cid, solo_futuras=False)
    assert len(todas) == 2


def test_auto_rebuild_tras_cancion(arb_module, monkeypatch) -> None:
    arb = arb_module
    conn = db_manager.create_connection(arb.DB_PATH)
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO canciones (titulo, html_visual) VALUES (?, ?)",
            ("Canción B", "<p>Texto</p>"),
        )
        cid = cur.lastrowid
        cur.execute(
            "INSERT INTO cancion_momentos (cancion_id, momento_liturgico) VALUES (?, ?)",
            (cid, "entrada"),
        )
        future = (date.today() + timedelta(days=7)).isoformat()
        cur.execute(
            "INSERT INTO presentaciones (fecha_domingo, canciones_json) VALUES (?, ?)",
            (future, json.dumps({"entrada": {"id": cid}})),
        )
    conn.close()

    with patch.object(arb_module, "proponer_composicion", return_value=[{"tipo": "entrada", "slide_id": 1}]):
        with patch.object(arb_module, "guardar_composicion"):
            with patch.object(arb_module.GeneradorDesdeComposicion, "generar_desde_presentacion", return_value=None):
                result = arb.auto_rebuild_tras_cancion(cid, solo_futuras=True)

    assert len(result["slides_creadas"]) == 1
    assert future in result["presentaciones_afectadas"]
    assert result["resultados"][0]["status"] == "ok"
