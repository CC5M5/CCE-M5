"""Renderizado de presentaciones a PPTX."""

import re
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Inches, Pt

from src.constants import SLIDE_HEIGHT_INCHES, SLIDE_WIDTH_INCHES


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _add_formatted_run(
    p,
    para_text: str,
    is_cancion: bool,
    is_portada: bool,
    para_index: int,
    slide_data: dict[str, Any],
    primary_rgb: tuple[int, int, int],
):
    """Añade el texto del párrafo respetando marcadores **negrita**."""
    primary = RGBColor(*primary_rgb)
    accent_gold = RGBColor(212, 167, 106)
    text_dark = RGBColor(55, 53, 47)
    is_momento = para_index == 0 and slide_data.get("momento")
    is_titulo = (para_index == 0 and not slide_data.get("momento")) or (
        para_index == 1 and slide_data.get("momento")
    )
    is_cita = slide_data.get("cita") and para_text.startswith(slide_data["cita"])

    base_size = Pt(19 if is_cancion else 20)
    if is_momento:
        base_size, base_bold, base_color = Pt(15), True, primary
    elif is_titulo:
        base_size, base_bold, base_color = Pt(34 if is_portada else 26), True, primary
    elif is_cita:
        base_size, base_bold, base_color = Pt(15), True, accent_gold
    else:
        base_size, base_bold, base_color = Pt(19 if is_cancion else 20), False, text_dark
        if is_cancion:
            p.line_spacing = 1.05
        else:
            p.line_spacing = 1.15

    segments = re.split(r"(\*\*.*?\*\*)", para_text)
    for seg in segments:
        if not seg:
            continue
        run = p.add_run()
        if seg.startswith("**") and seg.endswith("**") and len(seg) >= 4:
            run.text = seg[2:-2]
            run.font.bold = True
        else:
            run.text = seg
            run.font.bold = base_bold
        run.font.size = base_size
        run.font.color.rgb = base_color


def _render_pptx(data: dict[str, Any], pptx_path: Path, assets_dir: Path):
    """Genera PPTX 4:3 desde el JSON intermediario común."""
    from src.constants import COLORES_LITURGICOS

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_WIDTH_INCHES)
    prs.slide_height = Inches(SLIDE_HEIGHT_INCHES)
    blank_layout = prs.slide_layouts[6]

    color = COLORES_LITURGICOS.get(
        data["meta"]["color_liturgico"].lower(), COLORES_LITURGICOS["verde"]
    )
    lema_img_path = assets_dir / "lema_somos_uno.jpg"

    primary = (124, 58, 237)
    accent_gold = (161, 98, 7)
    bg_light = (250, 245, 255)
    text_dark = (44, 62, 80)
    text_muted = (85, 85, 85)

    for slide_data in data["slides"]:
        slide = prs.slides.add_slide(blank_layout)
        is_portada = slide_data["tipo"] == "portada"
        has_image = bool(slide_data.get("imagen"))
        is_cancion = slide_data["tipo"] in (
            "entrada", "gloria", "aleluya", "ofertorio", "santo",
            "padre_nuestro", "paz", "comunion", "maria", "despedida",
        )

        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(*primary) if is_portada else RGBColor(*bg_light)

        bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0),
            Inches(0),
            Inches(SLIDE_WIDTH_INCHES),
            Inches(0.12),
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = RGBColor(*primary)
        bar.line.fill.background()

        if lema_img_path.exists():
            try:
                slide.shapes.add_picture(
                    str(lema_img_path),
                    Inches(0.4),
                    Inches(SLIDE_HEIGHT_INCHES - 0.95),
                    height=Inches(0.75),
                )
            except (ValueError, TypeError, OSError):
                pass

        if has_image:
            base_name = Path(slide_data["imagen"]).stem
            for ext in (".png", ".jpg", ".jpeg", ".svg"):
                img_path = assets_dir / f"{base_name}{ext}"
                if img_path.exists():
                    if is_portada:
                        slide.shapes.add_picture(str(img_path), Inches(3.5), Inches(0.5), height=Inches(2.6))
                    else:
                        slide.shapes.add_picture(str(img_path), Inches(7.3), Inches(1.1), height=Inches(2.8))
                    break

        if is_portada:
            card_left = Inches(1.2)
            card_top = Inches(4.2)
            card_width = Inches(10.9)
            card_height = Inches(3.4)
        elif has_image:
            card_left = Inches(0.6)
            card_top = Inches(0.6)
            card_width = Inches(8.8)
            card_height = Inches(7.0)
        else:
            card_left = Inches(0.6)
            card_top = Inches(0.6)
            card_width = Inches(12.1)
            card_height = Inches(7.0)

        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            card_left, card_top, card_width, card_height,
        )
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        card.line.color.rgb = RGBColor(221, 214, 254)
        card.line.width = Pt(1)
        if hasattr(card, "adjustments"):
            try:
                card.adjustments[0] = 0.08
            except (ValueError, TypeError, IndexError, AttributeError):
                pass

        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            card_left,
            card_top + card_height - Inches(0.10),
            card_width,
            Inches(0.10),
        )
        line.fill.solid()
        line.fill.fore_color.rgb = RGBColor(*primary)
        line.line.fill.background()

        text_left = card_left + Inches(0.3)
        text_top = card_top + Inches(0.22)
        text_width = card_width - Inches(0.6)
        text_height = card_height - Inches(0.44)

        full_text = ""
        if slide_data.get("momento"):
            full_text += f"{slide_data['momento'].upper()}\n"
        full_text += f"{slide_data['titulo']}\n"
        if slide_data.get("subtitulo"):
            full_text += f"{slide_data['subtitulo']}\n"
        if slide_data.get("cita"):
            full_text += f"\n{slide_data['cita']}\n"
        if slide_data.get("contenido"):
            full_text += f"\n{slide_data['contenido']}"

        box = slide.shapes.add_textbox(text_left, text_top, text_width, text_height)
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = 0
        tf.margin_right = 0
        tf.margin_top = 0
        tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.TOP
        tf.auto_size = None

        paragraphs = full_text.split("\n")
        for i, para_text in enumerate(paragraphs):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            if not para_text.strip():
                p.space_after = Pt(0)
                p.space_before = Pt(0)
                continue
            _add_formatted_run(p, para_text, is_cancion, is_portada, i, slide_data, primary)

    prs.save(str(pptx_path))
