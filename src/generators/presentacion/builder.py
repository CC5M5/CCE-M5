"""Construcción del listado de diapositivas desde lecturas y canciones."""

import json
import shutil
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.constants import (
    COLORES_LITURGICOS,
    DB_PATH,
    ILUSTRACIONES_DIR,
    ILUSTRACIONES_PREFERIDAS,
    LEMA_DIR,
    TEXTOS_LITURGICOS,
)
from src.constants import (
    OUTPUT_DIR_HTML as OUTPUT_DIR,
)
from src.generators.presentacion.html_renderer import _render_html
from src.generators.presentacion.pdf_renderer import _render_pdf
from src.generators.presentacion.pptx_renderer import _render_pptx
from src.generators.presentacion.slide import Slide
from src.generators.presentacion.text_utils import (
    _compactar_salmo_o_lectura,
    _formatear_cita,
    _paginar_texto,
    _texto_cancion,
)


def _get_connection() -> sqlite3.Connection:
    """Conexión SQLite con filas accesibles por clave."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _cargar_catalogo() -> dict[str, list[str]]:
    catalogo_path = ILUSTRACIONES_DIR / "catalogo.json"
    if not catalogo_path.exists():
        return {}
    with open(catalogo_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("imagenes", {})


def _ilustracion_para(tipo: str, catalogo: dict[str, list[str]]) -> str:
    """Devuelve la primera ilustración disponible del catálogo para el tipo de slide."""
    opciones = catalogo.get(tipo, [])
    for opcion in opciones:
        path = ILUSTRACIONES_DIR / opcion
        if path.exists():
            return f"assets/{Path(opcion).name}"
    opciones_svg = ILUSTRACIONES_PREFERIDAS.get(tipo, ["comunidad_oracion.png"])
    for opcion in opciones_svg:
        path = ILUSTRACIONES_DIR / opcion
        if path.exists():
            return f"assets/{opcion}"
    return ""


def _celebracion_from_fecha(fecha: str) -> str:
    return "Domingo"


def _formatear_fecha(fecha: str) -> str:
    try:
        dt = datetime.strptime(fecha, "%Y-%m-%d")
        meses = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        return f"{dt.day} de {meses[dt.month - 1]} de {dt.year}"
    except (ValueError, TypeError, IndexError):
        return fecha


def _extraer_frase_evangelio(lectura: sqlite3.Row) -> str:
    """Extrae una frase corta representativa del Evangelio."""
    import re

    texto = lectura["evangelio_texto"] if lectura and "evangelio_texto" in lectura else ""
    if not texto:
        return ""
    comillas = re.findall(r"«([^»]{20,180})»", texto)
    if comillas:
        return comillas[-1].strip()
    for oracion in re.split(r"(?<=[.!?])\s+", texto):
        oracion = oracion.strip()
        if 20 <= len(oracion) <= 180:
            return oracion + "."
    return texto[:180].strip() + "..."


def _get_lectura(lectura_id: int) -> sqlite3.Row | None:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lecturas WHERE id=?", (lectura_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def _get_canciones(canciones_ids: dict[str, int]) -> dict[str, dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    canciones: dict[str, dict[str, Any]] = {}
    for key, cid in canciones_ids.items():
        cursor.execute(
            "SELECT id, titulo, letra_sin_acordes, letra_con_acordes, acordes_json, momento_liturgico "
            "FROM canciones WHERE id=?",
            (cid,),
        )
        row = cursor.fetchone()
        if row:
            canciones[key] = dict(row)
    conn.close()
    return canciones


def _add_cancion_slide(
    add,
    canciones: dict[str, dict[str, Any]],
    key: str,
    tipo: str,
    momento: str,
    titulo_fallback: str,
):
    """Añade slide de canción; si no existe, pone título + 'Rellenar a mano'."""
    c = canciones.get(key)
    if c and c.get("titulo"):
        texto = _texto_cancion(c)
        if not texto:
            texto = "Rellenar a mano"
        add(tipo, c.get("titulo", "").upper(), texto, momento=momento)
    else:
        add(tipo, titulo_fallback.upper(), "Rellenar a mano", momento=momento)


def _construir_slides(
    fecha: str,
    lectura: sqlite3.Row,
    celebracion: str,
    canciones: dict[str, dict[str, Any]],
    color_info: dict[str, str],
    incluir_bendicion_agua: bool = False,
    frase_evangelio: str = "",
    catalogo: dict[str, list[str]] | None = None,
) -> list[Slide]:
    slides: list[Slide] = []
    n = 0

    def add(
        tipo: str,
        titulo: str,
        contenido: str = "",
        cita: str = "",
        subtitulo: str = "",
        momento: str = "",
    ):
        nonlocal n
        n += 1
        slides.append(
            Slide(
                numero=n,
                tipo=tipo,
                titulo=titulo,
                contenido=contenido,
                cita=cita,
                subtitulo=subtitulo,
                momento=momento,
                imagen=_ilustracion_para(tipo, catalogo or {}),
            )
        )

    add(
        "portada",
        celebracion.upper(),
        subtitulo=f"{_formatear_fecha(fecha)}",
    )

    _add_cancion_slide(add, canciones, "entrada", "entrada", "Canción de Entrada", "Entrada")

    if canciones.get("perdon"):
        _add_cancion_slide(add, canciones, "perdon", "perdon", "Acto Penitencial", "Perdón")
    else:
        add("perdon", "ACTO PENITENCIAL", TEXTOS_LITURGICOS["acto_penitencial"])

    if incluir_bendicion_agua:
        add(
            "perdon",
            "BENDICIÓN DEL AGUA",
            TEXTOS_LITURGICOS["bendicion_agua"],
            subtitulo="Señor, Dios todopoderoso, que por medio del agua...",
        )

    if canciones.get("gloria"):
        _add_cancion_slide(add, canciones, "gloria", "gloria", "Gloria", "GLORIA")

    if lectura["primera_lectura_texto"]:
        fragmentos = _paginar_texto(lectura["primera_lectura_texto"])
        for i, frag in enumerate(fragmentos):
            sufijo = f" ({i + 1}/{len(fragmentos)})" if len(fragmentos) > 1 else ""
            add(
                "primera_lectura",
                f"PRIMERA LECTURA{sufijo}",
                frag,
                cita=_formatear_cita(
                    lectura["primera_lectura_libro"], lectura["primera_lectura_cita"]
                ),
            )

    if lectura["salmo_texto"]:
        salmo_texto = _compactar_salmo_o_lectura(lectura["salmo_texto"])
        if lectura["salmo_antifona"]:
            salmo_texto = f"Antífona: {lectura['salmo_antifona']}\n\n{salmo_texto}"
        salmo_cancion = canciones.get("salmo")
        if salmo_cancion and salmo_cancion.get("titulo"):
            cancion_texto = _texto_cancion(salmo_cancion)
            salmo_texto = (
                f"{salmo_texto}\n\n---\n\n{salmo_cancion['titulo'].upper()}\n{cancion_texto}"
            )
        fragmentos = _paginar_texto(salmo_texto)
        for i, frag in enumerate(fragmentos):
            sufijo = f" ({i + 1}/{len(fragmentos)})" if len(fragmentos) > 1 else ""
            add(
                "salmo",
                f"SALMO RESPONSORIAL{sufijo}",
                frag,
                cita=_formatear_cita(lectura["salmo_libro"], lectura["salmo_cita"]),
            )

    if lectura["segunda_lectura_texto"]:
        fragmentos = _paginar_texto(lectura["segunda_lectura_texto"])
        for i, frag in enumerate(fragmentos):
            sufijo = f" ({i + 1}/{len(fragmentos)})" if len(fragmentos) > 1 else ""
            add(
                "segunda_lectura",
                f"SEGUNDA LECTURA{sufijo}",
                frag,
                cita=_formatear_cita(
                    lectura["segunda_lectura_libro"], lectura["segunda_lectura_cita"]
                ),
            )

    _add_cancion_slide(add, canciones, "aleluya", "aleluya", "Aleluya", "ALELUYA")

    if lectura["evangelio_texto"]:
        fragmentos = _paginar_texto(lectura["evangelio_texto"])
        for i, frag in enumerate(fragmentos):
            sufijo = f" ({i + 1}/{len(fragmentos)})" if len(fragmentos) > 1 else ""
            add(
                "evangelio",
                f"EVANGELIO{sufijo}",
                frag,
                cita=_formatear_cita(lectura["evangelio_libro"], lectura["evangelio_cita"]),
            )

    add("credo", "CREDO", TEXTOS_LITURGICOS["credo"])

    _add_cancion_slide(add, canciones, "ofertorio", "ofertorio", "Ofertorio", "OFERTORIO")
    _add_cancion_slide(add, canciones, "santo", "santo", "Santo", "SANTO")
    _add_cancion_slide(
        add, canciones, "padre_nuestro", "padre_nuestro", "Padre Nuestro", "PADRE NUESTRO"
    )
    _add_cancion_slide(add, canciones, "paz", "paz", "Rito de la Paz", "PAZ")
    _add_cancion_slide(add, canciones, "comunion", "comunion", "Comunión", "COMUNIÓN")
    _add_cancion_slide(add, canciones, "maria", "maria", "Canto a María", "CANTO A MARÍA")
    _add_cancion_slide(add, canciones, "despedida", "despedida", "Despedida", "DESPEDIDA")

    add(
        "portada",
        "¡ID EN PAZ!",
        f"La paz del Señor esté siempre con vosotros.\n\n«{frase_evangelio}»",
        subtitulo="Somos uno · " + _formatear_fecha(fecha),
    )

    for i, s in enumerate(slides, 1):
        s.numero = i
    return slides


def generar(
    db_path: str | None,
    output_dir: str | None,
    fecha: str,
    lectura_id: int,
    canciones_ids: dict[str, int],
    incluir_bendicion_agua: bool = False,
    frase_evangelio: str = "",
) -> Path:
    """Genera JSON, HTML, PPTX y PDF para la fecha indicada."""
    lectura = _get_lectura(lectura_id)
    if not lectura:
        raise ValueError(f"No existe lectura con id={lectura_id}")

    celebracion = lectura["celebracion"] or _celebracion_from_fecha(fecha)
    color = (lectura["color_liturgico"] or "verde").lower()
    color_info = COLORES_LITURGICOS.get(color, COLORES_LITURGICOS["verde"])

    canciones = _get_canciones(canciones_ids)
    if not frase_evangelio:
        frase_evangelio = _extraer_frase_evangelio(lectura)

    catalogo = _cargar_catalogo()
    slides = _construir_slides(
        fecha,
        lectura,
        celebracion,
        canciones,
        color_info,
        incluir_bendicion_agua=incluir_bendicion_agua,
        frase_evangelio=frase_evangelio,
        catalogo=catalogo,
    )

    Path(db_path) if db_path else DB_PATH
    resolved_output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    lema_path = LEMA_DIR / "somos_uno.jpg"
    base_name = f"{fecha}_presentacion"
    bundle_dir = resolved_output_dir / base_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    if lema_path.exists():
        shutil.copy(lema_path, assets_dir / "lema_somos_uno.jpg")
    for slide in slides:
        if not slide.imagen:
            continue
        img_name = Path(slide.imagen).name
        src_candidates = list(ILUSTRACIONES_DIR.rglob(img_name))
        if not src_candidates:
            stem = Path(img_name).stem
            for ext in (".jpg", ".jpeg", ".png", ".svg", ".webp"):
                src_candidates.extend(ILUSTRACIONES_DIR.rglob(f"{stem}{ext}"))
        for src in src_candidates:
            if src.exists():
                shutil.copy(src, assets_dir / src.name)
                break

    data = {
        "meta": {
            "fecha": fecha,
            "celebracion": celebracion,
            "color_liturgico": color,
            "lema": "Somos uno",
            "lema_imagen": "assets/lema_somos_uno.jpg",
            "generado": datetime.now().isoformat(),
        },
        "slides": [asdict(s) for s in slides],
    }

    json_path = bundle_dir / f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    html_path = bundle_dir / "index.html"
    html = _render_html(data, color_info)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    pptx_path = bundle_dir / f"{base_name}.pptx"
    _render_pptx(data, pptx_path, assets_dir)

    pdf_path = bundle_dir / f"{base_name}.pdf"
    _render_pdf(html_path, pdf_path)

    return bundle_dir
