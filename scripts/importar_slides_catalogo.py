#!/usr/bin/env python3
"""
Importa las diapositivas de presentaciones ya generadas al catálogo maestro.
Fase A del Editor de Diapositivas CCE-M5.

Lógica:
- Lee JSON de presentaciones en presentaciones_html/YYYY-MM-DD_presentacion/*.json.
- Para cada slide, intenta vincular primero con el cancionero si el tipo espera una canción.
- Si el tipo no espera canción o la canción no se encuentra, se usa el texto fijo/canónico.
- Las slides fijas (Acto Penitencial, Credo, Bendición del agua, transiciones) se insertan como base única.
- Marca es_default la primera slide canónica encontrada por (tipo, subtipo, color).

Uso:
    python3 scripts/importar_slides_catalogo.py
"""
import json
import sqlite3
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
PRESENTACIONES_DIR = PROJECT_DIR / "presentaciones_html"
SCHEMA_PATH = PROJECT_DIR / "data" / "schema_slides.sql"

# Tipos canónicos reconocidos (deben coincidir con schema_slides.sql)
TIPOS_CANONICOS = {
    "portada", "entrada", "perdon", "gloria", "transicion_palabra",
    "primera_lectura", "salmo", "segunda_lectura", "aleluya", "evangelio",
    "transicion_eucaristia", "credo", "ofertorio", "santo", "padre_nuestro",
    "paz", "comunion", "maria", "despedida",
}

# Tipos que son siempre momentos musicales y deben buscar canción
TIPOS_MUSICALES = {
    "entrada", "gloria", "aleluya", "ofertorio", "santo", "padre_nuestro",
    "paz", "comunion", "maria", "despedida",
}

# Slides con texto fijo litúrgico que queremos como base única
TEXTOS_FIJOS = {
    "ACTO PENITENCIAL": ("perdon", "acto_penitencial"),
    "BENDICIÓN DEL AGUA": ("perdon", "bendicion_agua"),
    "GLORIA": ("gloria", "texto_fijo"),
    "CREDO": ("credo", "texto_fijo"),
    "SANTO": ("santo", "texto_fijo"),
    "PADRE NUESTRO": ("padre_nuestro", "texto_fijo"),
    "RITO DE LA PAZ": ("paz", "texto_fijo"),
    "CANTO A MARÍA": ("maria", "texto_fijo"),
    "LITURGIA DE LA PALABRA": ("transicion_palabra", "general"),
    "LITURGIA EUCARÍSTICA": ("transicion_eucaristia", "general"),
}


def _normalizar(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().strip())


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _aplicar_schema():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"No existe {SCHEMA_PATH}")
    conn = _get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def _buscar_cancion_por_titulo(conn: sqlite3.Connection, titulo: str):
    norm = _normalizar(titulo)
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, letra_sin_acordes, letra_con_acordes FROM canciones")
    for row in cursor.fetchall():
        if _normalizar(row["titulo"]) == norm:
            return row
    # Búsqueda por contención si no coincide exacto
    cursor.execute(
        "SELECT id, titulo, letra_sin_acordes, letra_con_acordes FROM canciones WHERE ? LIKE '%' || titulo || '%'",
        (titulo,),
    )
    row = cursor.fetchone()
    if row:
        return row
    cursor.execute(
        "SELECT id, titulo, letra_sin_acordes, letra_con_acordes FROM canciones WHERE titulo LIKE ?",
        (f"%{titulo}%",),
    )
    return cursor.fetchone()


def _extraer_subtipo_fijo(titulo: str, tipo: str) -> tuple:
    titulo_upper = titulo.upper()
    # La diapositiva final "¡Id en paz!" es portada de despedida, no canción
    if "¡ID EN PAZ!" in titulo_upper:
        return "portada", "despedida"
    # Los tipos musicales se intentan resolver primero por cancionero
    if tipo in TIPOS_MUSICALES:
        return tipo, ""
    # Para no musicales, buscar textos fijos conocidos
    for clave, (tipo_fijo, subtipo) in TEXTOS_FIJOS.items():
        if clave in titulo_upper:
            return tipo_fijo, subtipo
    return tipo, "general"


def _contenido_base(titulo: str, contenido: str) -> str:
    if "rellenar a mano" in contenido.lower():
        return ""
    return contenido


def _leer_presentaciones():
    bundles = []
    for bundle_dir in sorted(PRESENTACIONES_DIR.glob("*_presentacion")):
        json_files = list(bundle_dir.glob("*_presentacion.json"))
        if not json_files:
            continue
        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        data["_ruta"] = str(bundle_dir)
        bundles.append(data)
    return bundles


def _insertar_slide_base(
    conn: sqlite3.Connection,
    tipo: str,
    subtipo: str,
    titulo: str,
    contenido: str,
    cita: str,
    subtitulo: str,
    imagen: str,
    color_liturgico: str,
) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM slides
        WHERE tipo = ? AND subtipo = ? AND lower(trim(titulo)) = lower(trim(?))
        """,
        (tipo, subtipo, titulo),
    )
    existing = cursor.fetchone()
    if existing:
        return existing["id"]

    cursor.execute(
        """
        INSERT INTO slides (tipo, subtipo, titulo, contenido, cita, subtitulo, imagen, color_liturgico, es_default)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (tipo, subtipo, titulo, contenido, cita, subtitulo, imagen, color_liturgico, 1),
    )
    conn.commit()
    return cursor.lastrowid


def _marcar_default_unico(conn: sqlite3.Connection, tipo: str, subtipo: str, color: str):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM slides
        WHERE tipo = ? AND subtipo = ? AND (color_liturgico = ? OR color_liturgico = '') AND activo = 1
        ORDER BY fecha_creacion ASC, id ASC
        LIMIT 1
        """,
        (tipo, subtipo, color),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            """
            UPDATE slides SET es_default = 0
            WHERE tipo = ? AND subtipo = ? AND (color_liturgico = ? OR color_liturgico = '') AND id != ?
            """,
            (tipo, subtipo, color, row["id"]),
        )
        cursor.execute(
            "UPDATE slides SET es_default = 1 WHERE id = ?",
            (row["id"],),
        )
        conn.commit()


def _registrar_presentacion_slide(
    conn: sqlite3.Connection,
    presentacion_id: int,
    slide_id: int,
    numero: int,
    tipo: str,
    subtipo: str,
    titulo: str,
    contenido: str,
    cita: str,
    subtitulo: str,
    imagen: str,
    momento: str,
):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM presentacion_slides
        WHERE presentacion_id = ? AND numero = ?
        """,
        (presentacion_id, numero),
    )
    if cursor.fetchone():
        return
    cursor.execute(
        """
        INSERT INTO presentacion_slides
        (presentacion_id, slide_id, numero, tipo, subtipo, titulo, contenido, cita, subtitulo, imagen, momento)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (presentacion_id, slide_id, numero, tipo, subtipo, titulo, contenido, cita, subtitulo, imagen, momento),
    )
    conn.commit()


def _presentacion_id_por_fecha(conn: sqlite3.Connection, fecha: str) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM presentaciones WHERE fecha_domingo = ?", (fecha,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    cursor.execute(
        "INSERT INTO presentaciones (fecha_domingo, estado, fecha_creacion) VALUES (?, 'importado', ?)",
        (fecha, datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def main():
    print(f"[{datetime.now().isoformat()}] Iniciando importación de slides al catálogo...")
    print(f"Base de datos: {DB_PATH}")

    if not DB_PATH.exists():
        print("ERROR: No existe la base de datos.", file=sys.stderr)
        sys.exit(1)

    _aplicar_schema()
    conn = _get_connection()

    # Limpiar tablas para reimportación limpia
    cursor = conn.cursor()
    cursor.execute("DELETE FROM presentacion_slides")
    cursor.execute("DELETE FROM slides")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='slides'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='presentacion_slides'")
    conn.commit()
    print("Tablas de catálogo vaciadas para importación limpia.")

    presentaciones = _leer_presentaciones()
    print(f"Presentaciones encontradas: {len(presentaciones)}")

    stats = defaultdict(int)

    for data in presentaciones:
        meta = data.get("meta", {})
        fecha = meta.get("fecha")
        color = (meta.get("color_liturgico") or "verde").lower()
        if not fecha:
            print("WARNING: presentación sin fecha, se omite.", file=sys.stderr)
            continue

        presentacion_id = _presentacion_id_por_fecha(conn, fecha)
        slides = data.get("slides", [])
        print(f"Procesando {fecha} ({len(slides)} slides)...")

        for slide in slides:
            tipo = slide.get("tipo", "")
            titulo = slide.get("titulo", "").strip()
            contenido = slide.get("contenido", "")
            cita = slide.get("cita", "")
            subtitulo = slide.get("subtitulo", "")
            imagen = slide.get("imagen", "")
            momento = slide.get("momento", "")
            numero = slide.get("numero", 0)

            if tipo not in TIPOS_CANONICOS:
                stats["tipo_desconocido"] += 1
                continue

            tipo, subtipo = _extraer_subtipo_fijo(titulo, tipo)
            es_cancion = False
            cancion_id = None

            # Resolver canciones para tipos musicales
            if tipo in TIPOS_MUSICALES and not subtipo:
                cancion = _buscar_cancion_por_titulo(conn, titulo)
                if cancion:
                    es_cancion = True
                    cancion_id = cancion["id"]
                    subtipo = f"cancion_{cancion_id}"
                    contenido_base = cancion["letra_sin_acordes"] or cancion["letra_con_acordes"] or contenido
                    titulo_base = cancion["titulo"] or titulo
                    stats["canciones"] += 1
                else:
                    subtipo = "sin_cancion"
                    contenido_base = contenido
                    titulo_base = titulo
                    stats["sin_cancion"] += 1
            else:
                contenido_base = _contenido_base(titulo, contenido)
                titulo_base = titulo
                stats["fijos"] += 1

            slide_id = _insertar_slide_base(
                conn, tipo, subtipo, titulo_base, contenido_base, cita, subtitulo, imagen, color if es_cancion else ""
            )
            _marcar_default_unico(conn, tipo, subtipo, color if es_cancion else "")
            _registrar_presentacion_slide(
                conn, presentacion_id, slide_id, numero, tipo, subtipo,
                titulo, contenido, cita, subtitulo, imagen, momento,
            )

    conn.close()

    print("\nResumen de importación:")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"[{datetime.now().isoformat()}] Importación completada.")


if __name__ == "__main__":
    main()
