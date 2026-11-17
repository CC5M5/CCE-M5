"""T5/T6 (S5/S6): posición y tamaño por diapositiva de imagen y cuadro de texto.

Helpers puros (sin I/O): parsean y validan posiciones en permiles (0-1000)
del ancho/alto de la diapositiva y las convierten a pulgadas PPTX y a %
HTML. ``posiciones_por_defecto`` da las posiciones de la vista previa del
editor para que el preview coloque los elementos antes de cualquier
arrastre; cuando la posición guardada es NULL, los generadores mantienen
su layout fijo actual.
"""
from __future__ import annotations

import json

MIN_TAMANO = 80
MAX_PORMIL = 1000
_CLAVES = ("x", "y", "w", "h")


def _entero(valor: object) -> int | None:
    """El valor como int si es int-able, o ``None`` (bools no cuentan)."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        return int(valor) if valor.is_integer() else None
    if isinstance(valor, str):
        try:
            return int(valor.strip())
        except ValueError:
            return None
    return None


def parse_posicion(valor: object) -> dict | None:
    """Parsear una posición ``{"x","y","w","h"}`` en permiles (0-1000).

    Acepta ``None``, cadena JSON o dict. Devuelve el dict validado con
    valores int, o ``None`` si es inválida:

    - las cuatro claves x, y, w, h son obligatorias (las extra se ignoran);
    - cada valor debe ser int-able;
    - w y h se ajustan a [80, 1000]; luego x a [0, 1000-w] e y a [0, 1000-h].
    """
    if valor is None:
        return None
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except ValueError:
            return None
    if not isinstance(valor, dict):
        return None
    if any(clave not in valor for clave in _CLAVES):
        return None
    enteros: dict[str, int] = {}
    for clave in _CLAVES:
        entero = _entero(valor[clave])
        if entero is None:
            return None
        enteros[clave] = entero
    w = max(MIN_TAMANO, min(enteros["w"], MAX_PORMIL))
    h = max(MIN_TAMANO, min(enteros["h"], MAX_PORMIL))
    x = max(0, min(enteros["x"], MAX_PORMIL - w))
    y = max(0, min(enteros["y"], MAX_PORMIL - h))
    return {"x": x, "y": y, "w": w, "h": h}


def pptx_inches(
    pos: dict, slide_w_in: float = 13.333, slide_h_in: float = 10.0
) -> tuple[float, float, float, float]:
    """Permiles (x, y, w, h) -> pulgadas en un slide de las dimensiones dadas."""
    return (
        pos["x"] / MAX_PORMIL * slide_w_in,
        pos["y"] / MAX_PORMIL * slide_h_in,
        pos["w"] / MAX_PORMIL * slide_w_in,
        pos["h"] / MAX_PORMIL * slide_h_in,
    )


def html_percent(pos: dict) -> dict[str, str]:
    """Permiles -> % (left/top/width/height) para la vista previa del editor."""
    return {
        "left": f"{pos['x'] / 10:.2f}%",
        "top": f"{pos['y'] / 10:.2f}%",
        "width": f"{pos['w'] / 10:.2f}%",
        "height": f"{pos['h'] / 10:.2f}%",
    }


def posiciones_por_defecto(slide: dict) -> tuple[dict | None, dict | None]:
    """``(imagen_pos, texto_pos)`` en permiles para la vista previa del editor.

    - portada: imagen ``None`` (mantiene su colocación fija actual) y
      texto ``{"x": 90, "y": 420, "w": 818, "h": 340}``;
    - no portada con imagen: imagen ``None`` (fija) y texto
      ``{"x": 45, "y": 60, "w": 660, "h": 700}``;
    - sin imagen: imagen ``None`` y texto
      ``{"x": 45, "y": 60, "w": 908, "h": 700}``.
    """
    if slide.get("tipo") == "portada":
        return None, {"x": 90, "y": 420, "w": 818, "h": 340}
    if slide.get("imagen"):
        return None, {"x": 45, "y": 60, "w": 660, "h": 700}
    return None, {"x": 45, "y": 60, "w": 908, "h": 700}
