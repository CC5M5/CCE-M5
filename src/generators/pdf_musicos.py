#!/usr/bin/env python3
"""
Generador de PDF para músicos del Cancionero Escolapio CCE M5.

Produce una hoja A4 vertical con las canciones seleccionadas para los 12
momentos litúrgicos, mostrando los acordes posicionados exactamente sobre la
letra mediante una fuente monoespaciada (Courier New).

Requisitos técnicos:
- fpdf2 con fuentes Unicode incrustadas.
- A4 vertical, márgenes: 2cm arriba/abajo, 2.5cm izquierda, 2cm derecha.
- Acordes: Courier New Bold 11pt negro.
- Letra: Courier New 12pt negro (monoespaciada) para garantizar que la
  posición de carácter calculada por el parser se corresponda milimétrica y
  visualmente con la letra renderizada.
- Encabezado "CCE M5 — [Fecha]" y pie con número de página.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from src.parsers.acordes_parser_v3 import AcordesParser, LineaCancion, limpiar_texto_cancion

logger = logging.getLogger(__name__)

# Reducir el ruido del subconjunto de fuentes que genera fpdf2/fonttools.
logging.getLogger("fontTools").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Constantes de diseño
# ---------------------------------------------------------------------------

PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0
MARGIN_TOP_MM = 20.0
MARGIN_BOTTOM_MM = 20.0
MARGIN_LEFT_MM = 25.0
MARGIN_RIGHT_MM = 20.0
USABLE_WIDTH_MM = PAGE_WIDTH_MM - MARGIN_LEFT_MM - MARGIN_RIGHT_MM

FONT_ACORDES = "CourierNew"
# Decisión de diseño: usamos la misma fuente monoespaciada para letra y
# acordes.  El parser posiciona los acordes por índice de carácter, por lo que
# el ancho fijo de Courier New garantiza alineación exacta sin necesidad de
# recalcular offsets con get_string_width().  Alternativa: mantener Times
# New Roman para la letra y calcular x = ancho_real(letra[:posicion]); eso
# es más fiel estéticamente pero depende de normalizar NBSP y de que la fuente
# proporcional no desplace acordes complejos.  Para una hoja de músicos la
# prioridad es la precisión de la posición, por eso se opta por Courier New.
FONT_LETRA = "CourierNew"
SIZE_ACORDES_PT = 11
SIZE_LETRA_PT = 12
SIZE_HEADER_PT = 10
SIZE_FOOTER_PT = 10
SIZE_TITULO_PT = 16
SIZE_SUBTITULO_PT = 12
SIZE_MOMENTO_PT = 12

COLOR_NEGRO = (0, 0, 0)

MOMENTOS_ORDEN: List[str] = [
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

# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------


class PDFMusicosError(Exception):
    """Base para errores del generador de PDF de músicos."""


class CancionNoEncontradaError(PDFMusicosError):
    """Se solicita una canción que no existe en la base de datos."""


class FuenteNoDisponibleError(PDFMusicosError):
    """No se encuentran las fuentes necesarias en el sistema."""


# ---------------------------------------------------------------------------
# Resolución de fuentes del sistema
# ---------------------------------------------------------------------------


def _build_font_index() -> Dict[Tuple[str, str], Path]:
    """
    Construye un índice de rutas de fuentes TTF/OTF usando fc-list.

    Sólo se indexan archivos .ttf/.otf porque fpdf2 no soporta Type1/PFB.
    """
    index: Dict[Tuple[str, str], Path] = {}
    try:
        result = subprocess.run(
            ["fc-list", ":", "family", "style", "file"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        logger.warning("fc-list no está disponible; se usarán rutas de respaldo")
        return index

    for line in result.stdout.splitlines():
        match = re.match(
            r"(?P<file>.+?):\s*(?P<family>[^:]+?)(?:\s*:\s*style=(?P<style>.+))?\s*$",
            line,
        )
        if not match:
            continue
        path = Path(match.group("file").strip())
        if path.suffix.lower() not in {".ttf", ".otf"}:
            continue
        family_field = match.group("family").strip()
        style_field = (match.group("style") or "").strip()
        families = [f.strip().lower() for f in family_field.split(",")]
        styles = [s.strip().lower() for s in style_field.split(",")] if style_field else [""]
        for family in families:
            for style in styles:
                index.setdefault((family, style), path)
            index.setdefault((family, ""), path)
    return index


def _find_font_path(
    family_aliases: Sequence[str],
    style_aliases: Sequence[str],
    index: Optional[Dict[Tuple[str, str], Path]] = None,
) -> Path:
    """Busca la primera ruta de fuente que coincida con los alias dados."""
    idx = index or _build_font_index()
    for family in family_aliases:
        fam = family.lower()
        for style in style_aliases:
            path = idx.get((fam, style.lower()))
            if path is not None:
                return path
    raise FuenteNoDisponibleError(
        f"No se encontró fuente {family_aliases!r} estilo {style_aliases!r}"
    )


# ---------------------------------------------------------------------------
# Formato y utilidades de texto
# ---------------------------------------------------------------------------


def _format_fecha_es(fecha_str: str) -> str:
    """Convierte 'YYYY-MM-DD' a '13 de Septiembre de 2026'."""
    fecha = date.fromisoformat(fecha_str)
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    return f"{fecha.day} de {meses[fecha.month - 1]} de {fecha.year}"


def _default_output_path(fecha_domingo: str) -> Path:
    """Ruta por defecto: presentaciones/YYYY-MM-DD_hoja_musicos.pdf"""
    default_project_dir = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
    project_dir = Path(os.environ.get("CCE_PROJECT_DIR", default_project_dir))
    output_dir = project_dir / "presentaciones"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{fecha_domingo}_hoja_musicos.pdf"


def _sanitizar_texto(texto: Optional[str]) -> str:
    """Limpia caracteres de control no imprimibles."""
    if not texto:
        return ""
    texto = str(texto)
    # Elimina controles ilegales en XML/PDF excepto salto de línea y tabulador.
    texto = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", texto)
    # Normaliza secuencias de espacios no rompibles múltiples a un único espacio.
    texto = re.sub(r"\u00a0+", " ", texto)
    return texto


def _wrap_line(pdf: FPDF, text: str, max_width_mm: float, font_family: str = FONT_LETRA, font_size: int = SIZE_LETRA_PT) -> List[str]:
    """Divide un texto en líneas respetando límites de ancho y palabras.

    Permite especificar la fuente/tamaño usados para medir el texto, ya que
    Courier New (monoespaciada) y Times New Roman (proporcional) tienen
    anchos diferentes.
    """
    pdf.set_font(font_family, "", font_size)
    words = text.split()
    lines: List[str] = []
    line = ""
    for word in words:
        if not word:
            continue
        candidate = f"{line} {word}".strip() if line else word
        if pdf.get_string_width(candidate) <= max_width_mm:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def _titulo_momento(numero: int, nombre: str, titulo_cancion: str, tono: str) -> str:
    """Formatea el encabezado de cada momento litúrgico."""
    return f'{numero}. {nombre.upper()} — "{titulo_cancion}" ({tono})'


# ---------------------------------------------------------------------------
# Modelo de canción cargada
# ---------------------------------------------------------------------------


@dataclass
class CancionCargada:
    id: int
    titulo: str
    tono: str
    texto_original: str
    estructura: List[LineaCancion]


# ---------------------------------------------------------------------------
# Clase PDF personalizada
# ---------------------------------------------------------------------------


class PDFMusicos(FPDF):
    """Documento PDF con encabezado y pie de página fijos."""

    def __init__(self, fecha_domingo: str) -> None:
        super().__init__("P", "mm", "A4")
        self.fecha_domingo = fecha_domingo
        self.set_auto_page_break(auto=True, margin=MARGIN_BOTTOM_MM)
        self.set_margins(
            left=MARGIN_LEFT_MM,
            top=MARGIN_TOP_MM,
            right=MARGIN_RIGHT_MM,
        )

    def header(self) -> None:
        self.set_font(FONT_LETRA, "", SIZE_HEADER_PT)
        self.set_text_color(*COLOR_NEGRO)
        self.cell(
            0,
            10,
            f"CCE M5 — {self.fecha_domingo}",
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font(FONT_LETRA, "", SIZE_FOOTER_PT)
        self.set_text_color(*COLOR_NEGRO)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")


# ---------------------------------------------------------------------------
# Renderizado de bloques de canción
# ---------------------------------------------------------------------------


class RenderizadorCancion:
    """Renderiza una canción parseada dentro de un documento PDF."""

    def __init__(self, pdf: PDFMusicos) -> None:
        self.pdf = pdf
        self.chord_char_width_mm = self._chord_char_width()
        self.usable_width = USABLE_WIDTH_MM

    def _chord_char_width(self) -> float:
        # Medimos con el tamaño de letra, no con el de acordes, porque los
        # acordes se posicionan según la columna de letra subyacente.
        self.pdf.set_font(FONT_LETRA, "", SIZE_LETRA_PT)
        return self.pdf.get_string_width("M")

    def _check_page_break(self, needed_height: float) -> None:
        """Fuerza salto de página si el bloque no cabe en el espacio restante."""
        y = self.pdf.get_y()
        limit = self.pdf.h - self.pdf.b_margin
        if y + needed_height > limit:
            self.pdf.add_page()

    def _render_acordes_linea(
        self,
        acordes: Sequence[Any],
        base_y: float,
    ) -> None:
        """Dibuja los acordes en sus posiciones exactas de carácter."""
        self.pdf.set_font(FONT_ACORDES, "B", SIZE_ACORDES_PT)
        self.pdf.set_text_color(*COLOR_NEGRO)
        for acorde_info in acordes:
            x = MARGIN_LEFT_MM + acorde_info.posicion * self.chord_char_width_mm
            # Si el acorde excede el margen derecho se omite para no romper el
            # diseño; esto sólo ocurre con líneas de acordes anormalmente largas.
            if x > MARGIN_LEFT_MM + self.usable_width:
                logger.debug(
                    "Acorde '%s' en posición %s omite por exceder ancho",
                    acorde_info.acorde,
                    acorde_info.posicion,
                )
                continue
            self.pdf.set_xy(x, base_y)
            self.pdf.cell(0, 4, acorde_info.acorde)

    def _render_texto_letra(
        self,
        texto: str,
        base_y: float,
    ) -> float:
        """Escribe la letra justo debajo de la línea de acordes.

        Importante: la letra se imprime con la misma fuente monoespaciada que
        se usa para calcular la posición de los acordes (ver constantes de
        diseño).  Así el índice de carácter del parser se traduce directamente
        a milímetros sin desplazamientos.
        """
        self.pdf.set_font(FONT_LETRA, "", SIZE_LETRA_PT)
        self.pdf.set_text_color(*COLOR_NEGRO)
        self.pdf.set_xy(MARGIN_LEFT_MM, base_y)
        self.pdf.multi_cell(
            w=self.usable_width,
            h=4,
            text=texto,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        return self.pdf.get_y()

    def render_bloque_acordes_letra(
        self,
        linea: LineaCancion,
    ) -> None:
        """Renderiza un bloque acordes + letra, con salto de página si es necesario."""
        # La letra se imprime literal tal cual la devuelve el parser (Courier
        # New monoespaciado), por lo que no debe envolverse como texto libre.
        # Si una línea de letra es demasiado larga, cortamos por el ancho
        # disponible sin alterar la alineación de los acordes de esa línea.
        self.pdf.set_font(FONT_LETRA, "", SIZE_LETRA_PT)
        max_chars = int(self.usable_width // self.chord_char_width_mm)
        letra_cortada = linea.letra[:max_chars].rstrip()
        needed = 4 + 4 + 1  # acordes + letra + separación
        self._check_page_break(needed)

        y = self.pdf.get_y()
        self._render_acordes_linea(linea.acordes, y)
        final_y = self._render_texto_letra(letra_cortada, y + 4)
        self.pdf.set_y(final_y + 1)

    def render_linea_suelta(
        self,
        linea: LineaCancion,
    ) -> None:
        """Renderiza líneas sueltas de letra, acordes o secciones."""
        if linea.tipo == "letra":
            texto = _sanitizar_texto(linea.letra)
            if not texto.strip():
                return
            self.pdf.set_font(FONT_LETRA, "", SIZE_LETRA_PT)
            self.pdf.set_text_color(*COLOR_NEGRO)
            wrapped = _wrap_line(self.pdf, texto, self.usable_width)
            self._check_page_break(len(wrapped) * 4 + 1)
            self.pdf.set_x(MARGIN_LEFT_MM)
            self.pdf.multi_cell(
                w=self.usable_width,
                h=4,
                text=texto,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            self.pdf.ln(1)

        elif linea.tipo == "acordes":
            acordes = linea.acordes
            if not acordes:
                return
            self._check_page_break(6)
            y = self.pdf.get_y()
            self._render_acordes_linea(acordes, y)
            self.pdf.set_y(y + 6)

        elif linea.tipo == "sección":
            texto = _sanitizar_texto(linea.texto).strip("[]")
            if not texto:
                return
            self.pdf.set_font(FONT_LETRA, "B", SIZE_LETRA_PT)
            self.pdf.set_text_color(*COLOR_NEGRO)
            self._check_page_break(8)
            self.pdf.set_x(MARGIN_LEFT_MM)
            self.pdf.cell(
                0,
                7,
                texto,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            self.pdf.ln(1)

        elif linea.tipo == "vacía":
            return


# ---------------------------------------------------------------------------
# Carga desde base de datos
# ---------------------------------------------------------------------------


def _cargar_canciones(
    conn: sqlite3.Connection,
    canciones_por_momento: Dict[str, Union[int, str]],
) -> Dict[str, CancionCargada]:
    """
    Carga desde SQLite las canciones indicadas por momento.

    Acepta IDs numéricos o títulos de canción. Lanza CancionNoEncontradaError
    si alguna no existe.
    """
    cursor = conn.cursor()
    ids: List[int] = []
    titulos: List[str] = []
    for valor in canciones_por_momento.values():
        if isinstance(valor, int):
            ids.append(valor)
        else:
            titulos.append(str(valor))

    canciones_por_id: Dict[int, sqlite3.Row] = {}
    canciones_por_titulo: Dict[str, sqlite3.Row] = {}

    if ids:
        placeholders = ",".join("?" * len(ids))
        cursor.execute(
            f"SELECT id, titulo, tono, letra_con_acordes "
            f"FROM canciones WHERE id IN ({placeholders})",
            ids,
        )
        for row in cursor.fetchall():
            canciones_por_id[row["id"]] = row

    if titulos:
        placeholders = ",".join("?" * len(titulos))
        cursor.execute(
            f"SELECT id, titulo, tono, letra_con_acordes "
            f"FROM canciones WHERE titulo IN ({placeholders})",
            titulos,
        )
        for row in cursor.fetchall():
            canciones_por_titulo[row["titulo"]] = row

    parser = AcordesParser()
    resultado: Dict[str, CancionCargada] = {}

    for momento, valor in canciones_por_momento.items():
        row: Optional[sqlite3.Row] = None
        if isinstance(valor, int):
            row = canciones_por_id.get(valor)
        else:
            row = canciones_por_titulo.get(str(valor))

        if row is None:
            logger.error("Canción no encontrada para '%s': %r", momento, valor)
            raise CancionNoEncontradaError(
                f"No se encontró la canción para '{momento}': {valor!r}"
            )

        texto = limpiar_texto_cancion(_sanitizar_texto(row["letra_con_acordes"]))
        estructura = parser.parsear_cancion_completa(texto)
        tono = _sanitizar_texto(row["tono"]) or parser.detectar_tono(estructura)

        resultado[momento] = CancionCargada(
            id=row["id"],
            titulo=_sanitizar_texto(row["titulo"]) or "Canción",
            tono=tono or "—",
            texto_original=texto,
            estructura=estructura,
        )

    return resultado


# ---------------------------------------------------------------------------
# Construcción del documento completo
# ---------------------------------------------------------------------------


def _registrar_fuentes(pdf: PDFMusicos) -> None:
    """Añade al PDF las fuentes necesarias, buscándolas en el sistema."""
    index = _build_font_index()

    courier_regular = _find_font_path(
        ["Courier New", "TeX Gyre Cursor", "Courier"],
        ["Regular", ""],
        index,
    )
    courier_bold = _find_font_path(
        ["Courier New", "TeX Gyre Cursor", "Courier"],
        ["Bold"],
        index,
    )

    # Letra y acordes comparten la familia monoespaciada para mantener la
    # alineación exacta calculada por el parser (posición por carácter).
    # fpdf2 normaliza los nombres de fuente a minúsculas y crea una entrada
    # distinta por cada combinación (familia, estilo).  Evitamos registrar
    # dos veces la misma combinación, lo que generaría un UserWarning.
    existing_keys = {name.lower() for name in pdf.fonts}
    acordes_regular = FONT_ACORDES.lower()
    acordes_bold = (FONT_ACORDES + "B").lower()
    letra_regular = FONT_LETRA.lower()
    letra_bold = (FONT_LETRA + "B").lower()

    if acordes_regular not in existing_keys:
        pdf.add_font(FONT_ACORDES, "", str(courier_regular))
        existing_keys.add(acordes_regular)
    if acordes_bold not in existing_keys:
        pdf.add_font(FONT_ACORDES, "B", str(courier_bold))
        existing_keys.add(acordes_bold)
    if letra_regular not in existing_keys:
        pdf.add_font(FONT_LETRA, "", str(courier_regular))
        existing_keys.add(letra_regular)
    if letra_bold not in existing_keys:
        pdf.add_font(FONT_LETRA, "B", str(courier_bold))
    logger.debug(
        "Fuente monoespaciada registrada: regular=%s bold=%s",
        courier_regular,
        courier_bold,
    )


def _render_portada(
    pdf: PDFMusicos,
    fecha_domingo: str,
    celebracion: str,
    notas: Optional[List[str]],
) -> None:
    """Dibuja título, subtítulo, fecha y notas previas."""
    pdf.add_page()

    # Título principal
    pdf.set_font(FONT_LETRA, "B", SIZE_TITULO_PT)
    pdf.set_text_color(*COLOR_NEGRO)
    pdf.cell(
        0,
        10,
        "COMUNIDAD CRISTIANA ESCOLAPIA MONTEQUINTO",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    # Subtítulo
    pdf.set_font(FONT_LETRA, "", SIZE_SUBTITULO_PT)
    pdf.cell(
        0,
        8,
        f"Hoja de Músicos — {celebracion}",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    # Fecha
    pdf.cell(
        0,
        8,
        _format_fecha_es(fecha_domingo),
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)

    # Separador
    y = pdf.get_y()
    pdf.set_draw_color(*COLOR_NEGRO)
    pdf.line(MARGIN_LEFT_MM, y, PAGE_WIDTH_MM - MARGIN_RIGHT_MM, y)
    pdf.ln(3)

    # Notas previas
    if notas:
        pdf.set_font(FONT_LETRA, "B", SIZE_LETRA_PT)
        pdf.cell(
            0,
            6,
            "NOTAS PREVIAS:",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_font(FONT_LETRA, "", SIZE_LETRA_PT)
        for nota in notas:
            pdf.cell(
                0,
                6,
                f"• {nota}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
        pdf.ln(2)
        y = pdf.get_y()
        pdf.line(MARGIN_LEFT_MM, y, PAGE_WIDTH_MM - MARGIN_RIGHT_MM, y)
        pdf.ln(4)


def _render_cancion(
    pdf: PDFMusicos,
    numero: int,
    nombre_momento: str,
    cancion: CancionCargada,
) -> None:
    """Dibuja la cabecera de momento y el cuerpo de la canción."""
    renderizador = RenderizadorCancion(pdf)

    # Encabezado del momento
    pdf.set_font(FONT_LETRA, "B", SIZE_MOMENTO_PT)
    pdf.set_text_color(*COLOR_NEGRO)
    pdf.set_x(MARGIN_LEFT_MM)
    pdf.cell(
        0,
        7,
        _titulo_momento(numero, nombre_momento, cancion.titulo, cancion.tono),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    # Separador grueso
    y = pdf.get_y() + 1
    pdf.set_draw_color(*COLOR_NEGRO)
    pdf.set_line_width(0.5)
    pdf.line(MARGIN_LEFT_MM, y, PAGE_WIDTH_MM - MARGIN_RIGHT_MM, y)
    pdf.set_line_width(0.2)
    pdf.set_y(y + 2)

    # Si no hay acordes en ninguna línea, mostrar advertencia sutil y la letra
    tiene_acordes = any(
        linea.tipo in ("acordes_letra", "acordes") and linea.acordes
        for linea in cancion.estructura
    )
    if not tiene_acordes:
        pdf.set_font(FONT_LETRA, "I", SIZE_LETRA_PT)
        pdf.set_x(MARGIN_LEFT_MM)
        pdf.cell(
            0,
            6,
            "(Esta canción no tiene acordes registrados)",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(2)

    for linea in cancion.estructura:
        if linea.tipo == "acordes_letra":
            renderizador.render_bloque_acordes_letra(linea)
        elif linea.tipo in ("letra", "acordes", "sección"):
            renderizador.render_linea_suelta(linea)
        # Las líneas vacías ya no generan espacio adicional; el propio
        # renderizado añade los saltos necesarios.

    pdf.ln(2)


def _render_cierre(pdf: PDFMusicos) -> None:
    """Dibuja la línea final con 'FIN DE LA CELEBRACIÓN'."""
    pdf.ln(4)
    y = pdf.get_y()
    pdf.set_draw_color(*COLOR_NEGRO)
    pdf.set_line_width(0.5)
    pdf.line(MARGIN_LEFT_MM, y, PAGE_WIDTH_MM - MARGIN_RIGHT_MM, y)
    pdf.ln(3)

    pdf.set_font(FONT_LETRA, "B", SIZE_SUBTITULO_PT)
    pdf.set_text_color(*COLOR_NEGRO)
    pdf.cell(
        0,
        8,
        "FIN DE LA CELEBRACIÓN",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    y = pdf.get_y() + 1
    pdf.line(MARGIN_LEFT_MM, y, PAGE_WIDTH_MM - MARGIN_RIGHT_MM, y)
    pdf.set_line_width(0.2)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def generar_hoja_musicos(
    fecha_domingo: str,
    canciones_por_momento: Dict[str, Union[int, str]],
    notas: Optional[List[str]] = None,
    celebracion: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Genera el PDF de la hoja de músicos para una celebración.

    Parámetros:
        fecha_domingo: Fecha en formato ISO (YYYY-MM-DD).
        canciones_por_momento: Diccionario {nombre_momento: id_cancion | titulo}.
        notas: Lista de notas previas (tono general, eventos, ensayo, ...).
        celebracion: Nombre de la celebración (ej. 'Domingo XXIV T.O.').
        output_path: Ruta de salida. Si es None, se usa
                     presentaciones/YYYY-MM-DD_hoja_musicos.pdf.

    Retorna:
        Ruta absoluta del PDF generado.

    Lanza:
        CancionNoEncontradaError: si falta alguna canción.
        FuenteNoDisponibleError: si no se encuentran fuentes del sistema.
        PDFMusicosError: para errores inesperados de generación.
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha_domingo):
        raise PDFMusicosError(
            f"fecha_domingo debe tener formato YYYY-MM-DD: {fecha_domingo!r}"
        )

    celebracion_final = celebracion or f"Celebración del Domingo"
    output_path_final = (
        Path(output_path)
        if output_path
        else _default_output_path(fecha_domingo)
    )
    output_path_final.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Generando hoja de músicos para %s en %s",
        fecha_domingo,
        output_path_final,
    )

    try:
        from src.db_manager import get_connection

        with get_connection() as conn:
            canciones = _cargar_canciones(conn, canciones_por_momento)

        pdf = PDFMusicos(fecha_domingo)
        _registrar_fuentes(pdf)
        _render_portada(pdf, fecha_domingo, celebracion_final, notas)

        for numero, nombre_momento in enumerate(MOMENTOS_ORDEN, start=1):
            cancion = canciones.get(nombre_momento)
            if cancion is None:
                logger.warning("Sin canción asignada para '%s'", nombre_momento)
                continue
            _render_cancion(pdf, numero, nombre_momento, cancion)

        _render_cierre(pdf)
        pdf.output(str(output_path_final))

    except (CancionNoEncontradaError, FuenteNoDisponibleError):
        raise
    except sqlite3.Error as exc:
        logger.exception("Error de base de datos al generar hoja de músicos")
        raise PDFMusicosError(f"Error de base de datos: {exc}") from exc
    except Exception as exc:
        logger.exception("Error inesperado al generar hoja de músicos")
        raise PDFMusicosError(f"No se pudo generar el PDF: {exc}") from exc

    logger.info("Hoja de músicos generada: %s", output_path_final.resolve())
    return output_path_final.resolve()


# ---------------------------------------------------------------------------
# Punto de entrada directo (solo para pruebas puntuales)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    raise SystemExit("Usa el script demo para probar el generador.")
