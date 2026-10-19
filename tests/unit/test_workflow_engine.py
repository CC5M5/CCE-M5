"""Tests para src/web_admin/workflow_engine.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.web_admin import database as db
from src.web_admin import workflow_engine as we


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "admin.sqlite3")
    monkeypatch.setattr(we, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(we, "BACKUPS_DIR", tmp_path / "backups")
    p = tmp_path / "admin.sqlite3"
    db.init_admin_schema(p)
    return p


def test_run_step_workflow_not_found(db_path: Path) -> None:
    result = we.run_step(9999, "next")
    assert result["success"] is False
    assert "no encontrado" in result["error"].lower()


def test_run_step_invalid_action(db_path: Path) -> None:
    wid = db.create_workflow_run("2026-01-02", "admin", {})
    result = we.run_step(wid, "invalid")
    assert result["success"] is False
    assert "no válida" in result["error"]


def test_run_step_missing_handler(db_path: Path) -> None:
    wid = db.create_workflow_run("2026-01-03", "admin", {})
    db.update_workflow_step(wid, "unknown", "unknown")
    result = we.run_step(wid, "next")
    assert result["success"] is False
    assert "No hay handler" in result["error"]


def test_run_step_rollback_first(db_path: Path) -> None:
    wid = db.create_workflow_run("2026-01-04", "admin", {})
    result = we.run_step(wid, "rollback")
    assert result["success"] is False
    assert "retroceder" in result["error"].lower()


def test_run_step_rollback(db_path: Path) -> None:
    wid = db.create_workflow_run("2026-01-05", "admin", {})
    db.update_workflow_step(wid, "fetch_lectures", "fetch_lectures")
    result = we.run_step(wid, "rollback")
    assert result["success"] is True
    assert result["workflow"]["current_step"] == "init"


def test_handle_init() -> None:
    wf = {"steps_data": {}}
    result = we.handle_init(wf, {})
    assert result["success"] is True
    assert result["next_step"] == "fetch_lectures"


def test_handle_fetch_lectures_manual(db_path: Path) -> None:
    wid = db.create_workflow_run("2026-01-06", "admin", {})
    wf = db.get_workflow_run(wid)
    with patch.object(we, "KoinoniaScraper") as mock_scraper, patch.object(
        we, "obtener_lecturas_ciudadredonda", return_value=None
    ):
        mock_scraper.return_value.obtener_lecturas.return_value = None
        result = we.handle_fetch_lectures(wf, {})
    assert result["success"] is True
    assert result["next_step"] == "verify_lectures"
    assert "warning" in result


def test_handle_verify_lectures_empty(db_path: Path) -> None:
    wid = db.create_workflow_run("2026-01-07", "admin", {})
    db.update_workflow_step(wid, "fetch_lectures", "fetch_lectures")
    wf = db.get_workflow_run(wid)
    result = we.handle_verify_lectures(wf, {})
    assert result["success"] is True
    assert result["next_step"] == "propose_songs"


def test_handle_verify_lectures_manual(db_path: Path) -> None:
    wid = db.create_workflow_run("2026-01-08", "admin", {"lecturas": {}})
    db.update_workflow_step(wid, "fetch_lectures", "fetch_lectures")
    wf = db.get_workflow_run(wid)
    result = we.handle_verify_lectures(
        wf,
        {
            "domingo": "Domingo 1",
            "temporada": "ordinario",
            "ciclo": "A",
            "color_liturgico": "verde",
            "primera_lectura_texto": "texto",
        },
    )
    assert result["success"] is True
    assert "lecturas" in result["steps_data"]


def test_backup_existing_assets_none(db_path: Path) -> None:
    paths, backup_dir = we._backup_existing_assets(1, "2026-01-01", {})
    assert paths == []
    assert backup_dir is None
