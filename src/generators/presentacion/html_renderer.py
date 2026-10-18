"""Renderizado de presentaciones a HTML con Reveal.js."""

from typing import Any

from src.generators.presentacion.plantillas import base
from src.generators.presentacion.text_utils import _apply_bold_html, _escape_html


def _slide_to_html(slide: dict[str, Any], color_info: dict[str, str]) -> str:
    tipo = slide["tipo"]
    titulo = _escape_html(slide["titulo"])
    contenido = _apply_bold_html(_escape_html(slide["contenido"]))
    cita = _escape_html(slide["cita"])
    subtitulo = _escape_html(slide["subtitulo"])
    momento = _escape_html(slide["momento"])
    imagen = slide.get("imagen", "")

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
        html += f'    <img class="ilustracion" src="{imagen}" alt="ilustración">\n'
    html += f'    <div class="tarjeta">\n{inner}    </div>\n'
    html += f'    <img class="logo-lema" src="{lema_img}" alt="Somos uno">\n'
    html += '  </div>\n'
    html += '</section>\n'
    return html


def _render_html(data: dict[str, Any], color_info: dict[str, str]) -> str:
    slides_html = "\n".join(_slide_to_html(s, color_info) for s in data["slides"])
    return base.TEMPLATE.format(
        titulo=f'{data["meta"]["celebracion"]} - {data["meta"]["fecha"]}',
        from_color=color_info["from"],
        to_color=color_info["to"],
        acento=color_info["acento"],
        slides_html=slides_html,
    )
