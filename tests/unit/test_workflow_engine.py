"""Tests mínimos para funciones puras del workflow engine."""

import sqlite3
from unittest.mock import patch

from src.web_admin.workflow_engine import (
    handle_fetch_lectures,
    handle_init,
    handle_verify_lectures,
)


def test_handle_init():
    workflow = {"fecha_domingo": "2099-01-01", "steps_data": {"foo": "bar"}}
    result = handle_init(workflow, {})
    assert result["success"] is True
    assert result["next_step"] == "fetch_lectures"
    assert result["steps_data"] == {"foo": "bar"}
    assert any("Workflow iniciado" in log["message"] for log in result["logs"])


def test_handle_fetch_lectures_success():
    workflow = {"fecha_domingo": "2099-01-01", "steps_data": {}}
    lecturas = {
        "fecha": "2099-01-01",
        "domingo": "Domingo de prueba",
        "fuente_scraping": "koinonia",
    }
    with patch("src.web_admin.workflow_engine.KoinoniaScraper") as mock_scraper_cls:
        mock_scraper = mock_scraper_cls.return_value
        mock_scraper.obtener_lecturas.return_value = lecturas
        result = handle_fetch_lectures(workflow, {})

    assert result["success"] is True
    assert result["next_step"] == "verify_lectures"
    assert result["steps_data"]["lecturas"]["domingo"] == "Domingo de prueba"
    assert result["steps_data"]["lecturas_fuente"] == "koinonia"
    assert result["warning"] is None


def test_handle_fetch_lectures_fallback():
    workflow = {"fecha_domingo": "2099-01-01", "steps_data": {}}
    lecturas = {
        "fecha": "2099-01-01",
        "domingo": "Fallback",
        "fuente_scraping": "ciudad_redonda",
    }
    with patch("src.web_admin.workflow_engine.KoinoniaScraper") as mock_scraper_cls, patch(
        "src.web_admin.workflow_engine.obtener_lecturas_ciudadredonda",
        return_value=lecturas,
    ):
        mock_scraper = mock_scraper_cls.return_value
        mock_scraper.obtener_lecturas.side_effect = RuntimeError("Koinonia no responde")
        result = handle_fetch_lectures(workflow, {})

    assert result["success"] is True
    assert result["steps_data"]["lecturas"]["domingo"] == "Fallback"
    assert result["steps_data"]["lecturas_fuente"] == "ciudad_redonda"


def test_handle_verify_lectures():
    workflow = {
        "fecha_domingo": "2099-01-01",
        "steps_data": {"lecturas": {"domingo": "Antiguo"}},
    }
    with patch("src.web_admin.workflow_engine._save_lecturas_to_db") as mock_save:
        result = handle_verify_lectures(
            workflow,
            {"lecturas": {"domingo": "Nuevo", "color_liturgico": "verde"}},
        )

    assert result["success"] is True
    assert result["next_step"] == "propose_songs"
    assert result["steps_data"]["lecturas"]["domingo"] == "Nuevo"
    assert result["steps_data"]["lecturas_verificadas"] is True
    mock_save.assert_called_once()


def test_handle_verify_lectures_save_error():
    workflow = {
        "fecha_domingo": "2099-01-01",
        "steps_data": {"lecturas": {"domingo": "Antiguo"}},
    }
    with patch(
        "src.web_admin.workflow_engine._save_lecturas_to_db",
        side_effect=sqlite3.Error("BD bloqueada"),
    ):
        result = handle_verify_lectures(workflow, {})

    assert result["success"] is False
    assert "No se pudieron guardar" in result["error"]
