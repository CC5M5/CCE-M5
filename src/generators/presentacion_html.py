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
            """Creo en Dios, Padre todopoderoso, creador del cielo y de la tierra.
Creo en Jesucristo, su único Hijo, nuestro Señor, que fue concebido por obra y gracia del Espíritu Santo; nació de Santa María Virgen; padeció bajo el poder de Poncio Pilato; fue crucificado, muerto y sepultado; descendió a los infiernos; al tercer día resucitó de entre los muertos; subió a los cielos y está sentado a la derecha de Dios Padre todopoderoso.
Desde allí ha de venir a juzgar a vivos y muertos.
Creo en el Espíritu Santo, la santa Iglesia católica, la comunión de los santos, el perdón de los pecados, la resurrección de la carne y la vida eterna. Amén.""",
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
    @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&family=Nunito:wght@400;600;700&display=swap');
    
    :root {{
      --liturgia-from: {color_info['from']};
      --liturgia-to: {color_info['to']};
      --liturgia-acento: {color_info['acento']};
      --oro: #A16207;
      --morado: #7C3AED;
      --blanco-tarjeta: rgba(255,255,255,0.94);
    }}
    
    .reveal {{
      font-family: 'Nunito', 'Open Sans', sans-serif;
      font-size: 31px;
      color: #2c3e50;
    }}
    
    .reveal .slides {{
      text-align: left;
    }}
    
    .reveal .slides section {{
      box-sizing: border-box;
      padding: 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(135deg, #FAF5FF 0%, #F5F3FF 50%, #F0F4F8 100%);
      display: flex;
      flex-direction: column;
      justify-content: center;
      position: relative;
      overflow: hidden;
    }}
    
    .reveal .slides section::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 8px;
      background: linear-gradient(90deg, var(--liturgia-acento), var(--oro), var(--liturgia-acento));
      z-index: 20;
    }}
    
    .reveal h1, .reveal h2, .reveal h3 {{
      font-family: 'Fredoka', 'Montserrat', sans-serif;
      color: var(--liturgia-acento);
      text-transform: uppercase;
      margin-bottom: 0.3em;
      line-height: 1.15;
      font-weight: 600;
      letter-spacing: -0.01em;
    }}
    
    .reveal h1 {{ font-size: 1.55em; }}
    .reveal h2 {{ font-size: 1.15em; font-weight: 400; text-transform: none; color: #555; }}
    .reveal h3 {{ font-size: 0.85em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.85; }}
    
    .reveal p, .reveal li {{
      line-height: 1.55;
      margin-bottom: 0.5em;
    }}
    
    .reveal .tarjeta {{
      background: var(--blanco-tarjeta);
      border-radius: 24px;
      padding: 38px 48px;
      margin: 45px 60px;
      box-shadow: 0 20px 60px rgba(124, 58, 237, 0.12);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(124, 58, 237, 0.12);
      max-height: 82%;
      overflow: auto;
      position: relative;
      z-index: 5;
    }}
    
    .reveal .tarjeta::after {{
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 6px;
      background: linear-gradient(90deg, var(--liturgia-acento), var(--oro));
      border-radius: 0 0 24px 24px;
    }}
    
    .reveal .cita {{
      font-size: 0.85em;
      font-weight: 700;
      margin-bottom: 0.6em;
      padding: 0.25em 0.7em;
      display: inline-block;
      background: linear-gradient(90deg, var(--liturgia-acento), var(--oro));
      color: white;
      border-radius: 8px;
    }}
    
    .reveal .contenido {{
      white-space: pre-wrap;
      max-height: none;
      overflow: visible;
      font-size: 0.92em;
      line-height: 1.5;
    }}
    
    .reveal .logo-lema {{
      position: absolute;
      bottom: 22px;
      right: 30px;
      height: 55px;
      width: auto;
      max-width: 180px;
      z-index: 10;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
    }}
    
    .reveal .ilustracion {{
      position: absolute;
      top: auto;
      bottom: 90px;
      right: 80px;
      max-width: 320px;
      max-height: 320px;
      opacity: 0.98;
      z-index: 6;
      border-radius: 20px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.12);
      object-fit: contain;
    }}
    
    section:has(.ilustracion) .tarjeta {{
      margin-right: 380px;
    }}
    
    .reveal .portada {{
      text-align: center;
      justify-content: center;
      align-items: center;
      background: linear-gradient(135deg, var(--liturgia-acento) 0%, #6D28D9 40%, #7C3AED 70%, var(--oro) 100%);
    }}
    
    .reveal .portada .tarjeta {{
      background: rgba(255,255,255,0.96);
      max-width: 900px;
      margin: 0 auto;
      text-align: center;
    }}
    
    .reveal .portada h1 {{
      text-align: center;
      font-size: 2em;
      margin-top: 0;
    }}
    
    .reveal .portada h2 {{
      text-align: center;
      font-size: 1.2em;
      color: #555;
      text-transform: none;
      font-weight: 400;
      margin-top: 0.5em;
    }}
    
    .reveal .portada .ilustracion {{
      position: relative;
      top: auto;
      right: auto;
      bottom: auto;
      max-width: 380px;
      max-height: 380px;
      margin: 0 auto 1em;
    }}
    
    .reveal .transicion .tarjeta {{
      text-align: center;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      min-height: 55%;
    }}
    
    .reveal .transicion h1 {{
      text-align: center;
      font-size: 2.2em;
      letter-spacing: 0.04em;
    }}
    
    .reveal .cancion .tarjeta {{
      background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(250,245,255,0.96) 100%);
    }}
    
    .reveal .cancion .contenido {{
      font-size: 0.92em;
      line-height: 1.3;
    }}
    
    .reveal .cancion .contenido br {{
      display: block;
      content: "";
      margin-bottom: 0.1em;
    }}
    
    @keyframes fadeInUp {{
      from {{ opacity: 0; transform: translateY(20px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .reveal .slides section.present {{
      animation: fadeInUp 0.5s ease-out;
    }}
    
    .reveal .contenido::-webkit-scrollbar {{
      width: 6px;
    }}
    .reveal .contenido::-webkit-scrollbar-thumb {{
      background: var(--liturgia-acento);
      border-radius: 3px;
    }}
    
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
      section:has(.ilustracion) .tarjeta {{
        margin-right: 380px;
      }}
      .reveal .tarjeta {{
        margin: 30px 40px;
      }}
    }}  </style>
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

    def _slide_to_html(self, slide: Dict[str, Any], color_info: Dict[str, str], template: str = "liturgia") -> str:
        tipo = slide["tipo"]
        titulo = self._escape_html(slide["titulo"])
        contenido = self._escape_html(slide["contenido"])
        cita = self._escape_html(slide["cita"])
        subtitulo = self._escape_html(slide["subtitulo"])
        momento = self._escape_html(slide["momento"])
        imagen = slide.get("imagen", "")

        lema_img = "assets/lema_somos_uno.jpg"
        inner = ""

        if momento:
            inner += f'  <h3>{momento}</h3>\n'
        inner += f'  <h1>{titulo}</h1>\n'
        if subtitulo:
            inner += f'  <h2>{subtitulo}</h2>\n'
        if cita:
            inner += f'  <div class="cita">{cita}</div>\n'
        if contenido:
            inner += f'  <div class="contenido">{contenido}</div>\n'

        clase = tipo
        html = f'<section class="{clase}" data-transition="fade">\n'

        if imagen:
            html += f'  <img class="ilustracion" src="{imagen}" alt="ilustración">\n'

        html += f'  <div class="tarjeta">\n{inner}  </div>\n'
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
    # PPTX con estilo litúrgico mejorado
    # ------------------------------------------------------------------

    def _render_pptx(self, data: Dict[str, Any], pptx_path: Path, assets_dir: Path):
        """Genera PPTX desde el JSON con estilo litúrgico visual mejorado."""
        from pptx.util import Inches, Pt
        from pptx.enum.shapes import MSO_SHAPE

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        blank_layout = prs.slide_layouts[6]

        color = COLORES_LITURGICOS.get(data["meta"]["color_liturgico"].lower(), COLORES_LITURGICOS["verde"])
        lema_img_path = assets_dir / "lema_somos_uno.jpg"

        # Theme tokens (inspired by pptx-designer church-religious-organization)
        primary = (124, 58, 237)    # #7C3AED purple
        accent_gold = (161, 98, 7)  # #A16207 gold
        bg_light = (250, 245, 255)  # #FAF5FF
        text_dark = (44, 62, 80)    # #2c3e50
        text_muted = (85, 85, 85)

        for slide_data in data["slides"]:
            slide = prs.slides.add_slide(blank_layout)
            is_portada = slide_data["tipo"] == "portada"
            has_image = bool(slide_data.get("imagen"))

            # Background
            self._apply_gradient_background(slide, color, is_portada, primary, bg_light)

            # Top accent bar
            self._add_top_bar(slide, primary, accent_gold)

            # Lema
            if lema_img_path.exists():
                self._add_lema_pptx(slide, str(lema_img_path))

            # Illustration
            if has_image:
                self._add_illustration_pptx(slide, slide_data["imagen"], assets_dir, is_portada)

            # Card + content
            self._add_content_card_pptx(
                slide, slide_data, primary, accent_gold, text_dark, text_muted, has_image, is_portada
            )

        prs.save(str(pptx_path))

    def _apply_gradient_background(self, slide, color: Dict[str, str], is_portada: bool, primary: Tuple[int, ...], bg_light: Tuple[int, ...]):
        fill = slide.background.fill
        fill.solid()
        if is_portada:
            fill.fore_color.rgb = RGBColor(*primary)
        else:
            fill.fore_color.rgb = RGBColor(*bg_light)

    def _add_top_bar(self, slide, primary: Tuple[int, ...], accent_gold: Tuple[int, ...]):
        from pptx.util import Inches, Pt
        from pptx.enum.shapes import MSO_SHAPE
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
        bar.fill.solid()
        bar.fill.fore_color.rgb = RGBColor(*primary)
        bar.line.fill.background()

    def _add_illustration_pptx(self, slide, imagen: str, assets_dir: Path, is_portada: bool):
        from pptx.util import Inches
        base_name = Path(imagen).stem
        for ext in (".png", ".jpg", ".jpeg"):
            img_path = assets_dir / f"{base_name}{ext}"
            if img_path.exists():
                if is_portada:
                    slide.shapes.add_picture(str(img_path), Inches(4.8), Inches(0.6), height=Inches(3.0))
                else:
                    slide.shapes.add_picture(str(img_path), Inches(9.9), Inches(1.2), height=Inches(3.4))
                break

    def _add_lema_pptx(self, slide, lema_path: str):
        from pptx.util import Inches
        try:
            slide.shapes.add_picture(lema_path, Inches(0.4), Inches(6.55), height=Inches(0.75))
        except Exception:
            pass

    def _add_content_card_pptx(
        self, slide, slide_data: Dict[str, Any],
        primary: Tuple[int, ...], accent_gold: Tuple[int, ...],
        text_dark: Tuple[int, ...], text_muted: Tuple[int, ...],
        has_image: bool, is_portada: bool
    ):
        from pptx.util import Inches, Pt
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.enum.text import MSO_ANCHOR

        # Card dimensions
        if is_portada:
            card_left = Inches(1.5)
            card_top = Inches(3.9)
            card_width = Inches(10.3)
            card_height = Inches(2.8)
        elif has_image:
            card_left = Inches(0.7)
            card_top = Inches(0.7)
            card_width = Inches(8.8)
            card_height = Inches(6.1)
        else:
            card_left = Inches(0.7)
            card_top = Inches(0.7)
            card_width = Inches(12.0)
            card_height = Inches(6.1)

        # Card shape
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, card_left, card_top, card_width, card_height)
        card.fill.solid()
        if is_portada:
            card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        else:
            card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        card.line.color.rgb = RGBColor(221, 214, 254)
        card.line.width = Pt(1)
        # Rounded corners adjustment
        if hasattr(card, "adjustments"):
            try:
                card.adjustments[0] = 0.08
            except Exception:
                pass

        # Bottom accent line
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
            card_left, card_top + card_height - Inches(0.08), card_width, Inches(0.08))
        line.fill.solid()
        line.fill.fore_color.rgb = RGBColor(*primary)
        line.line.fill.background()

        # Text padding inside card
        text_left = card_left + Inches(0.35)
        text_top = card_top + Inches(0.25)
        text_width = card_width - Inches(0.7)
        text_height = card_height - Inches(0.45)

        # Build text
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

        paragraphs = full_text.split("\n")
        for i, para_text in enumerate(paragraphs):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            if not para_text.strip():
                continue

            run = p.add_run()
            run.text = para_text

            # Determine style based on position
            if i == 0 and slide_data.get("momento"):
                run.font.size = Pt(16)
                run.font.bold = True
                run.font.color.rgb = RGBColor(*primary)
            elif (i == 0 and not slide_data.get("momento")) or (i == 1 and slide_data.get("momento")):
                run.font.size = Pt(32 if is_portada else 28)
                run.font.bold = True
                run.font.color.rgb = RGBColor(*primary)
            elif para_text.startswith(slide_data.get("cita", "")) and slide_data.get("cita"):
                run.font.size = Pt(16)
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                # Add citation background
                p.alignment = PP_ALIGN.LEFT
                # We can't easily set per-paragraph background, so style with color
                run.font.color.rgb = RGBColor(*primary)
            else:
                run.font.size = Pt(19)
                run.font.color.rgb = RGBColor(*text_dark)
                if slide_data["tipo"] == "cancion":
                    run.font.size = Pt(18)
                    p.line_spacing = 1.15

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
