"""
Generador de presentaciones litúrgicas en formato JSON + HTML.

No depende de plantillas PPTX maestras. Usa un estilo visual propio:
- Fondos degradados sutiles según color litúrgico
- Ilustraciones estilo Fano / Pati.te / Sara BG (descargables)
- Lema del curso en cada slide
- HTML con Reveal.js para visualización web
- Exportable a PPTX/PDF desde el HTML
"""

import json
import sqlite3
import shutil
import subprocess
import re
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
LEMA_DIR = DATA_DIR / "lemas"
ILUSTRACIONES_DIR = DATA_DIR / "ilustraciones"
OUTPUT_DIR = PROJECT_DIR / "presentaciones_html"

MOMENTOS_ES = [
    "Entrada",
    "Perdón",
    "Gloria",
    "Salmo",
    "Aleluya",
    "Ofertorio",
    "Santo",
    "Padre Nuestro",
    "Paz",
    "Comunión",
    "Canto a María",
    "Despedida",
]

MOMENTOS_KEY = [
    "entrada",
    "perdon",
    "gloria",
    "salmo",
    "aleluya",
    "ofertorio",
    "santo",
    "padre_nuestro",
    "paz",
    "comunion",
    "maria",
    "despedida",
]

# Colores litúrgicos (fondos degradados)
COLORES_LITURGICOS = {
    "verde": {"from": "#e8f5e9", "to": "#c8e6c9", "acento": "#2e7d32"},
    "blanco": {"from": "#fffdf5", "to": "#f5f5f5", "acento": "#5d4037"},
    "rojo": {"from": "#ffebee", "to": "#ffcdd2", "acento": "#c62828"},
    "morado": {"from": "#f3e5f5", "to": "#e1bee7", "acento": "#6a1b9a"},
    "rosa": {"from": "#fce4ec", "to": "#f8bbd0", "acento": "#ad1457"},
    "negro": {"from": "#eeeeee", "to": "#bdbdbd", "acento": "#212121"},
}

# Rutas preferidas de ilustración por tipo de slide
ILUSTRACIONES_PREFERIDAS = {
    "portada": ["comunidad_oracion.svg", "corazon.svg"],
    "entrada": ["camino.svg", "corazon.svg"],
    "perdon": ["corazon.svg", "comunidad_oracion.svg"],
    "gloria": ["corazon.svg"],
    "salmo": ["biblia_abierta.svg", "corazon.svg"],
    "aleluya": ["corazon.svg", "camino.svg"],
    "transicion_palabra": ["biblia_abierta.png", "escuchar.png"],
    "primera_lectura": ["biblia_abierta.png", "escuchar.png"],
    "segunda_lectura": ["biblia_abierta.svg", "comunidad_oracion.svg"],
    "evangelio": ["comunidad_oracion.svg", "corazon.svg"],
    "credo": ["comunidad_oracion.svg", "corazon.svg"],
    "ofertorio": ["pan_vino.png", "pan_vino.svg", "corazon.svg"],
    "santo": ["corazon.svg", "pan_vino.svg"],
    "padre_nuestro": ["comunidad_oracion.svg", "corazon.svg"],
    "paz": ["comunidad_oracion.svg", "corazon.svg"],
    "comunion": ["pan_vino.png", "pan_vino.svg", "comunidad_oracion.svg"],
    "maria": ["comunidad_oracion.svg", "corazon.svg"],
    "despedida": ["camino.svg", "comunidad_oracion.svg"],
}


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class Slide:
    numero: int
    tipo: str
    titulo: str
    contenido: str
    cita: str = ""
    subtitulo: str = ""
    momento: str = ""
    imagen: str = ""


class GeneradorPresentacionHTML:
    """Genera presentación litúrgica en JSON + HTML sin depender de PPTX maestros."""

    def __init__(self, db_path: Optional[str] = None, output_dir: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lema_path = LEMA_DIR / "somos_uno.jpg"
        self.lema_web = "/presentaciones_assets/lema_somos_uno.jpg"
        self.catalogo = self._cargar_catalogo()

    def _cargar_catalogo(self) -> Dict[str, List[str]]:
        catalogo_path = ILUSTRACIONES_DIR / "catalogo.json"
        if not catalogo_path.exists():
            return {}
        with open(catalogo_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("imagenes", {})

    def generar(self, fecha: str, lectura_id: int, canciones_ids: Dict[str, int]) -> Path:
        """Genera JSON, HTML y PPTX para la fecha indicada."""
        lectura = self._get_lectura(lectura_id)
        if not lectura:
            raise ValueError(f"No existe lectura con id={lectura_id}")

        celebracion = lectura["celebracion"] or self._celebracion_from_fecha(fecha)
        color = (lectura["color_liturgico"] or "verde").lower()
        color_info = COLORES_LITURGICOS.get(color, COLORES_LITURGICOS["verde"])

        canciones = self._get_canciones(canciones_ids)
        slides = self._construir_slides(fecha, lectura, celebracion, canciones, color_info)

        base_name = f"{fecha}_presentacion"
        bundle_dir = self.output_dir / base_name
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # Copiar lema e ilustraciones
        assets_dir = bundle_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        if self.lema_path.exists():
            shutil.copy(self.lema_path, assets_dir / "lema_somos_uno.jpg")
        # Copiar ilustraciones usadas (buscar extensión real)
        for slide in slides:
            if not slide.imagen:
                continue
            img_name = Path(slide.imagen).name
            # Buscar en subcarpetas de ilustraciones
            src_candidates = list(ILUSTRACIONES_DIR.rglob(img_name))
            # También buscar sin extensión conocida
            if not src_candidates:
                stem = Path(img_name).stem
                for ext in (".jpg", ".jpeg", ".png", ".svg", ".webp"):
                    src_candidates.extend(ILUSTRACIONES_DIR.rglob(f"{stem}{ext}"))
            for src in src_candidates:
                if src.exists():
                    shutil.copy(src, assets_dir / src.name)
                    break

        # Escribir JSON
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

        # Escribir HTML con Reveal.js embebido (CDN)
        html_path = bundle_dir / "index.html"
        html = self._render_html(data, color_info)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        # Generar PPTX desde datos
        pptx_path = bundle_dir / f"{base_name}.pptx"
        self._render_pptx(data, pptx_path, assets_dir)

        # Generar PDF si hay playwright
        pdf_path = bundle_dir / f"{base_name}.pdf"
        self._render_pdf(html_path, pdf_path)

        return bundle_dir

    def _get_lectura(self, lectura_id: int) -> Optional[sqlite3.Row]:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lecturas WHERE id=?", (lectura_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    def _get_canciones(self, canciones_ids: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        conn = _get_connection()
        cursor = conn.cursor()
        canciones = {}
        for key, cid in canciones_ids.items():
            cursor.execute(
                "SELECT id, titulo, letra_sin_acordes, letra_con_acordes, acordes_json, momento_liturgico FROM canciones WHERE id=?",
                (cid,),
            )
            row = cursor.fetchone()
            if row:
                canciones[key] = dict(row)
        conn.close()
        return canciones

    def _celebracion_from_fecha(self, fecha: str) -> str:
        # Heurística simple; idealmente vendría de la BD.
        return "Domingo"

    def _ilustracion_para(self, tipo: str) -> str:
        """Devuelve la primera ilustración disponible del catálogo para el tipo de slide."""
        opciones = self.catalogo.get(tipo, [])
        for opcion in opciones:
            path = ILUSTRACIONES_DIR / opcion
            if path.exists():
                return f"assets/{Path(opcion).name}"
        # Fallback a SVGs propios
        opciones_svg = ILUSTRACIONES_PREFERIDAS.get(tipo, ["comunidad_oracion.png"])
        for opcion in opciones_svg:
            path = ILUSTRACIONES_DIR / opcion
            if path.exists():
                return f"assets/{opcion}"
        return ""

    def _texto_cancion(self, cancion: Dict[str, Any]) -> str:
        texto = cancion.get("letra_sin_acordes") or cancion.get("letra_con_acordes") or ""
        if not texto:
            return ""
        # Limpiar artefactos HTML / UI del blogspot
        lineas = texto.splitlines()
        limpio = []
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            # Descartar líneas que son botones/UI
            if re.search(r"volver|lista de canciones|escuchar|\[\s*\]|tone|tono|\^", linea, re.IGNORECASE):
                continue
            if linea in ["/", "|", "—"]:
                continue
            limpio.append(linea)
        return "\n\n".join(limpio)

    def _paginar_texto(self, texto: str, max_chars: int = 1200) -> List[str]:
        """Divide un texto largo en fragmentos que quepan en una slide."""
        if len(texto) <= max_chars:
            return [texto]
        
        fragmentos = []
        parrafos = texto.split("\n\n")
        actual = ""
        for parrafo in parrafos:
            if len(actual) + len(parrafo) + 2 > max_chars and actual:
                fragmentos.append(actual.strip())
                actual = parrafo
            else:
                actual = f"{actual}\n\n{parrafo}" if actual else parrafo
        if actual:
            fragmentos.append(actual.strip())
        
        # Si un párrafo individual excede, cortar por oraciones
        resultado = []
        for frag in fragmentos:
            if len(frag) <= max_chars:
                resultado.append(frag)
            else:
                oraciones = frag.replace('. ', '.\n').split('\n')
                actual2 = ""
                for oracion in oraciones:
                    if len(actual2) + len(oracion) + 1 > max_chars and actual2:
                        resultado.append(actual2.strip())
                        actual2 = oracion
                    else:
                        actual2 = f"{actual2} {oracion}".strip()
                if actual2:
                    resultado.append(actual2.strip())
        return resultado

    def _construir_slides(
        self,
        fecha: str,
        lectura: sqlite3.Row,
        celebracion: str,
        canciones: Dict[str, Dict[str, Any]],
        color_info: Dict[str, str],
    ) -> List[Slide]:
        slides: List[Slide] = []
        n = 0

        def add(tipo: str, titulo: str, contenido: str = "", cita: str = "", subtitulo: str = "", momento: str = ""):
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
                    imagen=self._ilustracion_para(tipo),
                )
            )

        # 1. Portada
        add(
            "portada",
            celebracion.upper(),
            subtitulo=f"{self._formatear_fecha(fecha)}",
        )

        # 2. Entrada
        c = canciones.get("entrada")
        if c:
            add("entrada", c.get("titulo", "").upper(), self._texto_cancion(c), momento="Canción de Entrada")

        # 3-4. Perdón / Bendición del agua
        add(
            "perdon",
            "ACTO PENITENCIAL",
            "Yo confieso ante Dios todopoderoso\ny ante vosotros, hermanos,\nque he pecado mucho de pensamiento, palabra, obra y omisión:\npor mi culpa, por mi culpa, por mi gran culpa.\n\nPor eso ruego a Santa María, siempre Virgen,\na los ángeles, a los santos y a vosotros, hermanos,\nque intercedáis por mí ante Dios, nuestro Señor.",
        )
        add("perdon", "BENDICIÓN DEL AGUA", "(Se bendice el agua y se asperja sobre la asamblea)", subtitulo="Señor, Dios todopoderoso, que por medio del agua...")

        # 5. Gloria
        gloria_texto = """Gloria a Dios en el cielo,
y en la tierra paz a los hombres que ama el Señor.
Te alabamos, te bendecimos, te adoramos, te glorificamos.
Te damos gracias, Señor Dios, Rey celestial."""
        add("gloria", "GLORIA", gloria_texto)

        # 6-7. Transición + Primera Lectura
        add("transicion_palabra", "LITURGIA DE LA PALABRA", "Escuchemos la Palabra de Dios")
        if lectura["primera_lectura_texto"]:
            fragmentos = self._paginar_texto(lectura["primera_lectura_texto"])
            for i, frag in enumerate(fragmentos):
                sufijo = f" ({i+1}/{len(fragmentos)})" if len(fragmentos) > 1 else ""
                add(
                    "primera_lectura",
                    f"PRIMERA LECTURA{sufijo}",
                    frag,
                    cita=f"{lectura['primera_lectura_cita']}",
                )

        # 8. Salmo
        if lectura["salmo_texto"]:
            salmo_texto = lectura["salmo_texto"]
            if lectura["salmo_antifona"]:
                salmo_texto = f"Antífona: {lectura['salmo_antifona']}\n\n{salmo_texto}"
            fragmentos = self._paginar_texto(salmo_texto)
            for i, frag in enumerate(fragmentos):
                sufijo = f" ({i+1}/{len(fragmentos)})" if len(fragmentos) > 1 else ""
                add(
                    "salmo",
                    f"SALMO RESPONSORIAL{sufijo}",
                    frag,
                    cita=f"{lectura['salmo_cita']}",
                )

        # 9. Aleluya
        add("aleluya", "ALELUYA", lectura["evangelio_cita"] or "Aleluya, aleluya, aleluya.")

        # 10-11. Segunda Lectura + Evangelio
        if lectura["segunda_lectura_texto"]:
            fragmentos = self._paginar_texto(lectura["segunda_lectura_texto"])
            for i, frag in enumerate(fragmentos):
                sufijo = f" ({i+1}/{len(fragmentos)})" if len(fragmentos) > 1 else ""
                add(
                    "segunda_lectura",
                    f"SEGUNDA LECTURA{sufijo}",
                    frag,
                    cita=f"{lectura['segunda_lectura_cita']}",
                )
        if lectura["evangelio_texto"]:
            fragmentos = self._paginar_texto(lectura["evangelio_texto"])
            for i, frag in enumerate(fragmentos):
                sufijo = f" ({i+1}/{len(fragmentos)})" if len(fragmentos) > 1 else ""
                add(
                    "evangelio",
                    f"EVANGELIO{sufijo}",
                    frag,
                    cita=f"{lectura['evangelio_cita']}",
                )

        # 12-15. Transición Eucarística + Credo + Ofertorio
        add("transicion_eucaristia", "LITURGIA EUCARÍSTICA", "Preparémonos para la mesa del Señor")
        add(
            "credo",
            "CREDO",
            "Creo en Dios, Padre todopoderoso, Creador del cielo y de la tierra.\nCreo en Jesucristo, su único Hijo, nuestro Señor...",
        )
        c = canciones.get("ofertorio")
        if c:
            add("ofertorio", c.get("titulo", "").upper(), self._texto_cancion(c), momento="Ofertorio")

        # 16-19. Santo + Padre Nuestro + Paz
        santo_texto = """Santo, santo, santo es el Señor,
Dios del universo.
Llenos están el cielo y la tierra de tu gloria.
Hosanna en el cielo.
Bendito el que viene en nombre del Señor.
Hosanna en el cielo."""
        add("santo", "SANTO", santo_texto)
        add(
            "padre_nuestro",
            "PADRE NUESTRO",
            "Padre nuestro, que estás en el cielo,\nsantificado sea tu nombre;\nvenga a nosotros tu reino;\nhágase tu voluntad en la tierra como en el cielo.\n\nDanos hoy nuestro pan de cada día;\nperdona nuestras ofensas,\ncomo también nosotros perdonamos a los que nos ofenden;\nno nos dejes caer en la tentación,\ny líbranos del mal.",
        )
        add("paz", "RITO DE LA PAZ", "Señor Jesucristo, que dijiste a tus apóstoles:\n«La paz os dejo, mi paz os doy»,\nno tengas en cuenta nuestros pecados,\nsino la fe de tu Iglesia,\ny conforme a tu palabra concédele la paz y la unidad.\n\nTú que vives y reinas por los siglos de los siglos. Amén.\n\nLa paz del Señor esté siempre con vosotros.")

        # 20-22. Comunión + Canto a María + Despedida
        c = canciones.get("comunion")
        if c:
            add("comunion", c.get("titulo", "").upper(), self._texto_cancion(c), momento="Comunión")
        add(
            "maria",
            "CANTO A MARÍA",
            "Dios te salve, María;\nllena eres de gracia;\nel Señor es contigo.\nBendita tú eres entre todas las mujeres,\ny bendito es el fruto de tu vientre, Jesús.\n\nSanta María, Madre de Dios,\nruega por nosotros, pecadores,\nahora y en la hora de nuestra muerte. Amén.",
        )
        c = canciones.get("despedida")
        if c:
            add("despedida", c.get("titulo", "").upper(), self._texto_cancion(c), momento="Despedida")

        # Renumerar
        for i, s in enumerate(slides, 1):
            s.numero = i
        return slides

    def _formatear_fecha(self, fecha: str) -> str:
        try:
            dt = datetime.strptime(fecha, "%Y-%m-%d")
            meses = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
            ]
            return f"{dt.day} de {meses[dt.month - 1]} de {dt.year}"
        except Exception:
            return fecha

    # ------------------------------------------------------------------
    # HTML con Reveal.js
    # ------------------------------------------------------------------

    def _render_html(self, data: Dict[str, Any], color_info: Dict[str, str]) -> str:
        slides_html = "\n".join(self._slide_to_html(s, color_info) for s in data["slides"])
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data["meta"]["celebracion"]} - {data["meta"]["fecha"]}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/theme/white.css">
  <style>
    :root {{
      --liturgia-from: {color_info['from']};
      --liturgia-to: {color_info['to']};
      --liturgia-acento: {color_info['acento']};
    }}
    @import url('https://fonts.googleapis.com/css2?family=Calibri:wght@400;700&display=swap');
    .reveal {{
      font-family: 'Calibri', 'Carlito', sans-serif;
      font-size: 32px;
      color: #333;
    }}
    .reveal .slides {{
      text-align: left;
    }}
    .reveal .slides section {{
      box-sizing: border-box;
      padding: 40px 60px;
      width: 100%;
      height: 100%;
      background: linear-gradient(135deg, var(--liturgia-from) 0%, var(--liturgia-to) 100%);
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}
    .reveal h1, .reveal h2, .reveal h3 {{
      font-family: 'Calibri', 'Carlito', sans-serif;
      color: var(--liturgia-acento);
      text-transform: uppercase;
      margin-bottom: 0.3em;
      line-height: 1.1;
    }}
    .reveal h1 {{ font-size: 1.4em; }}
    .reveal h2 {{ font-size: 1.2em; }}
    .reveal h3 {{ font-size: 1em; }}
    .reveal p, .reveal li {{
      line-height: 1.5;
      margin-bottom: 0.6em;
    }}
    .reveal .cita {{
      font-size: 0.85em;
      color: #555;
      font-weight: bold;
      margin-bottom: 0.5em;
    }}
    .reveal .contenido {{
      white-space: pre-wrap;
      max-height: 75%;
      overflow: auto;
    }}
    .reveal .logo-lema {{
      position: absolute;
      bottom: 20px;
      right: 30px;
      height: 60px;
      width: auto;
      max-width: 200px;
      z-index: 10;
    }}
    .reveal .ilustracion {{
      position: absolute;
      top: 40px;
      right: 60px;
      max-width: 180px;
      max-height: 180px;
      opacity: 0.9;
      z-index: 5;
    }}
    .reveal .ilustracion-bottom {{
      position: absolute;
      bottom: 100px;
      right: 80px;
      max-width: 220px;
      max-height: 220px;
      opacity: 0.9;
      z-index: 5;
    }}
    .reveal .portada h1 {{
      text-align: center;
      font-size: 1.8em;
      margin-top: 0;
    }}
    .reveal .portada h2 {{
      text-align: center;
      font-size: 1.1em;
      color: #555;
      text-transform: none;
      font-weight: normal;
    }}
    .reveal .transicion h1 {{
      text-align: center;
      font-size: 2em;
    }}
    .reveal .transicion p {{
      text-align: center;
      font-size: 1.1em;
      color: #555;
    }}
    /* Scrollbars */
    .reveal .contenido::-webkit-scrollbar {{
      width: 8px;
    }}
    .reveal .contenido::-webkit-scrollbar-thumb {{
      background: var(--liturgia-acento);
      border-radius: 4px;
    }}
    /* Print/PDF tweaks */
    @media print {{
      .reveal .slides section {{
        page-break-after: always;
        height: 100vh;
      }}
      .reveal .logo-lema {{
        position: fixed;
        bottom: 20px;
        right: 30px;
      }}
    }}
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">
      {slides_html}
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/reveal.js"></script>
  <script>
    Reveal.initialize({{
      hash: true,
      slideNumber: 'c/t',
      transition: 'slide',
      width: 1280,
      height: 720,
      margin: 0,
      minScale: 0.2,
      maxScale: 2.0,
    }});
  </script>
</body>
</html>"""

    def _slide_to_html(self, slide: Dict[str, Any], color_info: Dict[str, str]) -> str:
        tipo = slide["tipo"]
        titulo = self._escape_html(slide["titulo"])
        contenido = self._escape_html(slide["contenido"])
        cita = self._escape_html(slide["cita"])
        subtitulo = self._escape_html(slide["subtitulo"])
        momento = self._escape_html(slide["momento"])
        imagen = slide.get("imagen", "")

        lema_img = "assets/lema_somos_uno.jpg"

        clase = tipo
        html = f'<section class="{clase}" data-transition="fade">\n'

        if imagen:
            html += f'  <img class="ilustracion" src="{imagen}" alt="ilustración">\n'

        if momento:
            html += f'  <h3>{momento}</h3>\n'
        html += f'  <h1>{titulo}</h1>\n'
        if subtitulo:
            html += f'  <h2>{subtitulo}</h2>\n'
        if cita:
            html += f'  <div class="cita">{cita}</div>\n'
        if contenido:
            html += f'  <div class="contenido">{contenido}</div>\n'

        html += f'  <img class="logo-lema" src="{lema_img}" alt="Somos uno">\n'
        html += '</section>\n'
        return html

    def _escape_html(self, text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    # ------------------------------------------------------------------
    # PPTX
    # ------------------------------------------------------------------

    def _render_pptx(self, data: Dict[str, Any], pptx_path: Path, assets_dir: Path):
        """Genera PPTX desde el JSON usando python-pptx con estilos propios."""
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        # Layout en blanco
        blank_layout = prs.slide_layouts[6]
        color = COLORES_LITURGICOS.get(data["meta"]["color_liturgico"].lower(), COLORES_LITURGICOS["verde"])

        lema_img_path = assets_dir / "lema_somos_uno.jpg"

        for slide_data in data["slides"]:
            slide = prs.slides.add_slide(blank_layout)
            self._apply_gradient_background(slide, color)
            self._add_slide_content_pptx(slide, slide_data, color, assets_dir)
            if lema_img_path.exists():
                self._add_lema_pptx(slide, str(lema_img_path))

        prs.save(str(pptx_path))

    def _apply_gradient_background(self, slide, color: Dict[str, str]):
        # python-pptx no soporta degradados fácilmente; usamos color sólido intermedio.
        fill = slide.background.fill
        fill.solid()
        rgb = self._hex_to_rgb(color["from"])
        fill.fore_color.rgb = RGBColor(*rgb)

    def _add_slide_content_pptx(self, slide, slide_data: Dict[str, Any], color: Dict[str, str], assets_dir: Path):
        from pptx.util import Inches, Pt

        acento = self._hex_to_rgb(color["acento"])
        left = Inches(0.7)
        top = Inches(0.5)
        width = Inches(12)

        if slide_data.get("momento"):
            box = slide.shapes.add_textbox(left, top, width, Inches(0.4))
            tf = box.text_frame
            p = tf.paragraphs[0]
            p.text = slide_data["momento"]
            p.font.size = Pt(20)
            p.font.color.rgb = RGBColor(*acento)
            p.font.bold = True
            top += Inches(0.5)

        # Título
        box = slide.shapes.add_textbox(left, top, width, Inches(0.8))
        tf = box.text_frame
        p = tf.paragraphs[0]
        p.text = slide_data["titulo"]
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = RGBColor(*acento)
        p.alignment = PP_ALIGN.LEFT
        top += Inches(1.0)

        if slide_data.get("subtitulo"):
            box = slide.shapes.add_textbox(left, top, width, Inches(0.4))
            tf = box.text_frame
            p = tf.paragraphs[0]
            p.text = slide_data["subtitulo"]
            p.font.size = Pt(22)
            p.font.color.rgb = RGBColor(80, 80, 80)
            top += Inches(0.5)

        if slide_data.get("cita"):
            box = slide.shapes.add_textbox(left, top, width, Inches(0.4))
            tf = box.text_frame
            p = tf.paragraphs[0]
            p.text = slide_data["cita"]
            p.font.size = Pt(18)
            p.font.bold = True
            p.font.color.rgb = RGBColor(100, 100, 100)
            top += Inches(0.5)

        if slide_data.get("contenido"):
            remaining_height = Inches(5.5) - top
            box = slide.shapes.add_textbox(left, top, Inches(10.5), remaining_height)
            tf = box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = slide_data["contenido"]
            p.font.size = Pt(20)
            p.font.color.rgb = RGBColor(60, 60, 60)
            p.line_spacing = 1.3

        # Ilustración (usar PNG/JPG para PPTX)
        if slide_data.get("imagen"):
            base_name = Path(slide_data["imagen"]).stem
            for ext in (".png", ".jpg", ".jpeg"):
                img_path = assets_dir / f"{base_name}{ext}"
                if img_path.exists():
                    slide.shapes.add_picture(str(img_path), Inches(10.8), Inches(0.5), height=Inches(2.2))
                    break

    def _add_lema_pptx(self, slide, lema_path: str):
        try:
            slide.shapes.add_picture(lema_path, Inches(0.3), Inches(6.6), height=Inches(0.7))
        except Exception:
            pass

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # ------------------------------------------------------------------
    # PDF vía playwright
    # ------------------------------------------------------------------

    def _render_pdf(self, html_path: Path, pdf_path: Path):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.goto(f"file://{html_path}")
                page.wait_for_timeout(1000)
                page.pdf(path=str(pdf_path), width="13.333in", height="7.5in", print_background=True)
                browser.close()
        except Exception as exc:
            # No crítico: el PDF se puede generar luego con Reveal.js print o playwright.
            print(f"PDF no generado automáticamente: {exc}")


if __name__ == "__main__":
    gen = GeneradorPresentacionHTML()
    bundle = gen.generar(
        "2026-09-20",
        12,
        {
            "entrada": 8,
            "perdon": 2,
            "gloria": 9,
            "salmo": 3,
            "aleluya": 4,
            "ofertorio": 6,
            "santo": 9,
            "padre_nuestro": 5,
            "paz": 6,
            "comunion": 7,
            "maria": 7,
            "despedida": 8,
        },
    )
    print(f"Bundle generado: {bundle}")
