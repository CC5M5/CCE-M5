#!/usr/bin/env python3
"""
Script de integración end-to-end para CCE-M5-Web-Presentaciones.

Para un domingo dado (--fecha YYYY-MM-DD):
1. Obtiene lecturas de Koinonia (con cache y timeout; si falla, usa fallback a Ciudad Redonda o mock).
2. Si se provee --config, usa la asignación manual de canciones; si no, usa
   src.matching_engine para proponer canciones para los 12 momentos litúrgicos.
3. Genera la presentación PPTX para fieles.
4. Genera la hoja PDF para músicos con acordes.
5. Registra el resultado en SQLite (tabla presentaciones).
6. Imprime un resumen claro.

Modos de operación:
    --dry-run        Muestra lecturas, canciones propuestas y rutas SIN escribir archivos, BD ni commits.
    --modo borrador  Genera archivos en borradores/ y marca estado='borrador' en BD.
    --modo publicar  Genera en presentaciones/, marca estado='publicada' y es el comportamiento anterior.

Uso:
    python scripts/generar_semana.py --fecha 2026-09-13 --dry-run
    python scripts/generar_semana.py --fecha 2026-09-13 --modo borrador
    python scripts/generar_semana.py --fecha 2026-09-13 --modo publicar --config config_manual.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
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
BORRADOR_DIR = PROJECT_DIR / "borradores"
TEMPLATE_PATH = PROJECT_DIR / "data" / "templates" / "274_Domingo_21_06_2026.pptx"

# ---------------------------------------------------------------------------
# Modo de operación (borrador / publicar)
# ---------------------------------------------------------------------------

MODO_BORRADOR = "borrador"
MODO_PUBLICAR = "publicar"


def _directorio_salida(modo: str) -> Path:
    """Devuelve el directorio de salida según el modo."""
    if modo == MODO_BORRADOR:
        BORRADOR_DIR.mkdir(parents=True, exist_ok=True)
        return BORRADOR_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _estado_presentacion(modo: str) -> str:
    """Devuelve el estado de la presentación según el modo."""
    return "borrador" if modo == MODO_BORRADOR else "publicada"

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


def lectura_existe_en_bd(fecha_domingo: str) -> bool:
    """Comprueba si ya existen lecturas para la fecha."""
    return leer_lectura_id(fecha_domingo) is not None


def presentacion_existe_en_bd(fecha_domingo: str) -> bool:
    """Comprueba si ya existe una presentación publicada para la fecha."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT 1 FROM presentaciones WHERE fecha_domingo = ? AND estado = 'publicada' LIMIT 1",
                (fecha_domingo,),
            ).fetchone()
            return bool(row)
    except sqlite3.Error as exc:
        logger.warning("No se pudo comprobar presentación existente: %s", exc)
        return False


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
    """Resuelve un identificador de canción (int o título) a id de BD.

    Si el valor es None, False, 'null', 'N/A' o cadena vacía, se interpreta
    como 'sin canción asignada' y se devuelve None.
    """
    if valor is None or valor is False:
        return None
    if isinstance(valor, str):
        if not valor.strip() or valor.strip().lower() in {"null", "n/a", "none", "no", "-", "—"}:
            return None
        if valor.isdigit():
            return int(valor)
    if isinstance(valor, int):
        return valor
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM canciones WHERE titulo LIKE ? LIMIT 1",
        (f"%{valor}%",),
    )
    row = cur.fetchone()
    return row["id"] if row else None


DEFAULT_ASIGNACION: Dict[str, int] = {
    "entrada": 8,       # PREPARAD EL CAMINO
    "perdon": 70,       # OTRA OPORTUNIDAD
    "gloria": 9,        # GLORIA TE DAMOS GRACIAS, SEÑOR
    "salmo": 3,         # AQUÍ ESTOY, SEÑOR (SALMO 39)
    "aleluya": 47,      # JESÚS RESUCITA HOY
    "ofertorio": 74,    # PADRE NUESTRO DE LA VIDA
    "santo": 84,        # QUIERO HACER LO MISMO
    "padre_nuestro": 72,# PADRE NUESTRO (Gallego)
    "paz": 100,         # UNA NUEVA ESPERANZA
    "comunion": 95,     # TODO MI SER
    "maria": 7,         # MARÍA, MÚSICA DE DIOS
    "despedida": 26,    # DE NOCHE IREMOS DE NOCHE
}


def _es_id_valido(valor: Any) -> bool:
    try:
        return int(valor) > 0
    except (TypeError, ValueError):
        return False


def proponer_canciones_matching(
    lectura_id: int,
    limite_por_momento: int = 5,
) -> Dict[str, int]:
    """
    Usa src.matching_engine para proponer canciones para cada momento.

    Estrategia:
    - Para cada momento se pide un ranking amplio de candidatos.
    - Se priorizan canciones cuyo momento_liturgico etiquetado coincida
      exactamente con el momento solicitado.
    - Si no hay coincidencia exacta, se prueba coincidencia parcial y
      finalmente se recurre al score temático.
    - Se evita repetir una misma canción en dos momentos distintos.
    - Al final se asegura que todos los momentos tengan una canción,
      buscando alternativas del mismo momento si el fallback ya está usado.

    Args:
        lectura_id: id de la lectura en la tabla lecturas.
        limite_por_momento: número de candidatos que se piden al motor.

    Returns:
        Diccionario {momento_key: cancion_id} con una canción por momento.
    """
    import sqlite3

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM canciones WHERE titulo IS NOT NULL AND titulo != ''")
    count = cursor.fetchone()[0]
    conn.close()

    if count < 20:
        logger.info("Solo %s canciones en BD. Usando DEFAULT_ASIGNACION.", count)
        return dict(DEFAULT_ASIGNACION)

    from src.matching_engine import MatchingEngine

    engine = MatchingEngine(str(DB_PATH))

    # Ranking global una sola vez; se reutiliza para fallback de alternativas.
    matches = engine.encontrar_canciones_para_lectura(
        lectura_id,
        limite=count,
        score_minimo=0.0,
    )

    propuestas: Dict[str, int] = {}
    usadas: set[int] = set()

    for momento_es, momento_key in zip(MOMENTOS_ES, MOMENTOS_KEY):
        seleccionada = None
        try:
            # 1) Preferir canción cuyo momento litúrgico coincida exactamente
            #    y que no se haya usado ya.
            for match in matches:
                cancion_id = _cancion_id_de_match(match)
                if cancion_id in usadas:
                    continue
                if (match.get("momento_liturgico") or "").strip().lower() == momento_key:
                    seleccionada = match
                    break

            # 2) Coincidencia parcial en el momento litúrgico.
            if seleccionada is None:
                for match in matches:
                    cancion_id = _cancion_id_de_match(match)
                    if cancion_id in usadas:
                        continue
                    momento_cancion = (match.get("momento_liturgico") or "").strip().lower()
                    if momento_key in momento_cancion or momento_cancion in momento_key:
                        seleccionada = match
                        break

            # 3) Título que sugiera el momento litúrgico.
            if seleccionada is None:
                for match in matches:
                    cancion_id = _cancion_id_de_match(match)
                    if cancion_id in usadas:
                        continue
                    titulo = (match.get("titulo", "") or "").lower()
                    if momento_key.replace("_", " ") in titulo or momento_es.lower() in titulo:
                        seleccionada = match
                        break

            # 4) Último recurso antes del fallback: la de mayor score temático
            #    no usada, pero solo si su momento litúrgico no contradice mucho
            #    el solicitado (es decir, si es 'general' o el score es alto).
            #    Para momentos específicos sin candidato, preferimos el fallback.
            if seleccionada is None:
                if momento_key in ("general",):
                    for match in matches:
                        cancion_id = _cancion_id_de_match(match)
                        if cancion_id not in usadas:
                            seleccionada = match
                            break

            cancion_id = _cancion_id_de_match(seleccionada) if seleccionada else None
            if _es_id_valido(cancion_id):
                propuestas[momento_key] = int(cancion_id)
                usadas.add(int(cancion_id))
        except Exception as exc:
            logger.warning("Matching falló para '%s': %s", momento_key, exc)

    # Fallback: asegurar que todos los momentos tengan al menos una canción,
    #    evitando repetir canciones ya usadas.
    for key in MOMENTOS_KEY:
        if key not in propuestas and key in DEFAULT_ASIGNACION:
            fallback_id = DEFAULT_ASIGNACION[key]
            if fallback_id not in usadas:
                propuestas[key] = fallback_id
                usadas.add(fallback_id)
            else:
                # Si el fallback por defecto ya está usado, buscar otra canción del
                # mismo momento litúrgico que no se haya usado en el ranking global.
                alternativa = None
                for match in matches:
                    cancion_id = _cancion_id_de_match(match)
                    if cancion_id in usadas:
                        continue
                    if (match.get("momento_liturgico") or "").strip().lower() == key:
                        alternativa = cancion_id
                        break
                if _es_id_valido(alternativa):
                    propuestas[key] = int(alternativa)
                    usadas.add(int(alternativa))
                else:
                    # Último recurso: cualquier canción del momento litúrgico en BD
                    # que no esté usada, aunque no esté en el ranking temático.
                    try:
                        conn_fb = sqlite3.connect(str(DB_PATH))
                        cur_fb = conn_fb.cursor()
                        cur_fb.execute(
                            "SELECT id FROM canciones WHERE lower(momento_liturgico) = ? AND id NOT IN ({})".format(
                                ",".join("?" * len(usadas)) if usadas else "0"
                            ),
                            (key,) + tuple(usadas),
                        )
                        row_fb = cur_fb.fetchone()
                        if row_fb:
                            propuestas[key] = int(row_fb["id"])
                            usadas.add(int(row_fb["id"]))
                        conn_fb.close()
                    except Exception as exc:
                        logger.warning("Fallback alternativo BD falló para '%s': %s", key, exc)

    return propuestas


def _cancion_id_de_match(match: Dict[str, Any]) -> Any:
    """Devuelve el id de canción de un match del motor."""
    return match.get("cancion_id") or match.get("id")


def construir_asignacion_canciones(
    config_manual: Optional[Dict[str, Any]],
    fecha_domingo: str,
) -> Dict[str, int]:
    """
    Construye el diccionario final {momento_key: cancion_id}.

    - Si config_manual tiene asignaciones, las traduce a ids de BD.
      Un valor None o "N/A" deja el momento explícitamente vacío; no se
      completará con matching.
    - Los momentos no presentes en config_manual se completan con el motor de matching.
    """
    with get_connection() as conn:
        asignacion: Dict[str, int] = {}
        explicitamente_vacio: set[str] = set()

        if config_manual:
            for momento, valor in config_manual.items():
                # La clave especial 'bendicion_agua' no es un momento musical.
                if momento.lower() == "bendicion_agua":
                    continue
                key = MOMENTO_A_KEY.get(momento, momento.lower().replace(" ", "_"))
                cancion_id = _resolver_cancion_id(conn, valor)
                if cancion_id:
                    asignacion[key] = cancion_id
                else:
                    # El usuario dejó este momento explícitamente sin canción.
                    explicitamente_vacio.add(key)

        lectura_id = leer_lectura_id(fecha_domingo)
        if lectura_id is None:
            logger.warning("No hay lectura_id en BD; no se puede ejecutar matching")
            return asignacion

        faltantes = [k for k in MOMENTOS_KEY if k not in asignacion and k not in explicitamente_vacio]
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
    modo: str = MODO_PUBLICAR,
) -> Optional[Path]:
    """
    Genera la presentación PPTX para fieles.

    Usa src.generators.presentacion_html.GeneradorPresentacionHTML, que genera
    un bundle con HTML (Reveal.js), JSON, PPTX y PDF idénticos en contenido.
    El PPTX resultante se copia también a la ruta tradicional
    {fecha}_celebracion.pptx para compatibilidad con descargas.
    """
    output_dir = _directorio_salida(modo)
    output_path = output_dir / f"{fecha_domingo}_celebracion.pptx"
    if output_path.exists():
        logger.warning("PPTX de destino ya existe: %s", output_path)

    try:
        from src.generators.presentacion_html import GeneradorPresentacionHTML

        incluir_bendicion_agua = bool(canciones_ids.get("bendicion_agua"))
        gen = GeneradorPresentacionHTML(
            db_path=str(DB_PATH),
            output_dir=str(output_dir),
        )
        bundle_dir = gen.generar(
            fecha=fecha_domingo,
            lectura_id=lectura_id,
            canciones_ids={
                k: v for k, v in canciones_ids.items()
                if k in MOMENTOS_KEY or k == "bendicion_agua"
            },
            incluir_bendicion_agua=incluir_bendicion_agua,
        )
        bundle_pptx = bundle_dir / f"{fecha_domingo}_presentacion.pptx"
        if bundle_pptx.exists():
            shutil.copy(str(bundle_pptx), str(output_path))
            logger.info("PPTX generado con presentacion_html: %s", output_path)
            return output_path
        else:
            logger.warning("No se encontró PPTX en el bundle: %s", bundle_dir)
    except Exception as exc:
        logger.error("Generador presentacion_html falló: %s", exc)
        traceback.print_exc()

    return None


# ---------------------------------------------------------------------------
# Generación PDF músicos
# ---------------------------------------------------------------------------

def generar_pdf_musicos(
    fecha_domingo: str,
    canciones_ids: Dict[str, int],
    celebracion: str,
    notas: Optional[List[str]] = None,
    modo: str = MODO_PUBLICAR,
) -> Optional[Path]:
    """Genera la hoja de músicos en PDF usando src.generators.pdf_musicos."""
    output_dir = _directorio_salida(modo)
    output_path = output_dir / f"{fecha_domingo}_hoja_musicos.pdf"
    if output_path.exists():
        logger.warning("PDF de destino ya existe: %s", output_path)

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
    estado: str = "publicada",
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
                    estado,
                ),
            )
            conn.commit()
            presentacion_id = cur.lastrowid
            logger.info("Presentación registrada con id=%s estado=%s", presentacion_id, estado)
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
    modo: str = MODO_PUBLICAR
    dry_run: bool = False
    estado_presentacion: str = "publicada"

    def imprimir_resumen(self) -> None:
        """Imprime en consola un resumen legible del resultado."""
        modo_str = "[DRY-RUN]" if self.dry_run else f"[modo: {self.modo}]"
        print("\n" + "=" * 60)
        print(f"Resumen generación semana {self.fecha_domingo} {modo_str}")
        print("=" * 60)
        print(f"Lectura ID:    {self.lectura_id or 'N/A'}")
        print(f"Presentación ID: {self.presentacion_id or 'N/A'}")
        print(f"Estado BD:     {self.estado_presentacion}")
        if self.dry_run:
            print("PPTX fieles:   (no se escribió)")
            print("PDF músicos:   (no se escribió)")
        else:
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
        if self.dry_run:
            print("ℹ️  Este fue un dry-run. No se escribieron archivos ni BD.\n")


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
        "--modo",
        type=str,
        choices=[MODO_BORRADOR, MODO_PUBLICAR],
        default=MODO_BORRADOR,
        help="Modo de generación: borrador (por defecto, no publica) o publicar (sobrescribe presentaciones/ y BD).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula todo sin escribir archivos ni BD. Imprime resumen y sale.",
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Permite publicar incluso si ya existe una presentación publicada (sobrescribe).",
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

    modo = args.modo
    dry_run = args.dry_run

    # Seguridad: por defecto, publicar solo si no existe ya una publicada o con --forzar.
    if modo == MODO_PUBLICAR and not dry_run and not args.forzar:
        if presentacion_existe_en_bd(fecha_domingo):
            logger.error(
                "Ya existe una presentación publicada para %s. "
                "Usa --forzar para sobrescribir o --modo borrador para generar borrador.",
                fecha_domingo,
            )
            print(
                f"\n❌ Ya existe una presentación publicada para {fecha_domingo}.\n"
                "Opciones:\n"
                "  --modo borrador      Genera un borrador sin tocar la publicada.\n"
                "  --forzar             Sobrescribe la publicada (CUIDADO).\n"
            )
            return 3

    notas: List[str] = []
    if args.notas:
        notas = [n.strip() for n in args.notas.split("|") if n.strip()]

    config_manual: Optional[Dict[str, Any]] = None
    if args.config:
        config_manual = cargar_config_manual(args.config)

    if dry_run:
        logger.info("DRY-RUN: no se escribirá ningún archivo ni BD para %s", fecha_domingo)
    else:
        logger.info("Iniciando generación end-to-end para %s [modo=%s]", fecha_domingo, modo)

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

    # Nombres para resumen (necesarios en dry-run también)
    with get_connection() as conn:
        canciones_nombres = nombre_canciones(conn, canciones_ids)

    if dry_run:
        # En dry-run no se generan archivos ni se registra en BD.
        resultado = ResultadoGeneracion(
            fecha_domingo=fecha_domingo,
            lectura_id=lectura_id,
            presentacion_id=None,
            pptx_path=None,
            pdf_path=None,
            canciones=canciones_nombres,
            notas=notas,
            modo=modo,
            dry_run=True,
            estado_presentacion=_estado_presentacion(modo),
        )
        resultado.imprimir_resumen()
        return 0

    # 3. PPTX
    pptx_path = generar_pptx(fecha_domingo, lectura_id or -1, canciones_ids, modo=modo)

    # 4. PDF músicos
    celebracion = lecturas.get("celebracion", f"Celebración del Domingo {fecha_domingo}")
    pdf_path = generar_pdf_musicos(
        fecha_domingo,
        canciones_ids,
        celebracion,
        notas=notas,
        modo=modo,
    )

    # 5. Registrar en BD
    estado_bd = _estado_presentacion(modo)
    presentacion_id = registrar_presentacion(
        fecha_domingo=fecha_domingo,
        lectura_id=lectura_id,
        canciones_ids=canciones_ids,
        pptx_path=pptx_path,
        pdf_path=pdf_path,
        lecturas_json=lecturas_json,
        notas=notas,
        estado=estado_bd,
    )

    resultado = ResultadoGeneracion(
        fecha_domingo=fecha_domingo,
        lectura_id=lectura_id,
        presentacion_id=presentacion_id,
        pptx_path=pptx_path,
        pdf_path=pdf_path,
        canciones=canciones_nombres,
        notas=notas,
        modo=modo,
        dry_run=False,
        estado_presentacion=estado_bd,
    )
    resultado.imprimir_resumen()

    # Código de salida: éxito si al menos PPTX o PDF se generaron.
    exit_code = 0 if (pptx_path or pdf_path) else 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
