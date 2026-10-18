"""Tests para src/web_admin/workflow_engine.py."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src import db_manager


@pytest.fixture
def wf_module(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))
    schema_src = Path("/home/pciath/proyectos/CCE-M5-Web-Presentaciones/data/schema.sql")
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())

    # Limpiar cache de src para forzar relectura de CCE_PROJECT_DIR y DB_PATH
    import sys
    for name in list(sys.modules):
        if name.startswith("src") or name.startswith("src.web_admin"):
            del sys.modules[name]

    from src import db_manager as dbm

    dbm.init_database(dbm.DB_PATH)
    from src.web_admin import workflow_engine as wf

    return wf


def test_handle_init(wf_module) -> None:
    wf = wf_module
    workflow = {"steps_data": {}}
    result = wf.handle_init(workflow, {})
    assert result["success"] is True
    assert result["next_step"] == "fetch_lectures"


def test_handle_fetch_lecturas_success(wf_module, monkeypatch) -> None:
    wf = wf_module
    lecturas = {
        "fecha": "2026-01-01",
        "domingo": "Domingo 1",
        "temporada": "ordinario",
        "color_liturgico": "verde",
        "primera_lectura_cita": "Gn 1,1-10",
        "primera_lectura_texto": "En el principio...",
        "salmo_cita": "Sal 1",
        "salmo_texto": " dichoso el hombre...",
    }
    monkeypatch.setattr(
        wf_module,
        "KoinoniaScraper",
        lambda: MagicMock(obtener_lecturas=lambda dt: lecturas),
    )
    monkeypatch.setattr(wf_module, "obtener_lecturas_ciudadredonda", lambda f: None)

    workflow = {"fecha_domingo": "2026-01-01", "steps_data": {}}
    result = wf.handle_fetch_lectures(workflow, {})
    assert result["success"] is True
    assert result["next_step"] == "verify_lectures"
    assert result["steps_data"]["lecturas_fuente"] == "koinonia"


def test_handle_fetch_lecturas_fallback_ciudadredonda(wf_module, monkeypatch) -> None:
    wf = wf_module
    lecturas = {"fecha": "2026-01-01", "domingo": "", "temporada": "", "color_liturgico": "verde"}
    monkeypatch.setattr(
        wf_module,
        "KoinoniaScraper",
        lambda: MagicMock(obtener_lecturas=lambda dt: None),
    )
    monkeypatch.setattr(
        wf_module,
        "obtener_lecturas_ciudadredonda",
        lambda f: lecturas,
    )
    workflow = {"fecha_domingo": "2026-01-01", "steps_data": {}}
    result = wf.handle_fetch_lectures(workflow, {})
    assert result["success"] is True
    assert result["steps_data"]["lecturas_fuente"] == "ciudad_redonda"


def test_handle_verify_lectures(wf_module) -> None:
    wf = wf_module
    workflow = {
        "fecha_domingo": "2026-01-01",
        "steps_data": {
            "lecturas": {
                "fecha": "2026-01-01",
                "domingo": "Domingo 1",
                "temporada": "ordinario",
                "ciclo": "A",
                "color_liturgico": "verde",
                "primera_lectura_cita": "Gn 1,1",
                "primera_lectura_texto": "texto",
                "salmo_cita": "Sal 1",
                "salmo_texto": "texto",
                "evangelio_cita": "Mt 1,1",
                "evangelio_texto": "texto",
            }
        },
    }
    result = wf.handle_verify_lectures(workflow, {"lecturas": {"ciclo": "B"}})
    assert result["success"] is True
    assert result["next_step"] == "propose_songs"
    assert result["steps_data"]["lecturas"]["ciclo"] == "B"


def test_proponer_canciones_para_dia(wf_module, monkeypatch) -> None:
    wf = wf_module
    conn = db_manager.create_connection(wf.PROJECT_DIR / "data" / "db.sqlite3")
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO lecturas (fecha, domingo, temporada, color_liturgico) VALUES (?, ?, ?, ?)",
            ("2026-01-02", "Domingo 2", "ordinario", "verde"),
        )
        cur.execute(
            "INSERT INTO canciones (titulo, momento_liturgico) VALUES (?, ?)",
            ("Canción Entrada", "entrada"),
        )
    conn.close()

    fake_match = {"cancion_id": 1, "titulo": "Canción Entrada", "momento_liturgico": "entrada", "score": 0.5}
    monkeypatch.setattr(
        wf.MatchingEngine,
        "encontrar_canciones_para_lectura",
        lambda self, lid, limite=None, score_minimo=None: [fake_match],
    )

    propuestas = wf.proponer_canciones_para_dia("2026-01-02")
    assert "Entrada" in propuestas
    assert propuestas["Entrada"]["cancion_id"] == 1


def test_handle_propose_songs(wf_module, monkeypatch) -> None:
    wf = wf_module
    monkeypatch.setattr(wf, "proponer_canciones_para_dia", lambda f: {"Entrada": {"cancion_id": 1}})
    workflow = {"fecha_domingo": "2026-01-03", "steps_data": {}}
    result = wf.handle_propose_songs(workflow, {})
    assert result["success"] is True
    assert result["next_step"] == "verify_songs"


def test_handle_verify_songs(wf_module) -> None:
    wf = wf_module
    workflow = {
        "fecha_domingo": "2026-01-04",
        "steps_data": {
            "canciones_propuestas": {
                "Entrada": {"cancion_id": 1, "momento": "Entrada"},
            }
        },
    }
    result = wf.handle_verify_songs(workflow, {"canciones": {"Entrada": 2}})
    assert result["success"] is True
    assert result["next_step"] == "generate_assets"
    assert result["steps_data"]["canciones_json"]["entrada"] == 2


def test_handle_generate_assets(wf_module, monkeypatch, tmp_path: Path) -> None:
    wf = wf_module
    conn = db_manager.create_connection(wf.PROJECT_DIR / "data" / "db.sqlite3")
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO lecturas (fecha, domingo, temporada, color_liturgico) VALUES (?, ?, ?, ?)",
            ("2026-01-05", "Domingo 5", "ordinario", "verde"),
        )
    conn.close()

    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "2026-01-05_presentacion.pptx").write_text("pptx")
    (bundle_dir / "2026-01-05_presentacion.pdf").write_text("pdf")

    monkeypatch.setattr(wf, "asegurar_composicion", lambda fecha, cjson: True)

    fake_gen = MagicMock()
    fake_gen.generar_desde_presentacion.return_value = bundle_dir
    monkeypatch.setattr(wf, "GeneradorDesdeComposicion", lambda: fake_gen)
    monkeypatch.setattr(wf, "generar_hoja_musicos", lambda **kwargs: str(tmp_path / "musicos.pdf"))
    monkeypatch.setattr(wf, "_backup_existing_assets", lambda wid, fecha, sd: ([], None))

    workflow = {
        "id": 1,
        "fecha_domingo": "2026-01-05",
        "steps_data": {"canciones_json": {"entrada": 1}},
    }
    result = wf.handle_generate_assets(workflow, {})
    assert result["success"] is True
    assert result["next_step"] == "publish"
    assert result["steps_data"]["assets"]["pptx"] is not None


def test_handle_publish(wf_module, monkeypatch, tmp_path: Path) -> None:
    wf = wf_module
    conn = db_manager.create_connection(wf.PROJECT_DIR / "data" / "db.sqlite3")
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO lecturas (fecha, domingo, temporada, color_liturgico) VALUES (?, ?, ?, ?)",
            ("2026-01-06", "Domingo 6", "ordinario", "verde"),
        )
    conn.close()

    monkeypatch.setattr(wf, "sincronizar_presentacion_slides", lambda f: None)
    import subprocess

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: MagicMock(returncode=0, stderr=""))

    workflow = {
        "id": 1,
        "fecha_domingo": "2026-01-06",
        "steps_data": {
            "canciones_json": {"entrada": 1},
            "assets": {
                "pptx": str(tmp_path / "x.pptx"),
                "pdf_fieles": str(tmp_path / "x.pdf"),
                "pdf_musicos": str(tmp_path / "m.pdf"),
                "bundle_dir": str(tmp_path / "bundle"),
            },
        },
    }
    result = wf.handle_publish(workflow, {})
    assert result["success"] is True
    assert result["next_step"] == "done"


def test_run_step_workflow_not_found(wf_module) -> None:
    wf = wf_module
    with patch.object(wf, "get_workflow_run", return_value=None):
        result = wf.run_step(999, "next")
    assert result["success"] is False
