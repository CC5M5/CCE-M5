"""
Generador de presentaciones litúrgicas en formato JSON + HTML + PPTX + PDF.

Características:
- Aspecto 4:3 consistente en HTML, PPTX y PDF.
- Diapositivas generadas desde un JSON intermediario común para que PPTX y HTML sean idénticos en contenido.
- Canciones con letra compacta (sin espacios extra entre líneas de un verso).
- Estructura litúrgica corregida: no se incluyen transiciones "LITURGIA DE LA PALABRA" ni "LITURGIA EUCARÍSTICA".
- Perdón y bendición del agua: acto penitencial por defecto; bendición del agua solo bajo indicación.
- Gloria, Ofertorio, Santo, Padre Nuestro, Paz y Canto a María son canciones si hay asignación; si no, diapositiva con título + "Rellenar a mano".
- Lecturas largas se dividen en varias diapositivas con indicador (1/2, 2/2...).
- Aleluya es canción y va entre Segunda Lectura y Evangelio.
- Diapositiva final tipo portada con mensaje de despedida y frase del Evangelio.
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
from pptx.util import Emu, Inches, Pt, Cm

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
LEMA_DIR = DATA_DIR / "lemas"
ILUSTRACIONES_DIR = DATA_DIR / "ilustraciones"
OUTPUT_DIR = PROJECT_DIR / "presentaciones_html"

# 4:3 en cm reales: 33,87 cm × 25,4025 cm
SLIDE_WIDTH_INCHES = float(Cm(33.87)) / 914400
SLIDE_HEIGHT_INCHES = float(Cm(25.4025)) / 914400

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

MOMENTO_A_KEY = dict(zip(MOMENTOS_ES, MOMENTOS_KEY))

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

TEXTOS_LITURGICOS = {
    "acto_penitencial": (
        "Yo confieso ante Dios todopoderoso\n"
        "y ante vosotros, hermanos,\n"
        "que he pecado mucho de pensamiento, palabra, obra y omisión:\n"
        "por mi culpa, por mi culpa, por mi gran culpa.\n\n"
        "Por eso ruego a Santa María, siempre Virgen,\n"
        "a los ángeles, a los santos y a vosotros, hermanos,\n"
        "que intercedáis por mí ante Dios, nuestro Señor."
    ),
    "bendicion_agua": "(Se bendice el agua y se asperja sobre la asamblea)",
    "gloria": (
        "Gloria a Dios en el cielo,\n"
        "y en la tierra paz a los hombres que ama el Señor.\n"
        "Te alabamos, te bendecimos, te adoramos, te glorificamos.\n"
        "Te damos gracias, Señor Dios, Rey celestial."
    ),
    "credo": (
        "Creo en Dios, Padre todopoderoso, creador del cielo y de la tierra.\n"
        "Creo en Jesucristo, su único Hijo, nuestro Señor, que fue concebido por obra y gracia del Espíritu Santo; "
        "nació de Santa María Virgen; padeció bajo el poder de Poncio Pilato; fue crucificado, muerto y sepultado; "
        "descendió a los infiernos; al tercer día resucitó de entre los muertos; subió a los cielos y está sentado a la derecha de Dios Padre todopoderoso.\n"
        "Desde allí ha de venir a juzgar a vivos y muertos.\n"
        "Creo en el Espíritu Santo, la santa Iglesia católica, la comunión de los santos, el perdón de los pecados, "
        "la resurrección de la carne y la vida eterna. Amén."
    ),
    "santo": (
        "Santo, santo, santo es el Señor,\n"
        "Dios del universo.\n"
        "Llenos están el cielo y la tierra de tu gloria.\n"
        "Hosanna en el cielo.\n"
        "Bendito el que viene en nombre del Señor.\n"
        "Hosanna en el cielo."
    ),
    "padre_nuestro": (
        "Padre nuestro, que estás en el cielo,\n"
        "santificado sea tu nombre;\n"
        "venga a nosotros tu reino;\n"
        "hágase tu voluntad en la tierra como en el cielo.\n\n"
        "Danos hoy nuestro pan de cada día;\n"
        "perdona nuestras ofensas,\n"
        "como también nosotros perdonamos a los que nos ofenden;\n"
        "no nos dejes caer en la tentación,\n"
        "y líbranos del mal."
    ),
    "paz": (
        "Señor Jesucristo, que dijiste a tus apóstoles:\n"
        "«La paz os dejo, mi paz os doy»,\n"
        "no tengas en cuenta nuestros pecados,\n"
        "sino la fe de tu Iglesia,\n"
        "y conforme a tu palabra concédele la paz y la unidad.\n\n"
        "Tú que vives y reinas por los siglos de los siglos. Amén.\n\n"
        "La paz del Señor esté siempre con vosotros."
    ),
    "maria": (
        "Dios te salve, María;\n"
        "llena eres de gracia;\n"
        "el Señor es contigo.\n"
        "Bendita tú eres entre todas las mujeres,\n"
        "y bendito es el fruto de tu vientre, Jesús.\n\n"
        "Santa María, Madre de Dios,\n"
        "ruega por nosotros, pecadores,\n"
        "ahora y en la hora de nuestra muerte. Amén."
    ),
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
    """Genera presentación litúrgica en JSON + HTML + PPTX + PDF."""

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

    def generar(
        self,
        fecha: str,
        lectura_id: int,
        canciones_ids: Dict[str, int],
        incluir_bendicion_agua: bool = False,
        frase_evangelio: str = "",
    ) -> Path:
        """Genera JSON, HTML, PPTX y PDF para la fecha indicada."""
        lectura = self._get_lectura(lectura_id)
        if not lectura:
            raise ValueError(f"No existe lectura con id={lectura_id}")

        celebracion = lectura["celebracion"] or self._celebracion_from_fecha(fecha)
        color = (lectura["color_liturgico"] or "verde").lower()
        color_info = COLORES_LITURGICOS.get(color, COLORES_LITURGICOS["verde"])

        canciones = self._get_canciones(canciones_ids)
        if not frase_evangelio:
            frase_evangelio = self._extraer_frase_evangelio(lectura)

        slides = self._construir_slides(
            fecha, lectura, celebracion, canciones, color_info,
            incluir_bendicion_agua=incluir_bendicion_agua,
            frase_evangelio=frase_evangelio,
        )

        base_name = f"{fecha}_presentacion"
        bundle_dir = self.output_dir / base_name
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # Copiar lema e ilustraciones
        assets_dir = bundle_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        if self.lema_path.exists():
            shutil.copy(self.lema_path, assets_dir / "lema_somos_uno.jpg")
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
        html = self._render_html(data, color_info)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        pptx_path = bundle_dir / f"{base_name}.pptx"
        self._render_pptx(data, pptx_path, assets_dir)

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
        return "Domingo"

    def _ilustracion_para(self, tipo: str) -> str:
        """Devuelve la primera ilustración disponible del catálogo para el tipo de slide."""
        opciones = self.catalogo.get(tipo, [])
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

    def _extraer_frase_evangelio(self, lectura: sqlite3.Row) -> str:
        """Extrae una frase corta representativa del Evangelio."""
        texto = lectura["evangelio_texto"] if lectura and "evangelio_texto" in lectura.keys() else ""
        if not texto:
            return ""
        comillas = re.findall(r'«([^»]{20,180})»', texto)
        if comillas:
            return comillas[-1].strip()
        for oracion in re.split(r'(?<=[.!?])\s+', texto):
            oracion = oracion.strip()
            if 20 <= len(oracion) <= 180:
                return oracion + "."
        return texto[:180].strip() + "..."

    def _texto_cancion(self, cancion: Dict[str, Any]) -> str:
        """
        Devuelve la letra de una canción limpia, compacta y lista para slide.

        - Elimina líneas de acordes musicales residuales.
        - Une frases cortadas artificialmente por saltos de línea.
        - Detecta estribillos y los marca con doble asterisco para negrita.
        """
        texto = cancion.get("letra_sin_acordes") or cancion.get("letra_con_acordes") or ""
        if not texto:
            return ""

        lineas = texto.splitlines()

        basura_re = re.compile(
            r"volver|lista de canciones|escuchar|\[\s*\]|\btone\b|tono|\^",
            re.IGNORECASE,
        )
        estribillo_marcas = {"estribillo", "estrib", "coro", "todos", "todas"}
        # Palabras cortas en mayúsculas que suelen ser inicio de frase cortada al final de línea
        palabras_cortas = {
            "EL", "ÉL", "LA", "LAS", "LOS", "UN", "UNA", "Y", "O", "U", "NO", "SI", "ME", "SE", "TE",
            "LO", "LE", "LES", "NOS", "OS", "DEL", "AL", "CON", "POR", "PARA", "QUE", "COMO", "CUANDO",
            "MI", "SU", "SUS", "TU", "TUS", "ES", "SON", "ESTÁ", "ESTAN", "A", "EN", "DE", "DIOS",
        }

        limpio: List[str] = []
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            if linea in ["/", "|", "—"]:
                continue
            if basura_re.search(linea):
                continue
            if self._es_linea_solo_acordes(linea):
                continue
            limpio.append(linea)

        # Unir frases cortadas artificialmente
        unidas: List[str] = []
        actual = ""
        terminadores = ".!?;:)"
        for linea in limpio:
            # Ignorar acordes que hayan podido escapar al filtrado previo
            if self._es_linea_solo_acordes(linea):
                continue

            if not actual:
                actual = linea
                continue

            # Si la línea actual es solo una o dos palabras cortas en mayúsculas, unir a la siguiente
            palabras_actuales = actual.split()
            if (
                all(p.upper() in palabras_cortas for p in palabras_actuales)
                and len(palabras_actuales) <= 2
                and actual[-1] not in terminadores
            ):
                actual = self._unir_lineas(actual, linea)
                continue

            # Unir frases cortadas artificialmente
        unidas: List[str] = []
        actual = ""
        terminadores = ".!?;:)"
        for linea in limpio:
            # Ignorar acordes que hayan podido escapar al filtrado previo
            if self._es_linea_solo_acordes(linea):
                continue

            # Si la línea es una marca de estribillo, cerrar el verso actual y añadir la marca suelta
            if linea.strip().upper() in estribillo_marcas:
                if actual:
                    unidas.append(actual)
                    actual = ""
                unidas.append(linea.strip().upper())
                continue

            if not actual:
                actual = linea
                continue

            # Si la línea actual es solo una o dos palabras cortas en mayúsculas, unir a la siguiente
            palabras_actuales = actual.split()
            if (
                all(p.upper() in palabras_cortas for p in palabras_actuales)
                and len(palabras_actuales) <= 2
                and actual[-1] not in terminadores
            ):
                actual = self._unir_lineas(actual, linea)
                continue

            # Si la línea actual termina en signo fuerte, cerramos verso
            if actual[-1] in terminadores:
                unidas.append(actual)
                actual = linea
                continue

            # Si la nueva línea empieza en minúscula, pertenece al mismo verso
            if re.match(r"^[a-záéíóúñ]", linea):
                actual = self._unir_lineas(actual, linea)
                continue

            # Si la nueva línea empieza en mayúscula, puede ser nuevo verso.
            # Pero si la actual es corta o no termina bien, unimos.
            # Si la línea actual es una marca de estribillo, cerramos siempre
            if actual.strip().lower() in estribillo_marcas:
                unidas.append(actual)
                actual = linea
                continue

            if re.match(r"^[A-ZÁÉÍÓÚÑ¿¡]", linea):
                if len(palabras_actuales) <= 2 and actual[-1] not in terminadores:
                    actual = self._unir_lineas(actual, linea)
                else:
                    unidas.append(actual)
                    actual = linea
            else:
                actual = self._unir_lineas(actual, linea)

        if actual:
            unidas.append(actual)

        # Detectar y marcar estribillos en negrita
        resultado: List[str] = []
        en_estribillo = False
        for linea in unidas:
            linea_l = linea.lower().strip("():[] ")
            if linea_l in estribillo_marcas:
                en_estribillo = not en_estribillo
                continue

            # Línea completamente en mayúsculas (con longitud suficiente) = estribillo
            if linea == linea.upper() and len(linea) > 8 and not linea.startswith("("):
                resultado.append(f"**{linea}**")
                continue

            # Si estamos en modo estribillo y la línea no es pura mayúsculas, marcamos también
            if en_estribillo:
                resultado.append(f"**{linea}**")
            else:
                resultado.append(linea)

        return self._compactar_para_slide("\n".join(resultado))

    def _es_linea_solo_acordes(self, linea: str) -> bool:
        """Devuelve True si la línea contiene únicamente notas musicales/acordes."""
        # Token de nota musical: letras A-G o nombres solfege (Do, Re, Mi, Fa, Sol, La, Si)
        nota = r"(?:[A-Ga-g](?:[#b\u266d\u266f]|es|is|bemol|sostenido)?|Do|Re|Mi|Fa|Sol|La|Si|do|re|mi|fa|sol|la|si)"
        calidad = r"(?:m(?:in)?|M(?:aj)?|maj7?|7|9|6|dim|sus|add|aug|°|0|#|b|\u266d|\u266f|es|is|bemol|sostenido)"
        bajo = rf"(?:/{nota})"
        acorde_completo = rf"(?:{nota}(?:\s*{calidad})?(?:\s*{bajo})?)"
        acordes_re = re.compile(
            rf"^\s*(?:\(\s*\d*[\u00aa\u00ba°]?\s*:?\s*)?{acorde_completo}(?:\s+{acorde_completo})*\s*\)?\s*$"
        )
        return bool(acordes_re.match(linea))

    def _unir_lineas(self, anterior: str, siguiente: str) -> str:
        """Une dos líneas de letra respetando guiones de separación silábica."""
        if anterior.endswith("-"):
            return anterior[:-1] + siguiente
        return f"{anterior} {siguiente}"

    def _compactar_salmo_o_lectura(self, texto: str) -> str:
        """
        Compacta salmos y lecturas bíblicas.

        El texto de Ciudad Redonda suele tener dobles saltos de línea entre
        frases de un mismo verso. Esta función detecta los versos y une las
        frases internas con comas/espacios, dejando un doble salto de línea
        entre versos.
        """
        if not texto:
            return ""

        lineas = [l.strip() for l in texto.splitlines() if l.strip()]
        versos: List[List[str]] = []
        actual: List[str] = []

        def _empieza_verso(linea: str) -> bool:
            return bool(re.match(r"^[A-ZÁÉÍÓÚÑ]", linea))

        for i, linea in enumerate(lineas):
            if not actual:
                actual.append(linea)
                continue

            ultima = actual[-1]
            termina_verso = ultima.endswith((".", "!", "?", ":")) or _empieza_verso(linea)
            # Si la línea anterior termina en punto fuerte o la nueva empieza en mayúscula,
            # consideramos que empieza un nuevo verso.
            if termina_verso and _empieza_verso(linea):
                versos.append(actual)
                actual = [linea]
            else:
                actual.append(linea)

        if actual:
            versos.append(actual)

        resultado: List[str] = []
        for verso in versos:
            unido = verso[0]
            for frase in verso[1:]:
                # Si la frase anterior termina en coma/punto y coma, unir con espacio.
                # Si termina en punto, añadir espacio.
                if unido[-1] in ",;":
                    unido = f"{unido} {frase}"
                else:
                    unido = f"{unido} {frase}"
            resultado.append(unido)

        return "\n\n".join(resultado)

    def _compactar_para_slide(self, texto: str) -> str:
        """
        Lleva un texto plano a formato de slide compacto.

        - Líneas consecutivas no vacías se unen con \n simple (mismo verso/párrafo).
        - Líneas en blanco separan estrofas/párrafos (\n\n).
        """
        if not texto:
            return ""
        parrafos = []
        actual = []
        for linea in texto.splitlines():
            linea = linea.strip()
            if linea:
                actual.append(linea)
            else:
                if actual:
                    parrafos.append("\n".join(actual))
                    actual = []
        if actual:
            parrafos.append("\n".join(actual))
        return "\n\n".join(parrafos)

    def _paginar_texto(self, texto: str, max_chars: int = 1600) -> List[str]:
        """Divide un texto largo en fragmentos que quepan en una slide 4:3 real (33,87 cm × 25,4025 cm)."""
        if len(texto) <= max_chars:
            return [texto]

        parrafos = self._compactar_salmo_o_lectura(texto).split("\n\n")
        fragmentos = []
        actual = ""
        for parrafo in parrafos:
            if len(actual) + len(parrafo) + 2 > max_chars and actual:
                fragmentos.append(actual.strip())
                actual = parrafo
            else:
                actual = f"{actual}\n\n{parrafo}" if actual else parrafo
        if actual:
            fragmentos.append(actual.strip())

        resultado = []
        for frag in fragmentos:
            if len(frag) <= max_chars:
                resultado.append(frag)
            else:
                oraciones = frag.replace(". ", ".\n").split("\n")
                actual2 = ""
                for oracion in oraciones:
                    if len(actual2) + len(oracion) + 1 > max_chars and actual2:
                        resultado.append(actual2.strip())
                        actual2 = oracion
                    else:
                        actual2 = f"{actual2} {oracion}".strip()
                if actual2:
                    resultado.append(actual2.strip())
        return fragmentos

    def _add_cancion_slide(
        self,
        add,
        canciones: Dict[str, Dict[str, Any]],
        key: str,
        tipo: str,
        momento: str,
        titulo_fallback: str,
    ):
        """Añade slide de canción; si no existe, pone título + 'Rellenar a mano'."""
        c = canciones.get(key)
        if c and c.get("titulo"):
            texto = self._texto_cancion(c)
            if not texto:
                texto = "Rellenar a mano"
            add(tipo, c.get("titulo", "").upper(), texto, momento=momento)
        else:
            add(tipo, titulo_fallback.upper(), "Rellenar a mano", momento=momento)

    def _construir_slides(
        self,
        fecha: str,
        lectura: sqlite3.Row,
        celebracion: str,
        canciones: Dict[str, Dict[str, Any]],
        color_info: Dict[str, str],
        incluir_bendicion_agua: bool = False,
        frase_evangelio: str = "",
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
        self._add_cancion_slide(add, canciones, "entrada", "entrada", "Canción de Entrada", "Entrada")

        # 3. Perdón: canción si se asignó; si no, acto penitencial
        if canciones.get("perdon"):
            self._add_cancion_slide(add, canciones, "perdon", "perdon", "Acto Penitencial", "Perdón")
        else:
            add("perdon", "ACTO PENITENCIAL", TEXTOS_LITURGICOS["acto_penitencial"])

        # 4. Bendición del agua solo bajo indicación
        if incluir_bendicion_agua:
            add(
                "perdon",
                "BENDICIÓN DEL AGUA",
                TEXTOS_LITURGICOS["bendicion_agua"],
                subtitulo="Señor, Dios todopoderoso, que por medio del agua...",
            )

        # 5. Gloria: canción si hay asignación; si no, omitido
        if canciones.get("gloria"):
            self._add_cancion_slide(add, canciones, "gloria", "gloria", "Gloria", "GLORIA")

        # 6. Primera Lectura
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

        # 7. Salmo (compacto) + canción del salmo en la misma diapositiva
        if lectura["salmo_texto"]:
            salmo_texto = self._compactar_salmo_o_lectura(lectura["salmo_texto"])
            if lectura["salmo_antifona"]:
                salmo_texto = f"Antífona: {lectura['salmo_antifona']}\n\n{salmo_texto}"
            # Si hay canción asignada para el salmo, se añade en la misma slide
            salmo_cancion = canciones.get("salmo")
            if salmo_cancion and salmo_cancion.get("titulo"):
                cancion_texto = self._texto_cancion(salmo_cancion)
                salmo_texto = f"{salmo_texto}\n\n---\n\n{salmo_cancion['titulo'].upper()}\n{cancion_texto}"
            fragmentos = self._paginar_texto(salmo_texto)
            for i, frag in enumerate(fragmentos):
                sufijo = f" ({i+1}/{len(fragmentos)})" if len(fragmentos) > 1 else ""
                add(
                    "salmo",
                    f"SALMO RESPONSORIAL{sufijo}",
                    frag,
                    cita=f"{lectura['salmo_cita']}",
                )

        # 8. Segunda Lectura
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

        # 9. Aleluya: canción
        self._add_cancion_slide(add, canciones, "aleluya", "aleluya", "Aleluya", "ALELUYA")

        # 10. Evangelio
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

        # 11. Credo
        add("credo", "CREDO", TEXTOS_LITURGICOS["credo"])

        # 12-16. Ofertorio, Santo, Padre Nuestro, Paz
        self._add_cancion_slide(add, canciones, "ofertorio", "ofertorio", "Ofertorio", "OFERTORIO")
        self._add_cancion_slide(add, canciones, "santo", "santo", "Santo", "SANTO")
        self._add_cancion_slide(add, canciones, "padre_nuestro", "padre_nuestro", "Padre Nuestro", "PADRE NUESTRO")
        self._add_cancion_slide(add, canciones, "paz", "paz", "Rito de la Paz", "PAZ")

        # 17. Comunión
        self._add_cancion_slide(add, canciones, "comunion", "comunion", "Comunión", "COMUNIÓN")

        # 18. Canto a María
        self._add_cancion_slide(add, canciones, "maria", "maria", "Canto a María", "CANTO A MARÍA")

        # 19. Despedida
        self._add_cancion_slide(add, canciones, "despedida", "despedida", "Despedida", "DESPEDIDA")

        # 20. Diapositiva final
        add(
            "portada",
            "¡ID EN PAZ!",
            f"La paz del Señor esté siempre con vosotros.\n\n«{frase_evangelio}»",
            subtitulo="Somos uno · " + self._formatear_fecha(fecha),
        )

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
    # HTML con Reveal.js (4:3)
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
      font-size: 26px;
      color: #2c3e50;
    }}

    .reveal .slides {{
      text-align: left;
    }}

    .reveal .slides section {{
      padding: 0;
      background: linear-gradient(135deg, #FAF5FF 0%, #F5F3FF 50%, #F0F4F8 100%);
    }}

    .slide-wrapper {{
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: flex-start;
      position: relative;
      overflow: hidden;
      box-sizing: border-box;
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

    .reveal h1 {{ font-size: 1.35em; }}
    .reveal h2 {{ font-size: 0.95em; font-weight: 400; text-transform: none; color: #555; }}
    .reveal h3 {{ font-size: 0.72em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.85; }}

    .reveal p, .reveal li {{
      line-height: 1.5;
      margin-bottom: 0.5em;
    }}

    .reveal .tarjeta {{
      background: var(--blanco-tarjeta);
      border-radius: 24px;
      padding: 24px 32px;
      margin: 30px 40px 80px 40px;
      box-shadow: 0 20px 60px rgba(124, 58, 237, 0.12);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(124, 58, 237, 0.12);
      max-height: 76%;
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
      font-size: 0.85em;
      line-height: 1.25;
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
      right: 70px;
      max-width: 280px;
      max-height: 280px;
      opacity: 0.98;
      z-index: 6;
      border-radius: 20px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.12);
      object-fit: contain;
    }}

    section:has(.ilustracion) .tarjeta {{
      margin-right: 320px;
    }}

    .reveal .portada .slide-wrapper {{
      text-align: center;
      justify-content: center;
      align-items: center;
      background: linear-gradient(135deg, var(--liturgia-acento) 0%, #6D28D9 40%, #7C3AED 70%, var(--oro) 100%);
    }}

    .reveal .portada .tarjeta {{
      background: rgba(255,255,255,0.96);
      max-width: 760px;
      margin: 0 auto;
      text-align: center;
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
      font-weight: 400;
      margin-top: 0.5em;
    }}

    .reveal .portada .ilustracion {{
      position: relative;
      top: auto;
      right: auto;
      bottom: auto;
      max-width: 320px;
      max-height: 320px;
      margin: 0 auto 1em;
    }}

    .reveal .transicion .slide-wrapper {{
      justify-content: center;
      align-items: center;
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
      font-size: 2.0em;
      letter-spacing: 0.04em;
    }}

    .reveal .cancion .tarjeta {{
      background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(250,245,255,0.96) 100%);
    }}

    .reveal .cancion .contenido {{
      font-size: 0.88em;
      line-height: 1.25;
    }}

    .reveal .cancion .contenido br {{
      display: block;
      content: "";
      margin-bottom: 0.05em;
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
      .reveal .slides section .slide-wrapper {{
        height: 100vh;
      }}
      .reveal .logo-lema {{
        position: fixed;
        bottom: 20px;
        right: 30px;
      }}
      .slide-wrapper:has(.ilustracion) .tarjeta {{
        margin-right: 340px;
      }}
      .reveal .tarjeta {{
        margin: 30px 40px;
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
  <img class="logo-lema" src="assets/lema_somos_uno.jpg" alt="Somos uno" style="display:none;">
  <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/reveal.js"></script>
  <script>
    Reveal.initialize({{
      hash: true,
      slideNumber: 'c/t',
      transition: 'slide',
      width: 1280,
      height: 960,
      center: true,
      margin: 0.04,
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
        contenido = self._apply_bold_html(contenido)
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

        clase = f"{tipo} cancion" if tipo in ("entrada", "gloria", "aleluya", "ofertorio", "santo", "padre_nuestro", "paz", "comunion", "maria", "despedida") else tipo
        html = f'<section class="{clase}" data-transition="fade">\n'
        html += f'  <div class="slide-wrapper">\n'

        if imagen:
            html += f'    <img class="ilustracion" src="{imagen}" alt="ilustración">\n'

        html += f'    <div class="tarjeta">\n{inner}    </div>\n'
        html += f'    <img class="logo-lema" src="{lema_img}" alt="Somos uno">\n'
        html += f'  </div>\n'
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
    def _apply_bold_html(self, text: str) -> str:
        """Convierte **texto** en <strong>texto</strong> para HTML."""
        import re
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


    # ------------------------------------------------------------------
    # PPTX con estilo litúrgico mejorado (4:3, mismo contenido que HTML)
    # ------------------------------------------------------------------

    def _render_pptx(self, data: Dict[str, Any], pptx_path: Path, assets_dir: Path):
        """Genera PPTX 4:3 desde el mismo JSON intermediario que el HTML."""
        from pptx.enum.shapes import MSO_SHAPE

        prs = Presentation()
        prs.slide_width = Inches(SLIDE_WIDTH_INCHES)
        prs.slide_height = Inches(SLIDE_HEIGHT_INCHES)
        blank_layout = prs.slide_layouts[6]

        color = COLORES_LITURGICOS.get(data["meta"]["color_liturgico"].lower(), COLORES_LITURGICOS["verde"])
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
                "entrada", "gloria", "aleluya", "ofertorio", "santo", "padre_nuestro", "paz", "comunion", "maria", "despedida"
            )

            fill = slide.background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(*primary) if is_portada else RGBColor(*bg_light)

            # Barra superior
            bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(SLIDE_WIDTH_INCHES), Inches(0.12))
            bar.fill.solid()
            bar.fill.fore_color.rgb = RGBColor(*primary)
            bar.line.fill.background()

            # Logo lema
            if lema_img_path.exists():
                try:
                    slide.shapes.add_picture(str(lema_img_path), Inches(0.4), Inches(SLIDE_HEIGHT_INCHES - 0.95), height=Inches(0.75))
                except Exception:
                    pass

            # Ilustración
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

            # Tarjeta de contenido
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

            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, card_left, card_top, card_width, card_height)
            card.fill.solid()
            card.fill.fore_color.rgb = RGBColor(255, 255, 255)
            card.line.color.rgb = RGBColor(221, 214, 254)
            card.line.width = Pt(1)
            if hasattr(card, "adjustments"):
                try:
                    card.adjustments[0] = 0.08
                except Exception:
                    pass

            # Línea inferior acento
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

            # Caja de texto
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
            tf.auto_size = None  # no auto-shrink

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

                # Aplicar negrita a segmentos marcados con **texto**
                self._add_formatted_run(p, para_text, is_cancion, is_portada, i, slide_data, primary)

    def _add_formatted_run(
        self,
        p,
        para_text: str,
        is_cancion: bool,
        is_portada: bool,
        para_index: int,
        slide_data: Dict[str, Any],
        primary_rgb: Tuple[int, int, int],
    ):
        """Añade el texto del párrafo respetando marcadores **negrita**."""
        from pptx.dml.color import RGBColor

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

        # Segmentar por **bold**
        import re
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

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # ------------------------------------------------------------------
    # PDF vía playwright (4:3)
    # ------------------------------------------------------------------

    def _render_pdf(self, html_path: Path, pdf_path: Path):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1024, "height": 768})
                page.goto(f"file://{html_path}")
                page.wait_for_timeout(1000)
                page.pdf(path=str(pdf_path), width="10in", height="7.5in", print_background=True)
                browser.close()
        except Exception as exc:
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
