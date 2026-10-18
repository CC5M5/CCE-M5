"""Tests para src/generators/presentacion/generador.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.generators.presentacion.generador import GeneradorPresentacionHTML


@pytest.fixture
def generador(tmp_path: Path) -> GeneradorPresentacionHTML:
    return GeneradorPresentacionHTML(db_path=str(tmp_path / "db.sqlite3"), output_dir=str(tmp_path / "out"))


def test_init_crea_output_dir(generador, tmp_path: Path) -> None:
    assert generador.output_dir.exists()
    assert generador.output_dir == tmp_path / "out"


def test_metodos_wrapper_devuelven_valores(generador) -> None:
    assert generador._formatear_cita("Mateo", "5,1-10") == "Mateo 5,1-10"
    assert generador._formatear_cita("Mateo", "Mateo 5,1-10") == "Mateo 5,1-10"
    assert generador._escape_html("<a>") == "&lt;a&gt;"
    assert generador._apply_bold_html("**x**") == "<strong>x</strong>"
    assert generador._es_linea_solo_acordes("Sol Lam Re7") is True
    assert generador._es_linea_solo_acordes("letra normal") is False
    assert generador._unir_lineas("a-", "b") == "ab"
    assert generador._unir_lineas("a", "b") == "a b"
    assert generador._hex_to_rgb("#FF5733") == (255, 87, 51)
    assert generador._hex_to_rgb("FF5733") == (255, 87, 51)


def test_compactaciones(generador) -> None:
    assert generador._compactar_para_slide("a\nb\n\nc") == "a\nb\n\nc"
    assert generador._paginar_texto("x", max_chars=100) == ["x"]


def test_generar_mockeado(generador) -> None:
    with patch("src.generators.presentacion.generador._generar_presentacion") as mock_gen:
        mock_gen.return_value = Path("/tmp/result.html")
        resultado = generador.generar(
            fecha="2026-01-01",
            lectura_id=1,
            canciones_ids={"entrada": 2},
        )
        assert resultado == Path("/tmp/result.html")
        mock_gen.assert_called_once()
