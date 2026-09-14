#!/usr/bin/env python3
"""
Script de integración end-to-end para CCE-M5-Web-Presentaciones.

Para un domingo dado (--fecha YYYY-MM-DD):
1. Obtiene lecturas de Koinonia (con cache y timeout; si falla, usa mock/parcial).
2. Si se provee --config, usa la asignación manual de canciones; si no, usa
   src.matching_engine para proponer canciones para los 12 momentos litúrgicos.
3. Genera la presentación PPTX para fieles.
4. Genera la hoja PDF para músicos con acordes.
5. Registra el resultado en SQLite (tabla presentaciones).
6. Imprime un resumen claro.

Uso:
    python scripts/generar_semana.py --fecha 2026-09-13
    python scripts/generar_semana.py --fecha 2026-09-13 --config config_manual.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Asegurar que src/ es importable cuando se ejecuta desde el repo raíz.
PROJECT_DIR = Path(__file__).parent.parent.resolve()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.db_manager import DB_PATH, get_connection
from src.generators.pdf_musicos import CancionNoEncontradaError, generar_hoja_musicos

logger = logging.getLogger("generar_semana")

OUTPUT_DIR = PROJECT_DIR / "presentaciones"
TEMPLATE_PATH = PROJECT_DIR / "data" / "templates" / "274_Domingo_21_06_2026.pptx"

MOMENTOS_ES: List[str] = [
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

MOMENTOS_KEY: List[str] = [
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


# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------

def configurar_logging(nivel: int = logging.INFO) -> None:
    """Configura logging uniforme para consola."""
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


# ---------------------------------------------------------------------------
# Utilidades de fechas
# ---------------------------------------------------------------------------

def normalizar_domingo(fecha_str: str) -> str:
    """Devuelve el domingo de la semana correspondiente a la fecha recibida."""
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"--fecha debe ser YYYY-MM-DD: {fecha_str}") from exc
    dias_hasta_domingo = (6 - fecha.weekday()) % 7
    domingo = fecha + timedelta(days=dias_hasta_domingo)
    return domingo.isoformat()


# ---------------------------------------------------------------------------
# Lecturas: Koinonia con fallback a mock/parcial
# ---------------------------------------------------------------------------

def obtener_lecturas(
    fecha_domingo: str,
    timeout: int = 30,
    usar_cache: bool = True,
) -> Dict[str, Any]:
    """
    Obtiene lecturas de Koinonia. Si falla la red, usa mock del cancionero.

    Args:
        fecha_domingo: Fecha ISO del domingo (YYYY-MM-DD).
        timeout: Segundos máximo para la petición HTTP.
        usar_cache: Si es True, utiliza el cache SQLite del scraper.

    Returns:
        Diccionario con datos de lecturas (compatible con tabla lecturas).
    """
    try:
        from src.scrapers.koinonia_scraper import KoinoniaScraper

        scraper = KoinoniaScraper()
        if not usar_cache:
            scraper.client.session.cache.clear()
        fecha_dt = datetime.strptime(fecha_domingo, "%Y-%m-%d")
        lecturas = scraper.obtener_lecturas(fecha_dt)
        if lecturas:
            scraper.guardar_en_db(lecturas)
            logger.info("Lecturas de Koinonia obtenidas para %s", fecha_domingo)
            return lecturas
        logger.warning("Koinonia no devolvió datos para %s; se usará mock", fecha_domingo)
    except Exception as exc:
        logger.warning("Error al consultar Koinonia para %s: %s", fecha_domingo, exc)

    # Fallback a Ciudad Redonda
    try:
        from src.scrapers.ciudadredonda_scraper import obtener_lecturas_ciudadredonda
        
        lecturas_cr = obtener_lecturas_ciudadredonda(fecha_domingo)
        if lecturas_cr:
            logger.info("Lecturas de Ciudad Redonda obtenidas para %s", fecha_domingo)
            return lecturas_cr
        logger.warning("Ciudad Redonda no devolvió datos para %s; se usará mock", fecha_domingo)
    except Exception as exc_cr:
        logger.warning("Error al consultar Ciudad Redonda para %s: %s", fecha_domingo, exc_cr)

    # Fallback a mock (persistimos en BD para permitir matching posterior)
    try:
        from src.scrapers.koinonia_mock import generar_mock_aleatorio
        from src.scrapers.koinonia_scraper import KoinoniaRepository

        codigo = fecha_domingo.replace("-", "")
        mock = generar_mock_aleatorio(codigo)
        mock["fecha"] = fecha_domingo
        try:
            KoinoniaRepository().guardar(mock)
        except Exception as exc_guardar:
            logger.warning("No se pudo guardar mock en BD: %s", exc_guardar)
        logger.warning("Usando mock de lecturas para %s", fecha_domingo)
        return mock
    except Exception as exc:
        logger.error("No se pudo generar mock de lecturas: %s", exc)
        return _lecturas_vacias(fecha_domingo)


def _lecturas_vacias(fecha_domingo: str) -> Dict[str, Any]:
    """Devuelve un diccionario de lecturas mínimo para no romper el flujo."""
    return {
        "fecha": fecha_domingo,
        "celebracion": f"Celebración del Domingo {fecha_domingo}",
        "domingo": "Domingo",
        "temporada": "ordinario",
        "ciclo": "C",
        "color_liturgico": "verde",
        "primera_lectura_cita": "",
        "primera_lectura_texto": "",
        "salmo_cita": "",
        "salmo_antifona": "",
        "salmo_texto": "",
        "segunda_lectura_cita": "",
        "segunda_lectura_texto": "",
        "evangelio_cita": "",
        "evangelio_texto": "",
        "fuente": "parcial",
    }


def leer_lectura_id(fecha_domingo: str) -> Optional[int]:
    """Lee el id de la fila lecturas correspondiente a la fecha."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT id FROM lecturas WHERE fecha = ? ORDER BY id DESC LIMIT 1",
                (fecha_domingo,),
            ).fetchone()
            return row["id"] if row else None
    except sqlite3.Error as exc:
        logger.warning("No se pudo leer lectura_id: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Matching / asignación manual de canciones
# ---------------------------------------------------------------------------

def cargar_config_manual(path: Path) -> Dict[str, Any]:
    """Carga un JSON con asignación manual de canciones por momento."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise ValueError(f"No se pudo leer config manual {path}: {exc}") from exc


def _resolver_cancion_id(
    conn: sqlite3.Connection,
    valor: Any,
) -> Optional[int]:
    """Resuelve un identificador de canción (int o título) a id de BD."""
    if isinstance(valor, int):
        return valor
    if isinstance(valor, str) and valor.isdigit():
        return int(valor)
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM canciones WHERE titulo LIKE ? LIMIT 1",
        (f"%{valor}%",),
    )
    row = cur.fetchone()
    return row["id"] if row else None


DEFAULT_ASIGNACION: Dict[str, int] = {
    "entrada": 8,      # Preparad el camino
    "perdon": 2,       # A tu amparo
    "gloria": 9,       # Gloria te damos
    "salmo": 3,        # Aquí estoy, Señor (Salmo 39)
    "aleluya": 4,      # Cantad con gozo
    "ofertorio": 6,    # Hoy como ayer
    "santo": 9,        # Gloria te damos
    "padre_nuestro": 5,# El Espíritu del Señor
    "paz": 6,          # Hoy como ayer
    "comunion": 7,     # María, música de Dios
    "maria": 7,        # María, música de Dios
    "despedida": 8,    # Preparad el camino
}


def proponer_canciones_matching(
    lectura_id: int,
    limite_por_momento: int = 5,
) -> Dict[str, int]:
    """
    Usa src.matching_engine para proponer canciones para cada momento.

    Args:
        lectura_id: id de la lectura en la tabla lecturas.
        limite_por_momento: número de candidatos que se piden al motor.

    Returns:
        Diccionario {momento_key: cancion_id} con una canción por momento.
    """
    from src.matching_engine import MatchingEngine

    engine = MatchingEngine(str(DB_PATH))
    propuestas: Dict[str, int] = {}

    for momento_es, momento_key in zip(MOMENTOS_ES, MOMENTOS_KEY):
        try:
            matches = engine.encontrar_canciones_para_lectura(
                lectura_id,
                limite=limite_por_momento,
                score_minimo=0.0,
            )
            if not matches:
                continue

            # Priorizar canciones cuyo título sugiera el momento litúrgico.
            seleccionada = None
            for match in matches:
                titulo = (match.get("titulo", "") or "").lower()
                if momento_key.replace("_", " ") in titulo or (
                    momento_es.lower() in titulo
                ):
                    seleccionada = match
                    break
            if seleccionada is None:
                seleccionada = matches[0]

            cancion_id = seleccionada.get("cancion_id") or seleccionada.get("id")
            if cancion_id:
                propuestas[momento_key] = int(cancion_id)
        except Exception as exc:
            logger.warning("Matching falló para '%s': %s", momento_key, exc)

    # Fallback: asegurar que todos los momentos tengan al menos una canción.
    for key in MOMENTOS_KEY:
        if key not in propuestas and key in DEFAULT_ASIGNACION:
            propuestas[key] = DEFAULT_ASIGNACION[key]

    return propuestas


def construir_asignacion_canciones(
    config_manual: Optional[Dict[str, Any]],
    fecha_domingo: str,
) -> Dict[str, int]:
    """
    Construye el diccionario final {momento_key: cancion_id}.

    - Si config_manual tiene asignaciones, las traduce a ids de BD.
    - Los momentos no asignados se completan con el motor de matching.
    """
    with get_connection() as conn:
        asignacion: Dict[str, int] = {}

        if config_manual:
            for momento, valor in config_manual.items():
                key = MOMENTO_A_KEY.get(momento, momento.lower().replace(" ", "_"))
                cancion_id = _resolver_cancion_id(conn, valor)
                if cancion_id:
                    asignacion[key] = cancion_id
                else:
                    logger.warning(
                        "Config manual: no se encontró canción '%s' para '%s'",
                        valor,
                        momento,
                    )

        lectura_id = leer_lectura_id(fecha_domingo)
        if lectura_id is None:
            logger.warning("No hay lectura_id en BD; no se puede ejecutar matching")
            return asignacion

        faltantes = [k for k in MOMENTOS_KEY if k not in asignacion]
        if faltantes:
            propuestas = proponer_canciones_matching(lectura_id)
            for key in faltantes:
                if key in propuestas:
                    asignacion[key] = propuestas[key]

        return asignacion


def nombre_canciones(
    conn: sqlite3.Connection,
    asignacion: Dict[str, int],
) -> Dict[str, str]:
    """Devuelve {momento_key: titulo} para una asignación de ids."""
    ids = [cid for cid in asignacion.values() if isinstance(cid, int) and cid > 0]
    nombres: Dict[int, str] = {}
    if ids:
        placeholders = ",".join("?" * len(ids))
        cur = conn.cursor()
        cur.execute(
            f"SELECT id, titulo FROM canciones WHERE id IN ({placeholders})",
            ids,
        )
        nombres = {row["id"]: row["titulo"] for row in cur.fetchall()}

    return {k: nombres.get(v, f"id={v}") for k, v in asignacion.items()}


# ---------------------------------------------------------------------------
# Generación PPTX
# ---------------------------------------------------------------------------

def generar_pptx(
    fecha_domingo: str,
    lectura_id: int,
    canciones_ids: Dict[str, int],
) -> Optional[Path]:
    """
    Genera la presentación PPTX para fieles.

    - Intenta usar src.generators.presentacion_fieles.GeneradorPPTX.
    - Si falla la importación o la generación, genera un PPTX mínimo con
      python-pptx usando el template real descargado del NAS.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{fecha_domingo}_celebracion.pptx"

    try:
        from src.generators.presentacion_master import GeneradorPPTXMaster

        gen = GeneradorPPTX(
            db_path=str(DB_PATH),
            template_path=str(TEMPLATE_PATH),
            output_dir=str(OUTPUT_DIR),
        )
        ruta = gen.generar_presentacion(fecha_domingo, lectura_id, canciones_ids)
        if ruta:
            logger.info("PPTX generado con presentacion_fieles: %s", ruta)
            return Path(ruta)
    except Exception as exc:
        logger.warning("Generador presentacion_fieles falló: %s", exc)

    # Fallback: PPTX mínimo con template real.
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        from pptx.util import Inches, Pt

        prs = Presentation(str(TEMPLATE_PATH))

        # Diapositiva resumen con asignación.
        blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
        slide = prs.slides.add_slide(blank_layout)
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0x4C, 0xAF, 0x50)

        tb = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.5), Inches(12.33), Inches(6.5)
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"Celebración del Domingo\n{fecha_domingo}"
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = PP_ALIGN.CENTER

        # Añadir diapositivas por cada canción asignada.
        with get_connection() as conn:
            nombres = nombre_canciones(conn, canciones_ids)
        for momento_key, titulo in nombres.items():
            slide = prs.slides.add_slide(blank_layout)
            tb = slide.shapes.add_textbox(
                Inches(0.5), Inches(0.5), Inches(12.33), Inches(6.5)
            )
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = f"{momento_key.upper()}\n{titulo}"
            p.font.size = Pt(36)
            p.font.bold = True
            p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            p.alignment = PP_ALIGN.CENTER

        prs.save(str(output_path))
        logger.info("PPTX mínimo generado con template: %s", output_path)
        return output_path
    except Exception as exc:
        logger.error("No se pudo generar PPTX ni siquiera de forma mínima: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Generación PDF músicos
# ---------------------------------------------------------------------------

def generar_pdf_musicos(
    fecha_domingo: str,
    canciones_ids: Dict[str, int],
    celebracion: str,
    notas: Optional[List[str]] = None,
) -> Optional[Path]:
    """Genera la hoja de músicos en PDF usando src.generators.pdf_musicos."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{fecha_domingo}_hoja_musicos.pdf"

    # El generador espera claves con espacios como en MOMENTOS_ES.
    canciones_por_momento: Dict[str, int] = {}
    for es, key in zip(MOMENTOS_ES, MOMENTOS_KEY):
        if key in canciones_ids:
            canciones_por_momento[es] = canciones_ids[key]

    if not canciones_por_momento:
        logger.warning("No hay canciones asignadas; PDF de músicos tendrá portada vacía")

    try:
        ruta = generar_hoja_musicos(
            fecha_domingo=fecha_domingo,
            canciones_por_momento=canciones_por_momento,
            notas=notas,
            celebracion=celebracion,
            output_path=str(output_path),
        )
        logger.info("PDF de músicos generado: %s", ruta)
        return Path(ruta)
    except CancionNoEncontradaError as exc:
        logger.error("Canción no encontrada al generar PDF: %s", exc)
        return None
    except Exception as exc:
        logger.error("Error generando PDF de músicos: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Registro en SQLite
# ---------------------------------------------------------------------------

def registrar_presentacion(
    fecha_domingo: str,
    lectura_id: Optional[int],
    canciones_ids: Dict[str, int],
    pptx_path: Optional[Path],
    pdf_path: Optional[Path],
    lecturas_json: str,
    notas: Optional[List[str]] = None,
) -> Optional[int]:
    """Inserta o actualiza una fila en la tabla presentaciones."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS presentaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_domingo DATE NOT NULL,
                    lectura_id INTEGER,
                    canciones_json TEXT,
                    evento_especial TEXT,
                    ruta_pptx TEXT,
                    ruta_pdf_fieles TEXT,
                    ruta_pdf_musicos TEXT,
                    ruta_web TEXT,
                    estado TEXT DEFAULT 'borrador',
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lectura_id) REFERENCES lecturas(id)
                )
                """
            )

            # Schema extendido: añadimos columnas si no existen (compatibilidad).
            columnas_existentes = {
                row["name"]
                for row in cur.execute("PRAGMA table_info(presentaciones)").fetchall()
            }
            for col in ["lectura_json", "notas", "creado_en"]:
                if col not in columnas_existentes:
                    tipo = "TEXT"
                    if col == "creado_en":
                        tipo = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                    cur.execute(f"ALTER TABLE presentaciones ADD COLUMN {col} {tipo}")

            canciones_json = json.dumps(canciones_ids, ensure_ascii=False, sort_keys=True)
            notas_texto = "\n".join(notas) if notas else ""

            cur.execute(
                """
                INSERT INTO presentaciones (
                    fecha_domingo, lectura_id, canciones_json, notas,
                    lectura_json, ruta_pptx, ruta_pdf_musicos, estado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fecha_domingo,
                    lectura_id,
                    canciones_json,
                    notas_texto,
                    lecturas_json,
                    str(pptx_path) if pptx_path else None,
                    str(pdf_path) if pdf_path else None,
                    "generado",
                ),
            )
            conn.commit()
            presentacion_id = cur.lastrowid
            logger.info("Presentación registrada con id=%s", presentacion_id)
            return presentacion_id
    except sqlite3.Error as exc:
        logger.error("Error al registrar presentación en BD: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------

@dataclass
class ResultadoGeneracion:
    """Resultado del flujo end-to-end."""

    fecha_domingo: str
    lectura_id: Optional[int]
    presentacion_id: Optional[int]
    pptx_path: Optional[Path]
    pdf_path: Optional[Path]
    canciones: Dict[str, str] = field(default_factory=dict)
    notas: List[str] = field(default_factory=list)

    def imprimir_resumen(self) -> None:
        """Imprime en consola un resumen legible del resultado."""
        print("\n" + "=" * 60)
        print(f"Resumen generación semana {self.fecha_domingo}")
        print("=" * 60)
        print(f"Lectura ID:    {self.lectura_id or 'N/A'}")
        print(f"Presentación ID: {self.presentacion_id or 'N/A'}")
        print(f"PPTX fieles:   {self.pptx_path or 'NO GENERADO'}")
        print(f"PDF músicos:   {self.pdf_path or 'NO GENERADO'}")
        print("\nCanciones asignadas:")
        for es, key in zip(MOMENTOS_ES, MOMENTOS_KEY):
            titulo = self.canciones.get(key, "(sin asignar)")
            print(f"  - {es:<18} {titulo}")
        if self.notas:
            print("\nNotas:")
            for nota in self.notas:
                print(f"  * {nota}")
        print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Punto de entrada del script."""
    parser = argparse.ArgumentParser(
        description="Genera presentaciones y hoja de músicos para un domingo.",
    )
    parser.add_argument(
        "--fecha",
        required=True,
        help="Fecha del domingo en formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Ruta a JSON con asignación manual de canciones por momento.",
    )
    parser.add_argument(
        "--notas",
        type=str,
        default=None,
        help="Notas adicionales separadas por '|'.",
    )
    parser.add_argument(
        "--limite-matching",
        type=int,
        default=5,
        help="Número de candidatos por momento para el motor de matching.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout en segundos para peticiones a Koinonia.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Fuerza petición fresca a Koinonia (ignora cache).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Activa salida detallada de debug.",
    )

    args = parser.parse_args(argv)
    configurar_logging(logging.DEBUG if args.verbose else logging.INFO)

    try:
        fecha_domingo = normalizar_domingo(args.fecha)
    except ValueError as exc:
        logger.error(str(exc))
        return 2

    notas: List[str] = []
    if args.notas:
        notas = [n.strip() for n in args.notas.split("|") if n.strip()]

    config_manual: Optional[Dict[str, Any]] = None
    if args.config:
        config_manual = cargar_config_manual(args.config)

    logger.info("Iniciando generación end-to-end para %s", fecha_domingo)

    # 1. Lecturas
    lecturas = obtener_lecturas(
        fecha_domingo,
        timeout=args.timeout,
        usar_cache=not args.no_cache,
    )
    lectura_id = leer_lectura_id(fecha_domingo)
    lecturas_json = json.dumps(lecturas, ensure_ascii=False, sort_keys=True)

    if lecturas.get("fuente") in {"parcial", "mock"}:
        notas.append(f"Lecturas de origen {lecturas.get('fuente')}")

    # 2. Asignación de canciones
    canciones_ids = construir_asignacion_canciones(config_manual, fecha_domingo)

    # 3. PPTX
    pptx_path = generar_pptx(fecha_domingo, lectura_id or -1, canciones_ids)

    # 4. PDF músicos
    celebracion = lecturas.get("celebracion", f"Celebración del Domingo {fecha_domingo}")
    pdf_path = generar_pdf_musicos(
        fecha_domingo,
        canciones_ids,
        celebracion,
        notas=notas,
    )

    # 5. Registrar en BD
    presentacion_id = registrar_presentacion(
        fecha_domingo=fecha_domingo,
        lectura_id=lectura_id,
        canciones_ids=canciones_ids,
        pptx_path=pptx_path,
        pdf_path=pdf_path,
        lecturas_json=lecturas_json,
        notas=notas,
    )

    # Nombres para resumen
    with get_connection() as conn:
        canciones_nombres = nombre_canciones(conn, canciones_ids)

    resultado = ResultadoGeneracion(
        fecha_domingo=fecha_domingo,
        lectura_id=lectura_id,
        presentacion_id=presentacion_id,
        pptx_path=pptx_path,
        pdf_path=pdf_path,
        canciones=canciones_nombres,
        notas=notas,
    )
    resultado.imprimir_resumen()

    # Código de salida: éxito si al menos PPTX o PDF se generaron.
    exit_code = 0 if (pptx_path or pdf_path) else 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
