"""Gestión compartida de canciones del cancionero CCE-M5.

Operaciones CRUD de canciones usadas por:
- Editor de acordes (Flask, puerto 4322)
- Editor de diapositivas (Flask, puerto 4323)
- Admin API / cancionero web (FastAPI, puerto 4324)

La fuente de verdad es SQLite (`data/db.sqlite3`). Al crear o editar una
canción se regeneran los campos derivados (html_visual, estructura_json,
letra_sin_acordes, tono) y se sincronizan los momentos litúrgicos.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"

MOMENTOS_LITURGICOS = [
    "entrada", "acto penitencial", "gloria", "primera_lectura", "salmo",
    "segunda_lectura", "aleluya", "evangelio", "credo", "ofertorio", "santo",
    "padre_nuestro", "paz", "comunion", "maria", "despedida", "general",
]


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def slugify(titulo: str) -> str:
    t = unicodedata.normalize("NFD", titulo.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t


def _regenerar_derivados(texto_con_acordes: str) -> dict:
    """Regenera html_visual, estructura_json, letra_sin_acordes y tono."""
    if str(PROJECT_DIR / "src") not in __import__("sys").path:
        __import__("sys").path.insert(0, str(PROJECT_DIR / "src"))
    from parsers.acordes_parser_v3 import AcordesParser

    parser = AcordesParser()
    estructura = parser.parsear_cancion_completa(texto_con_acordes)
    html_visual = parser.generar_html_visual(estructura)
    tono = parser.detectar_tono(estructura)

    letra_limpia_lines = []
    for linea in estructura:
        if linea.tipo in ("letra", "acordes_letra"):
            letra_limpia_lines.append(linea.letra)
    letra_sin_acordes = "\n".join(letra_limpia_lines)

    estructura_json = json.dumps(
        [
            {
                "tipo": linea.tipo,
                "acordes": [{"acorde": a.acorde, "posicion": a.posicion} for a in linea.acordes],
                "letra": linea.letra,
                "texto": linea.texto,
            }
            for linea in estructura
        ],
        ensure_ascii=False,
    )

    return {
        "letra_sin_acordes": letra_sin_acordes,
        "acordes_json": "",
        "estructura_json": estructura_json,
        "html_visual": html_visual,
        "tono": tono,
    }


@dataclass
class CancionCreateUpdate:
    titulo: str
    letra_con_acordes: str
    momentos: Optional[List[str]] = None
    tono: Optional[str] = None
    fuente: Optional[str] = None


def crear_cancion(data: CancionCreateUpdate) -> Dict[str, Any]:
    """Inserta una nueva canción en la base de datos."""
    titulo = data.titulo.strip()
    if not titulo:
        raise ValueError("El título es obligatorio")

    texto = data.letra_con_acordes or ""
    derivados = _regenerar_derivados(texto)

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO canciones (
            titulo, titulo_url, letra_con_acordes, letra_sin_acordes,
            acordes_json, estructura_json, html_visual, tono, fuente, fecha_creacion
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            titulo,
            slugify(titulo),
            texto,
            derivados["letra_sin_acordes"],
            derivados["acordes_json"],
            derivados["estructura_json"],
            derivados["html_visual"],
            data.tono or derivados["tono"],
            data.fuente or "manual",
        ),
    )
    cancion_id = cursor.lastrowid

    _sync_momentos(cursor, cancion_id, data.momentos or [])
    conn.commit()

    cancion = _get_cancion_by_id(cursor, cancion_id)
    conn.close()

    try:
        from src.auto_rebuild_presentaciones import auto_rebuild_tras_cancion
        auto_rebuild_tras_cancion(cancion_id, solo_futuras=True)
    except Exception:
        # No bloquear la creación de la canción si la regeneración de presentaciones falla.
        pass

    return cancion


def actualizar_cancion(cancion_id: int, data: CancionCreateUpdate) -> Dict[str, Any]:
    """Actualiza una canción existente."""
    titulo = data.titulo.strip()
    if not titulo:
        raise ValueError("El título es obligatorio")

    texto = data.letra_con_acordes or ""
    derivados = _regenerar_derivados(texto)

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE canciones SET
            titulo = ?,
            titulo_url = ?,
            letra_con_acordes = ?,
            letra_sin_acordes = ?,
            acordes_json = ?,
            estructura_json = ?,
            html_visual = ?,
            tono = ?,
            fuente = ?
        WHERE id = ?
        """,
        (
            titulo,
            slugify(titulo),
            texto,
            derivados["letra_sin_acordes"],
            derivados["acordes_json"],
            derivados["estructura_json"],
            derivados["html_visual"],
            data.tono or derivados["tono"],
            data.fuente or "manual",
            cancion_id,
        ),
    )
    if cursor.rowcount == 0:
        conn.close()
        raise ValueError(f"No existe canción con id={cancion_id}")

    _sync_momentos(cursor, cancion_id, data.momentos or [])
    conn.commit()

    cancion = _get_cancion_by_id(cursor, cancion_id)
    conn.close()

    try:
        from src.auto_rebuild_presentaciones import auto_rebuild_tras_cancion
        auto_rebuild_tras_cancion(cancion_id, solo_futuras=True)
    except Exception:
        # No bloquear la actualización de la canción si la regeneración de presentaciones falla.
        pass

    return cancion


def eliminar_cancion(cancion_id: int) -> None:
    """Elimina una canción y sus momentos asociados."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cancion_momentos WHERE cancion_id = ?", (cancion_id,))
    cursor.execute("DELETE FROM canciones WHERE id = ?", (cancion_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise ValueError(f"No existe canción con id={cancion_id}")
    conn.commit()
    conn.close()


def _sync_momentos(cursor, cancion_id: int, momentos: List[str]) -> None:
    cursor.execute("DELETE FROM cancion_momentos WHERE cancion_id = ?", (cancion_id,))
    for m in momentos:
        m = m.strip().lower()
        if m:
            cursor.execute(
                "INSERT OR IGNORE INTO cancion_momentos (cancion_id, momento_liturgico) VALUES (?, ?)",
                (cancion_id, m),
            )


def _get_momentos(cursor, cancion_id: int) -> List[str]:
    cursor.execute(
        "SELECT momento_liturgico FROM cancion_momentos WHERE cancion_id = ? ORDER BY momento_liturgico",
        (cancion_id,),
    )
    return [r["momento_liturgico"] for r in cursor.fetchall()]


def _get_cancion_by_id(cursor, cancion_id: int) -> Dict[str, Any]:
    cursor.execute("SELECT * FROM canciones WHERE id = ?", (cancion_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"No existe canción con id={cancion_id}")
    d = dict(row)
    d["momentos"] = _get_momentos(cursor, cancion_id)
    d["slug"] = slugify(d["titulo"])
    return d


def listar_canciones() -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo FROM canciones ORDER BY titulo")
    result = []
    for r in cursor.fetchall():
        cancion = _get_cancion_by_id(cursor, r["id"])
        result.append(cancion)
    conn.close()
    return result


def obtener_cancion(cancion_id: int) -> Dict[str, Any]:
    conn = _get_connection()
    cursor = conn.cursor()
    cancion = _get_cancion_by_id(cursor, cancion_id)
    conn.close()
    return cancion
