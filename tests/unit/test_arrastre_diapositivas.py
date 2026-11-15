"""T5/T6 (S5/S6): helpers de posición y tamaño arrastrables por diapositiva.

Cubre:
- parse_posicion: parsear/validar/ajustar posiciones en permiles (0-1000)
  desde None, cadena JSON o dict;
- pptx_inches: permiles -> pulgadas (slide por defecto 13.333 x 10.0);
- html_percent: permiles -> % para la vista previa del editor;
- posiciones_por_defecto: defectos (imagen, texto) de la vista previa para
  portada, con imagen y sin imagen.
"""
from __future__ import annotations

import pytest

from src.generators.presentacion import posiciones


# ---------------------------------------------------------------------------
# parse_posicion
# ---------------------------------------------------------------------------

def test_parse_posicion_json_valido() -> None:
    pos = posiciones.parse_posicion('{"x": 100, "y": 200, "w": 500, "h": 400}')
    assert pos == {"x": 100, "y": 200, "w": 500, "h": 400}


def test_parse_posicion_dict_aceptado_y_extras_ignorados() -> None:
    pos = posiciones.parse_posicion(
        {"x": 10, "y": 20, "w": 300, "h": 400, "otra": 123}
    )
    assert pos == {"x": 10, "y": 20, "w": 300, "h": 400}


def test_parse_posicion_none_y_cadenas_malformadas() -> None:
    assert posiciones.parse_posicion(None) is None
    assert posiciones.parse_posicion("{no es json") is None
    assert posiciones.parse_posicion("42") is None
    assert posiciones.parse_posicion("null") is None


def test_parse_posicion_faltan_claves() -> None:
    assert posiciones.parse_posicion('{"x": 1, "y": 2, "w": 3}') is None


def test_parse_posicion_valor_no_convertible() -> None:
    # Ni "abc" ni un float no entero son int-ables válidos.
    assert posiciones.parse_posicion({"x": "abc", "y": 2, "w": 3, "h": 4}) is None
    assert posiciones.parse_posicion({"x": 500.5, "y": 2, "w": 3, "h": 4}) is None


def test_parse_posicion_clamp_w_h() -> None:
    # w/h por debajo de 80 -> 80; por encima de 1000 -> 1000.
    pos = posiciones.parse_posicion({"x": 0, "y": 0, "w": 10, "h": 2000})
    assert pos == {"x": 0, "y": 0, "w": 80, "h": 1000}


def test_parse_posicion_clamp_negativos() -> None:
    # x, y negativos -> 0.
    pos = posiciones.parse_posicion({"x": -5, "y": -1, "w": 300, "h": 400})
    assert pos == {"x": 0, "y": 0, "w": 300, "h": 400}


def test_parse_posicion_clamp_overflow_despues_de_w_h() -> None:
    # w=300 -> x en [0, 700]; y=2000 con h=400 -> y en [0, 600].
    pos = posiciones.parse_posicion({"x": 900, "y": 2000, "w": 300, "h": 400})
    assert pos == {"x": 700, "y": 600, "w": 300, "h": 400}


def test_parse_posicion_w_maximo_deja_sin_margen() -> None:
    # w=1000 -> x en [0, 0]; h=1000 -> y en [0, 0].
    pos = posiciones.parse_posicion({"x": 900, "y": 900, "w": 1000, "h": 1000})
    assert pos == {"x": 0, "y": 0, "w": 1000, "h": 1000}


# ---------------------------------------------------------------------------
# pptx_inches
# ---------------------------------------------------------------------------

def test_pptx_inches_defecto() -> None:
    pos = {"x": 500, "y": 250, "w": 300, "h": 400}
    x, y, w, h = posiciones.pptx_inches(pos)
    assert x == pytest.approx(6.6665, abs=0.001)
    assert y == pytest.approx(2.5, abs=0.001)
    assert w == pytest.approx(4.0, abs=0.001)
    assert h == pytest.approx(4.0, abs=0.001)


def test_pptx_inches_dimensiones_custom() -> None:
    pos = {"x": 500, "y": 250, "w": 300, "h": 400}
    x, y, w, h = posiciones.pptx_inches(pos, slide_w_in=16.0, slide_h_in=9.0)
    assert x == pytest.approx(8.0, abs=0.001)
    assert y == pytest.approx(2.25, abs=0.001)
    assert w == pytest.approx(4.8, abs=0.001)
    assert h == pytest.approx(3.6, abs=0.001)


# ---------------------------------------------------------------------------
# html_percent
# ---------------------------------------------------------------------------

def test_html_percent() -> None:
    pos = {"x": 500, "y": 250, "w": 300, "h": 400}
    assert posiciones.html_percent(pos) == {
        "left": "50.00%",
        "top": "25.00%",
        "width": "30.00%",
        "height": "40.00%",
    }


# ---------------------------------------------------------------------------
# posiciones_por_defecto
# ---------------------------------------------------------------------------

def _slide(tipo: str = "evangelio", imagen: str = "") -> dict:
    return {
        "numero": 1, "tipo": tipo, "titulo": "T", "contenido": "C",
        "cita": "", "subtitulo": "", "momento": "", "imagen": imagen,
    }


def test_posiciones_por_defecto_portada() -> None:
    imagen, texto = posiciones.posiciones_por_defecto(_slide("portada", "img.png"))
    assert imagen is None
    assert texto == {"x": 90, "y": 420, "w": 818, "h": 340}


def test_posiciones_por_defecto_con_imagen() -> None:
    imagen, texto = posiciones.posiciones_por_defecto(_slide("evangelio", "img.png"))
    assert imagen is None
    assert texto == {"x": 45, "y": 60, "w": 660, "h": 700}


def test_posiciones_por_defecto_sin_imagen() -> None:
    imagen, texto = posiciones.posiciones_por_defecto(_slide("evangelio", ""))
    assert imagen is None
    assert texto == {"x": 45, "y": 60, "w": 908, "h": 700}
