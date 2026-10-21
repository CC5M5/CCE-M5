"""Helpers de base de datos para los editores Flask legacy."""

from __future__ import annotations

import sqlite3
from typing import Any

from src.config import settings

DB_PATH = settings.db_path


def get_connection():
    """Conexión SQLite con acceso por columnas como dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_momentos_cancion(cancion_id: int) -> list[str]:
    """Devuelve los momentos litúrgicos asignados a una canción."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT momento_liturgico FROM cancion_momentos WHERE cancion_id = ? ORDER BY momento_liturgico",
        (cancion_id,),
    )
    rows = [r["momento_liturgico"] for r in cursor.fetchall()]
    conn.close()
    return rows


def set_momentos_cancion(cancion_id: int, momentos: list[str]) -> None:
    """Reemplaza los momentos litúrgicos de una canción."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cancion_momentos WHERE cancion_id = ?", (cancion_id,))
    for m in momentos:
        m = m.strip().lower()
        if m:
            cursor.execute(
                "INSERT OR IGNORE INTO cancion_momentos (cancion_id, momento_liturgico) VALUES (?, ?)",
                (cancion_id, m),
            )
    conn.commit()
    conn.close()


def run_query(
    sql: str, params: tuple[Any, ...] = (), *, fetch_one: bool = False
) -> list[sqlite3.Row] | sqlite3.Row | None:
    """Ejecuta una consulta SQL y devuelve las filas (o None si fetch_one=True y no hay)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    if fetch_one:
        row = cursor.fetchone()
        conn.close()
        return row
    rows = cursor.fetchall()
    conn.close()
    return rows
