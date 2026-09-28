#!/usr/bin/env python3
"""Exporta datos de SQLite a JSON para el build estático de Astro."""

import json
import os
import sqlite3
from pathlib import Path

PROJECT_DIR = Path(os.environ.get('CCE_PROJECT_DIR', Path(__file__).parent.parent.resolve()))
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
WEB_DATA_DIR = PROJECT_DIR / "web" / "data"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def export_all():
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        for tabla, query, orden in [
            ("canciones.json", "SELECT * FROM canciones ORDER BY id", None),
            ("cancion_momentos.json", "SELECT cancion_id, momento_liturgico FROM cancion_momentos ORDER BY cancion_id", None),
            ("presentaciones.json", "SELECT * FROM presentaciones ORDER BY fecha_domingo DESC", None),
            ("comentarios.json", "SELECT * FROM comentarios ORDER BY fecha_creacion DESC", None),
        ]:
            rows = conn.execute(query).fetchall()
            data = [dict(r) for r in rows]
            out = WEB_DATA_DIR / tabla
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  {tabla}: {len(data)} registros")
    print(f"Exportación completada en {WEB_DATA_DIR}")


if __name__ == "__main__":
    export_all()
