"""Renderizado de presentaciones a HTML con Reveal.js."""

from typing import Any

from src.constants import SLIDE_WIDTH_INCHES, TAMANO_LETRA_DEFECTO
from src.generators.presentacion.plantillas import base
from src.generators.presentacion.posiciones import html_percent, parse_posicion
from src.generators.presentacion.text_utils import _apply_bold_html, _escape_html


def _slide_to_html(slide: dict[str, Any], color_info: dict[str, str]) -> str:
    tipo = slide["tipo"]
    titulo = _escape_html(slide["titulo"])
    contenido = _apply_bold_html(_escape_html(slide["contenido"]))
    cita = _escape_html(slide["cita"])
    subtitulo = _escape_html(slide["subtitulo"])
    momento = _escape_html(slide["momento"])
    imagen = slide.get("imagen", "")
    # S5/S6: posiciones guardadas por diapositiva (per-mille); NULL = CSS actual.
    imagen_pos = parse_posicion(slide.get("imagen_pos"))
    texto_pos = parse_posicion(slide.get("texto_pos"))

    lema_img = "assets/lema_somos_uno.jpg"
    inner = ""

    if momento:
        inner += f'  <h3>{momento}</h3>\n'
    if titulo or tipo != 'paso':
        inner += f'  <h1>{titulo}</h1>\n'
    if subtitulo:
        inner += f'  <h2>{subtitulo}</h2>\n'
    if cita:
        inner += f'  <div class="cita">{cita}</div>\n'
    if contenido:
        inner += f'  <div class="contenido">{contenido}</div>\n'

    clase = f"{tipo} cancion" if tipo in (
        "entrada", "gloria", "aleluya", "ofertorio", "santo",
        "padre_nuestro", "paz", "comunion", "maria", "despedida",
    ) else tipo

    html = f'<section class="{clase}" data-transition="fade">\n'
    html += '  <div class="slide-wrapper">\n'
    if imagen:
        if imagen_pos is not None:
            p = html_percent(imagen_pos)
            html += (
                f'    <img class="ilustracion ilustracion-pos" src="{imagen}" alt="ilustración" '
                f'style="left:{p["left"]};top:{p["top"]};width:{p["width"]};height:{p["height"]}">\n'
            )
        else:
            html += f'    <img class="ilustracion" src="{imagen}" alt="ilustración">\n'
    if texto_pos is not None:
        p = html_percent(texto_pos)
        html += (
            f'    <div class="tarjeta tarjeta-pos" '
            f'style="left:{p["left"]};top:{p["top"]};width:{p["width"]};height:{p["height"]}">\n'
            f'{inner}    </div>\n'
        )
    else:
        html += f'    <div class="tarjeta">\n{inner}    </div>\n'
    html += f'    <img class="logo-lema" src="{lema_img}" alt="Somos uno">\n'
    html += '  </div>\n'
    html += '</section>\n'
    return html


# Lienzo de Reveal (ver Reveal.initialize) y escala pt -> px: px = pt * 1280 / (13.333 in * 72 pt/in).
REVEAL_W_PX = 1280
REVEAL_PT_A_PX = REVEAL_W_PX / (SLIDE_WIDTH_INCHES * 72)


def _px(pt: float) -> str:
    return f"{pt * REVEAL_PT_A_PX:.4f}"


def _render_html(data: dict[str, Any], color_info: dict[str, str]) -> str:
    slides_html = "\n".join(_slide_to_html(s, color_info) for s in data["slides"])
    # S2: tamaños globales por parte (pt); sin meta (o incompleta) se usan los defectos.
    tamanos = dict(
        TAMANO_LETRA_DEFECTO, **(data.get("meta", {}).get("tamanos_fuente") or {})
    )
    return base.TEMPLATE.format(
        titulo=f'{data["meta"]["celebracion"]} - {data["meta"]["fecha"]}',
        from_color=color_info["from"],
        to_color=color_info["to"],
        acento=color_info["acento"],
        slides_html=slides_html,
        fuente_titulo=_px(tamanos["titulo"]),
        fuente_subtitulo=_px(tamanos["subtitulo"]),
        fuente_cita=_px(tamanos["cita"]),
        fuente_cuerpo=_px(tamanos["cuerpo"]),
    )
