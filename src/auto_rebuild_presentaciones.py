"""Auto-reconstrucción de presentaciones cuando cambia una canción.

Opción B: tras crear/editar una canción, se crean automáticamente las slides
`cancion_<id>` para sus momentos litúrgicos y se regeneran las presentaciones
futuras que usen esa canción en su asignación.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"

MOMENTOS_CON_SLIDE = {
    "entrada", "acto_penitencial", "gloria", "salmo", "aleluya",
    "ofertorio", "santo", "padre_nuestro", "paz", "comunion", "maria", "despedida",
}

MOMENTO_A_TITULO = {
    "entrada": "{titulo}",
    "acto_penitencial": "{titulo}",
    "gloria": "{titulo}",
    "salmo": "SALMO: {titulo}",
    "aleluya": "{titulo}",
    "ofertorio": "{titulo}",
    "santo": "{titulo}",
    "padre_nuestro": "{titulo}",
    "paz": "{titulo}",
    "comunion": "{titulo}",
    "maria": "{titulo}",
    "despedida": "{titulo}",
}


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _limpiar_letra(html_visual: Optional[str], letra_sin_acordes: Optional[str], letra_con_acordes: Optional[str]) -> str:
    """Devuelve la letra limpia para el contenido de una slide."""
    if html_visual:
        return re.sub(r"<[^>]+?>", "", html_visual)
    if letra_sin_acordes:
        return letra_sin_acordes
    if letra_con_acordes:
        return letra_con_acordes
    return ""


def crear_slides_para_cancion(cancion_id: int) -> List[Tuple[str, int]]:
    """Crea slides `cancion_<id>` para los momentos litúrgicos de la canción.

    Devuelve la lista de (momento, slide_id) creados o ya existentes.
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT titulo, html_visual, letra_sin_acordes, letra_con_acordes FROM canciones WHERE id=?",
        (cancion_id,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return []

    titulo = row["titulo"]
    contenido = _limpiar_letra(
        row["html_visual"], row["letra_sin_acordes"], row["letra_con_acordes"]
    )

    cursor.execute(
        "SELECT momento_liturgico FROM cancion_momentos WHERE cancion_id=?",
        (cancion_id,),
    )
    momentos = [r["momento_liturgico"] for r in cursor.fetchall()]

    creados: List[Tuple[str, int]] = []
    for momento in momentos:
        # Normalizar variantes de clave
        momento_norm = "perdon" if momento == "acto_penitencial" else momento
        if momento_norm not in MOMENTOS_CON_SLIDE:
            continue

        subtipo = f"cancion_{cancion_id}"
        slide_titulo = MOMENTO_A_TITULO.get(momento_norm, "{titulo}").format(titulo=titulo)

        cursor.execute(
            "SELECT id FROM slides WHERE tipo=? AND subtipo=?",
            (momento_norm, subtipo),
        )
        existing = cursor.fetchone()
        if existing:
            creados.append((momento_norm, existing["id"]))
            continue

        cursor.execute(
            """
            INSERT INTO slides (tipo, subtipo, titulo, contenido, cita, subtitulo, imagen, es_default, activo, notas)
            VALUES (?, ?, ?, ?, '', '', '', 0, 1, 'Auto-creada desde canción')
            """,
            (momento_norm, subtipo, slide_titulo, contenido),
        )
        creados.append((momento_norm, cursor.lastrowid))

    conn.commit()
    conn.close()
    return creados


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
    resultado: Dict[str, int] = {}
    for momento, info in data.items():
        if info is None:
            continue
        if isinstance(info, dict) and "id" in info:
            try:
                resultado[momento] = int(info["id"])
            except (ValueError, TypeError):
                pass
        elif isinstance(info, int):
            resultado[momento] = info
        elif isinstance(info, str):
            try:
                resultado[momento] = int(info)
            except (ValueError, TypeError):
                pass
    return resultado


def encontrar_presentaciones_afectadas(cancion_id: int, solo_futuras: bool = True) -> List[Dict[str, Any]]:
    """Busca presentaciones cuya asignación incluya la canción."""
    conn = _get_connection()
    cursor = conn.cursor()

    today = date.today().isoformat()
    sql = "SELECT id, fecha_domingo, canciones_json, estado FROM presentaciones"
    params = []
    if solo_futuras:
        sql += " WHERE fecha_domingo >= ?"
        params.append(today)
    sql += " ORDER BY fecha_domingo"

    cursor.execute(sql, params)
    afectadas = []
    for row in cursor.fetchall():
        asignadas = _canciones_asignadas(row["canciones_json"])
        if cancion_id in asignadas.values():
            afectadas.append(dict(row))

    conn.close()
    return afectadas


def regenerar_presentacion(fecha: str) -> Dict[str, str]:
    """Regenera composición y bundle para una presentación."""
    import sys

    sys.path.insert(0, str(PROJECT_DIR / "src" / "generators"))
    from composicion_catalogo import proponer_composicion, guardar_composicion
    from generar_desde_composicion import GeneradorDesdeComposicion

    items = proponer_composicion(fecha)
    if not items:
        return {"status": "error", "error": f"No se pudo proponer composición para {fecha}"}

    # Forzar regeneración completa borrando la composición anterior
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM presentacion_slides WHERE presentacion_id=(SELECT id FROM presentaciones WHERE fecha_domingo=?)",
        (fecha,),
    )
    conn.commit()
    conn.close()

    guardar_composicion(fecha, items)
    GeneradorDesdeComposicion().generar_desde_presentacion(fecha)

    return {"status": "ok", "slides": len(items)}


def auto_rebuild_tras_cancion(cancion_id: int, solo_futuras: bool = True) -> Dict[str, Any]:
    """Punto de entrada principal: crea slides y regenera presentaciones afectadas."""
    slides = crear_slides_para_cancion(cancion_id)
    presentaciones = encontrar_presentaciones_afectadas(cancion_id, solo_futuras=solo_futuras)
    resultados = []
    for pres in presentaciones:
        res = regenerar_presentacion(pres["fecha_domingo"])
        res["fecha"] = pres["fecha_domingo"]
        resultados.append(res)

    return {
        "slides_creadas": slides,
        "presentaciones_afectadas": [p["fecha_domingo"] for p in presentaciones],
        "resultados": resultados,
    }
