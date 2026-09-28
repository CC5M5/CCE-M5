"""Lógica compartida de composición de presentaciones desde el catálogo de slides."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"

ORDEN_MOMENTOS_C: List[tuple[str, str]] = [
    ("portada", "general"),
    ("entrada", ""),
    ("transicion_palabra", "general"),
    ("perdon", ""),
    ("paso", "neutro"),
    ("gloria", ""),
    ("primera_lectura", "general"),
    ("salmo", "general"),
    ("segunda_lectura", "general"),
    ("aleluya", ""),
    ("evangelio", "general"),
    ("transicion_eucaristia", "general"),
    ("credo", "texto_fijo"),
    ("paso", "neutro"),
    ("ofertorio", ""),
    ("paso", "neutro"),
    ("santo", ""),
    ("paso", "neutro"),
    ("padre_nuestro", ""),
    ("paso", "neutro"),
    ("paz", ""),
    ("paso", "neutro"),
    ("comunion", ""),
    ("paso", "neutro"),
    ("maria", ""),
    ("paso", "neutro"),
    ("despedida", ""),
    ("portada", "despedida"),
]

MOMENTOS_MUSICALES = ("entrada", "gloria", "aleluya", "ofertorio", "santo", "padre_nuestro", "paz", "comunion", "maria", "despedida")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _canciones_asignadas(canciones_json: Optional[str]) -> Dict[str, int]:
    """Devuelve {momento: cancion_id} desde el JSON de la presentación."""
    if not canciones_json:
        return {}
    try:
        data = json.loads(canciones_json)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    resultado = {}
    for momento, info in data.items():
        if isinstance(info, dict) and "id" in info:
            resultado[momento] = int(info["id"])
        elif isinstance(info, int):
            resultado[momento] = info
    return resultado


def _get_slide_variantes(tipo: str) -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, subtipo, titulo, es_default
        FROM slides
        WHERE tipo = ? AND activo = 1
        ORDER BY es_default DESC, titulo
    """, (tipo,))
    rows = [{"id": r["id"], "subtipo": r["subtipo"], "titulo": r["titulo"], "es_default": r["es_default"]} for r in cursor.fetchall()]
    conn.close()
    return rows


def _slide_para_momento(tipo: str, subtipo_sugerido: str) -> Optional[Dict[str, Any]]:
    """Busca la mejor slide del catálogo para un momento dado."""
    conn = _get_connection()
    cursor = conn.cursor()
    # 1. subtipo exacto y default
    cursor.execute("""
        SELECT * FROM slides
        WHERE tipo = ? AND subtipo = ? AND activo = 1
        ORDER BY es_default DESC, id
        LIMIT 1
    """, (tipo, subtipo_sugerido))
    row = cursor.fetchone()
    if not row:
        # 2. cualquier subtipo default
        cursor.execute("""
            SELECT * FROM slides
            WHERE tipo = ? AND es_default = 1 AND activo = 1
            ORDER BY id
            LIMIT 1
        """, (tipo,))
        row = cursor.fetchone()
    if not row:
        # 3. cualquier slide activa del tipo
        cursor.execute("""
            SELECT * FROM slides
            WHERE tipo = ? AND activo = 1
            ORDER BY id
            LIMIT 1
        """, (tipo,))
        row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def _get_presentacion_por_fecha(fecha: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM presentaciones WHERE fecha_domingo = ?", (fecha,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def proponer_composicion(fecha: str) -> List[Dict[str, Any]]:
    """Genera la lista de items propuestos para una fecha usando el catálogo de slides."""
    pres = _get_presentacion_por_fecha(fecha)
    if not pres:
        return []
    canciones = _canciones_asignadas(pres.get("canciones_json"))

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.titulo, GROUP_CONCAT(cm.momento_liturgico, ',') as momentos
        FROM canciones c
        LEFT JOIN cancion_momentos cm ON cm.cancion_id = c.id
        GROUP BY c.id
    """)
    canciones_info = {
        r["id"]: {"titulo": r["titulo"], "momento": r["momentos"].split(",")[0] if r["momentos"] else ""}
        for r in cursor.fetchall()
    }
    conn.close()

    items: List[Dict[str, Any]] = []
    numero = 1
    for tipo, subtipo_default in ORDEN_MOMENTOS_C:
        if tipo == "paso":
            items.append({
                "numero": numero,
                "tipo": "paso",
                "subtipo": f"paso_{subtipo_default}",
                "titulo": "",
                "slide_id": None,
                "activo": 1,
                "_es_paso": True,
            })
            numero += 1
            continue

        subtipo = subtipo_default
        if tipo in MOMENTOS_MUSICALES and tipo in canciones:
            cancion_id = canciones[tipo]
            slide_pref = _slide_para_momento(tipo, f"cancion_{cancion_id}")
            if slide_pref:
                subtipo = f"cancion_{cancion_id}"
            else:
                slide_pref = _slide_para_momento(tipo, subtipo_default)
        else:
            slide_pref = _slide_para_momento(tipo, subtipo_default)

        if not slide_pref:
            items.append({
                "numero": numero,
                "tipo": tipo,
                "subtipo": subtipo,
                "titulo": f"[FALTA: {tipo}]",
                "slide_id": None,
                "activo": 1,
                "_es_paso": False,
            })
        else:
            items.append({
                "numero": numero,
                "tipo": tipo,
                "subtipo": slide_pref["subtipo"],
                "titulo": slide_pref["titulo"],
                "slide_id": slide_pref["id"],
                "activo": 1,
                "_es_paso": False,
            })
        numero += 1
    return items


def guardar_composicion(fecha: str, items: List[Dict[str, Any]]) -> None:
    """Guarda una composición en presentacion_slides para una fecha."""
    pres = _get_presentacion_por_fecha(fecha)
    if not pres:
        raise ValueError(f"No existe presentación para {fecha}")
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM presentacion_slides WHERE presentacion_id = ?", (pres["id"],))
    for item in items:
        slide_id = item.get("slide_id")
        if slide_id:
            cursor.execute("""
                INSERT INTO presentacion_slides
                (presentacion_id, slide_id, numero, tipo, subtipo, titulo, contenido, cita, subtitulo, imagen, momento, activo)
                SELECT ?, s.id, ?, ?, ?, s.titulo, s.contenido, s.cita, s.subtitulo, s.imagen, '', ?
                FROM slides s
                WHERE s.id = ?
            """, (pres["id"], item["numero"], item["tipo"], item["subtipo"], item["activo"], slide_id))
            if cursor.rowcount == 0:
                slide_id = None
        if not slide_id:
            cursor.execute("""
                INSERT INTO presentacion_slides
                (presentacion_id, slide_id, numero, tipo, subtipo, titulo, contenido, activo)
                VALUES (?, NULL, ?, ?, ?, ?, '', ?)
            """, (pres["id"], item["numero"], item["tipo"], item["subtipo"], item["titulo"], item["activo"]))
    conn.commit()
    conn.close()


def asegurar_composicion(fecha: str, canciones_json: Optional[str] = None) -> bool:
    """Crea una composición por defecto si no existe. Devuelve True si se creó."""
    pres = _get_presentacion_por_fecha(fecha)
    if not pres:
        return False
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS n FROM presentacion_slides WHERE presentacion_id = ?", (pres["id"],))
    count = cursor.fetchone()["n"]
    conn.close()
    if count > 0:
        return False
    # Crear composición por defecto; si se pasa canciones_json actualizar presentaciones primero
    if canciones_json is not None:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE presentaciones SET canciones_json = ? WHERE id = ?", (canciones_json, pres["id"]))
        conn.commit()
        conn.close()
    items = proponer_composicion(fecha)
    if items:
        guardar_composicion(fecha, items)
        return True
    return False
