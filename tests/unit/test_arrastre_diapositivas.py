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

import json
import struct
import zlib

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

from src.constants import COLORES_LITURGICOS
from src.generators.presentacion import html_renderer, posiciones, pptx_renderer
from src.generators.presentacion.slide import Slide

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


# ---------------------------------------------------------------------------
# Propagación a generadores (fase 2b)
# ---------------------------------------------------------------------------

def _datos(slides: list[dict]) -> dict:
    return {
        "meta": {
            "fecha": "2026-01-01",
            "celebracion": "Domingo",
            "color_liturgico": "verde",
            "lema": "Somos uno",
            "lema_imagen": "assets/lema_somos_uno.jpg",
            "generado": "2026-01-01T00:00:00",
        },
        "slides": slides,
    }


def _slide_json(**kwargs) -> dict:
    base = {
        "numero": 1, "tipo": "portada", "titulo": "D", "contenido": "",
        "cita": "", "subtitulo": "", "momento": "", "imagen": "",
        "imagen_pos": None, "texto_pos": None,
    }
    base.update(kwargs)
    return base


def _png(path, w: int, h: int) -> None:
    """Genera un PNG RGB w x h válido sin dependencias externas."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + b"\x00\x80\xff" * w for _ in range(h))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _pptx_render(tmp_path, slides: list[dict]):
    datos = _datos(slides)
    assets = tmp_path / "assets"
    assets.mkdir(exist_ok=True)
    salida = tmp_path / "salida.pptx"
    pptx_renderer._render_pptx(datos, salida, assets)
    return Presentation(str(salida))


def _forma_por_rect(slide, left, top, width, height):
    for forma in slide.shapes:
        if (
            forma.left == left
            and forma.top == top
            and forma.width == width
            and forma.height == height
        ):
            return forma
    return None


def test_slide_dataclass_carga_posiciones() -> None:
    from dataclasses import asdict

    s = Slide(
        numero=1, tipo="portada", titulo="T", contenido="",
        imagen_pos='{"x": 1, "y": 2, "w": 300, "h": 400}', texto_pos=None,
    )
    d = asdict(s)
    assert d["imagen_pos"] == '{"x": 1, "y": 2, "w": 300, "h": 400}'
    assert d["texto_pos"] is None


def test_pptx_texto_pos_portada(tmp_path) -> None:
    """S6: portada con texto_pos {90,420,818,340} -> tarjeta en pptx_inches."""
    pos = {"x": 90, "y": 420, "w": 818, "h": 340}
    prs = _pptx_render(tmp_path, [_slide_json(texto_pos=json.dumps(pos))])
    slide = prs.slides[0]
    ex, ey, ew, eh = posiciones.pptx_inches(pos)
    card = _forma_por_rect(slide, Inches(ex), Inches(ey), Inches(ew), Inches(eh))
    assert card is not None, "la tarjeta no está en la posición guardada"
    caja = next(f for f in slide.shapes if f.shape_type == MSO_SHAPE_TYPE.TEXT_BOX)
    assert caja.left == card.left + Inches(0.3)
    assert caja.top == card.top + Inches(0.22)
    assert caja.width == card.width - Inches(0.6)
    assert caja.height == card.height - Inches(0.44)


def test_pptx_imagen_pos_cabe_en_caja(tmp_path) -> None:
    """S5: imagen con imagen_pos se coloca dentro de la caja, con su
    proporción preservada y centrada."""
    assets = tmp_path / "assets"
    assets.mkdir(exist_ok=True)
    _png(assets / "foo.png", 200, 100)  # proporción 2:1
    pos = {"x": 50, "y": 100, "w": 400, "h": 400}
    datos = _datos([_slide_json(
        numero=2, tipo="evangelio", contenido="x",
        imagen="assets/foo.png", imagen_pos=json.dumps(pos),
    )])
    salida = tmp_path / "salida.pptx"
    pptx_renderer._render_pptx(datos, salida, assets)
    slide = Presentation(str(salida)).slides[0]
    pic = next(f for f in slide.shapes if f.shape_type == MSO_SHAPE_TYPE.PICTURE)
    bx, by, bw, bh = posiciones.pptx_inches(pos)
    tol = 9525  # 0.01 in en EMU
    # Debe caber íntegramente dentro de la caja.
    assert pic.left >= Inches(bx) - tol
    assert pic.top >= Inches(by) - tol
    assert pic.left + pic.width <= Inches(bx) + Inches(bw) + tol
    assert pic.top + pic.height <= Inches(by) + Inches(bh) + tol
    # 2:1 es más ancha que la caja (1.33:1) -> llena el ancho y centra en alto.
    assert pic.width == pytest.approx(Inches(bw), abs=tol)
    assert pic.height == pytest.approx(Inches(bw) / 2, abs=tol)
    assert pic.left == pytest.approx(Inches(bx), abs=tol)
    assert pic.top == pytest.approx(
        Inches(by) + (Inches(bh) - Inches(bw) / 2) / 2, abs=tol
    )


def test_pptx_sin_posiciones_mantiene_layout_fijo(tmp_path) -> None:
    """NULL: se conserva el layout fijo actual por tipo (constantes de hoy)."""
    assets = tmp_path / "assets"
    assets.mkdir(exist_ok=True)
    _png(assets / "foo.png", 200, 100)
    datos = _datos([
        _slide_json(),  # portada sin posiciones
        _slide_json(numero=2, tipo="evangelio", contenido="x", imagen="assets/foo.png"),
    ])
    salida = tmp_path / "salida.pptx"
    pptx_renderer._render_pptx(datos, salida, assets)
    prs = Presentation(str(salida))
    portada = prs.slides[0]
    assert _forma_por_rect(portada, Inches(1.2), Inches(4.2), Inches(10.9), Inches(3.4)) is not None
    cuerpo = prs.slides[1]
    assert _forma_por_rect(cuerpo, Inches(0.6), Inches(0.6), Inches(8.8), Inches(7.0)) is not None
    pic = next(f for f in cuerpo.shapes if f.shape_type == MSO_SHAPE_TYPE.PICTURE)
    assert pic.left == Inches(7.3)
    assert pic.top == Inches(1.1)
    assert pic.height == Inches(2.8)


def test_html_posiciones_percent() -> None:
    """S5/S6: las posiciones se emiten como % (html_percent) en el HTML."""
    datos = _datos([_slide_json(
        numero=2, tipo="evangelio", titulo="E", contenido="x",
        imagen="assets/foo.png",
        imagen_pos=json.dumps({"x": 90, "y": 10, "w": 400, "h": 500}),
        texto_pos=json.dumps({"x": 5, "y": 6, "w": 600, "h": 700}),
    )])
    html = html_renderer._render_html(datos, COLORES_LITURGICOS["verde"])
    assert (
        '<img class="ilustracion ilustracion-pos" src="assets/foo.png" '
        'alt="ilustración" style="left:9.00%;top:1.00%;width:40.00%;height:50.00%">'
    ) in html
    assert (
        '<div class="tarjeta tarjeta-pos" '
        'style="left:0.50%;top:0.60%;width:60.00%;height:70.00%">'
    ) in html


def test_html_sin_posiciones_css_actual() -> None:
    """NULL: el HTML mantiene el CSS actual (sin clases ni estilos de posición)."""
    datos = _datos([_slide_json(
        numero=2, tipo="evangelio", titulo="E", contenido="x", imagen="assets/foo.png",
    )])
    html = html_renderer._render_html(datos, COLORES_LITURGICOS["verde"])
    assert 'class="ilustracion ilustracion-pos"' not in html
    assert 'class="tarjeta tarjeta-pos"' not in html
    assert '<img class="ilustracion" src="assets/foo.png" alt="ilustración">' in html
    assert '<div class="tarjeta">' in html
