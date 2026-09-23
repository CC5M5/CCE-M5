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
from typing import Dict, List

PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
PRESENTACIONES_DIR = PROJECT_DIR / "presentaciones_html"
SCHEMA_PATH = PROJECT_DIR / "data" / "schema_slides.sql"

# Tipos canónicos reconocidos (deben coincidir con schema_slides.sql)
TIPOS_CANONICOS = {
    "portada", "entrada", "paso", "perdon", "gloria", "transicion_palabra",
    "primera_lectura", "salmo", "segunda_lectura", "aleluya", "evangelio",
    "transicion_eucaristia", "credo", "ofertorio", "santo", "padre_nuestro",
    "paz", "comunion", "maria", "despedida",
}

# Tipos que son siempre momentos musicales y deben buscar canción
TIPOS_MUSICALES = {
    "entrada", "gloria", "aleluya", "ofertorio", "santo", "padre_nuestro",
    "paz", "comunion", "maria", "despedida",
}

# Orden canónico de momentos en una presentación, con los pasos de transición
# que deben aparecer ANTES del momento indicado.
ORDEN_MOMENTOS = [
    ("portada", None),
    ("entrada", None),
    ("transicion_palabra", None),             # Liturgia de la Palabra (texto)
    ("perdon", None),
    ("paso", "transicion_gloria"),             # paso neutro antes del gloria
    ("gloria", None),
    ("primera_lectura", None),
    ("salmo", None),
    ("segunda_lectura", None),
    ("aleluya", None),
    ("evangelio", None),
    ("transicion_eucaristia", None),            # Liturgia Eucarística (texto)
    ("credo", None),
    ("paso", "transicion_ofertorio"),
    ("ofertorio", None),
    ("paso", "transicion_santo"),
    ("santo", None),
    ("paso", "transicion_padre_nuestro"),
    ("padre_nuestro", None),
    ("paso", "transicion_paz"),
    ("paz", None),
    ("paso", "transicion_comunion"),
    ("comunion", None),
    ("paso", "transicion_maria"),
    ("maria", None),
    ("paso", "transicion_despedida"),
    ("despedida", None),
    ("portada", "despedida"),                   # slide final ¡Id en paz!
]

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

# Textos sugeridos para diapositivas de paso neutras entre momentos
PASO_ETIQUETAS = {
    "transicion_palabra": ("", ""),
    "transicion_gloria": ("", ""),
    "transicion_ofertorio": ("", ""),
    "transicion_santo": ("", ""),
    "transicion_padre_nuestro": ("", ""),
    "transicion_paz": ("", ""),
    "transicion_comunion": ("", ""),
    "transicion_maria": ("", ""),
    "transicion_despedida": ("", ""),
}

# Imagen por defecto para slides de paso
PASO_IMAGEN_DEFAULT = "assets/comunidad_oracion.svg"


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


def _insertar_paso_base(conn: sqlite3.Connection, etiqueta: str, imagen: str = "") -> int:
    """Devuelve el ID de la slide base tipo 'paso' para una etiqueta concreta."""
    subtipo = f"paso_{etiqueta}" if etiqueta else "paso_generico"
    titulo = ""
    contenido = ""
    img = imagen or PASO_IMAGEN_DEFAULT
    return _insertar_slide_base(conn, "paso", subtipo, titulo, contenido, "", "", img, "")


def _slide_por_tipo_y_subtipo(conn: sqlite3.Connection, tipo: str, subtipo: str):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM slides WHERE tipo = ? AND subtipo = ? AND activo = 1 LIMIT 1",
        (tipo, subtipo),
    )
    row = cursor.fetchone()
    return row["id"] if row else None


def _construir_orden_con_pasos(slides_originales: List[dict]) -> List[dict]:
    """
    Toma las slides de una presentación histórica y devuelve el orden canónico
    con diapositivas de paso insertadas según ORDEN_MOMENTOS.
    """
    # Indexar slides originales por tipo (y subtipo para portada/despedida)
    by_tipo: Dict[str, List[dict]] = defaultdict(list)
    for s in slides_originales:
        tipo = s.get("tipo", "")
        titulo = s.get("titulo", "").strip().upper()
        # Portada final va con subtipo despedida
        if tipo == "portada" and "ID EN PAZ" in titulo:
            by_tipo["portada_despedida"].append(s)
        else:
            by_tipo[tipo].append(s)

    # Asegurar que las transiciones litúrgicas existen como base canónica
    for trans_tipo, trans_titulo, trans_contenido, trans_imagen in [
        ("transicion_palabra", "LITURGIA DE LA PALABRA", "Escuchemos la Palabra de Dios", "assets/20140961.jpg"),
        ("transicion_eucaristia", "LITURGIA EUCARÍSTICA", "Preparémonos para la mesa del Señor", "assets/20140959.jpg"),
    ]:
        if not by_tipo.get(trans_tipo):
            by_tipo[trans_tipo].append({
                "tipo": trans_tipo,
                "subtipo": "general",
                "titulo": trans_titulo,
                "contenido": trans_contenido,
                "cita": "",
                "subtitulo": "",
                "imagen": trans_imagen,
                "momento": "",
            })

    resultado: List[dict] = []
    for tipo_req, subtipo_req in ORDEN_MOMENTOS:
        if tipo_req == "paso":
            # Insertar slide de paso neutra
            resultado.append({
                "tipo": "paso",
                "subtipo": f"paso_{subtipo_req}",
                "titulo": "",
                "contenido": "",
                "cita": "",
                "subtitulo": "",
                "imagen": PASO_IMAGEN_DEFAULT,
                "momento": "",
                "_es_paso": True,
                "_paso_etiqueta": subtipo_req,
            })
        elif tipo_req == "portada" and subtipo_req == "despedida":
            slide = by_tipo.get("portada_despedida", [None])[0]
            if slide:
                resultado.append(slide)
        else:
            slides = by_tipo.get(tipo_req, [])
            # Para tipos musicales, si hay varias variantes, tomamos la primera
            for slide in slides:
                resultado.append(slide)
    return resultado


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
    pasos_vistos: set = set()

    for data in presentaciones:
        meta = data.get("meta", {})
        fecha = meta.get("fecha")
        color = (meta.get("color_liturgico") or "verde").lower()
        if not fecha:
            print("WARNING: presentación sin fecha, se omite.", file=sys.stderr)
            continue

        presentacion_id = _presentacion_id_por_fecha(conn, fecha)
        slides_originales = data.get("slides", [])
        slides_ordenadas = _construir_orden_con_pasos(slides_originales)
        print(f"Procesando {fecha} ({len(slides_originales)} originales -> {len(slides_ordenadas)} con pasos)...")

        for numero, slide in enumerate(slides_ordenadas, start=1):
            tipo = slide.get("tipo", "")
            titulo = slide.get("titulo", "").strip()
            contenido = slide.get("contenido", "")
            cita = slide.get("cita", "")
            subtitulo = slide.get("subtitulo", "")
            imagen = slide.get("imagen", "")
            momento = slide.get("momento", "")

            if slide.get("_es_paso"):
                etiqueta = slide["_paso_etiqueta"]
                subtipo = f"paso_{etiqueta}"
                slide_id = _insertar_paso_base(conn, etiqueta, imagen)
                pasos_vistos.add(subtipo)
                _registrar_presentacion_slide(
                    conn, presentacion_id, slide_id, numero, "paso", subtipo,
                    titulo, contenido, cita, subtitulo, imagen, momento,
                )
                stats["pasos"] += 1
                continue

            if tipo not in TIPOS_CANONICOS:
                stats["tipo_desconocido"] += 1
                continue

            tipo_resuelto, subtipo = _extraer_subtipo_fijo(titulo, tipo)
            es_cancion = False
            cancion_id = None

            # Resolver canciones para tipos musicales
            if tipo_resuelto in TIPOS_MUSICALES and not subtipo:
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
                conn, tipo_resuelto, subtipo, titulo_base, contenido_base, cita, subtitulo, imagen, ""
            )
            _registrar_presentacion_slide(
                conn, presentacion_id, slide_id, numero, tipo_resuelto, subtipo,
                titulo, contenido, cita, subtitulo, imagen, momento,
            )

    # Normalizar es_default: solo una por (tipo, subtipo)
    print("\nNormalizando es_default por (tipo, subtipo)...")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT tipo, subtipo FROM slides")
    for row in cursor.fetchall():
        _marcar_default_unico(conn, row["tipo"], row["subtipo"], "")

    conn.close()

    print("\nResumen de importación:")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"[{datetime.now().isoformat()}] Importación completada.")


if __name__ == "__main__":
    main()
