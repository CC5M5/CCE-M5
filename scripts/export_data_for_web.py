#!/usr/bin/env python3
"""Exporta datos de SQLite a JSON para el build estático de Astro.

Uso en CI:
    python scripts/export_data_for_web.py --project-dir .
"""

import argparse
import json
import sqlite3
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exporta datos de SQLite a JSON")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Directorio raíz del proyecto (default: directorio padre de scripts/)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.project_dir:
        project_dir = args.project_dir.resolve()
    else:
        project_dir = Path(__file__).resolve().parent.parent

    db_path = project_dir / "data" / "db.sqlite3"
    web_data_dir = project_dir / "web" / "data"
    web_data_dir.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        raise FileNotFoundError(f"No se encuentra la base de datos: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        for tabla, query in [
            ("canciones.json", "SELECT * FROM canciones ORDER BY id"),
            (
                "cancion_momentos.json",
                "SELECT cancion_id, momento_liturgico FROM cancion_momentos ORDER BY cancion_id",
            ),
            (
                "presentaciones.json",
                "SELECT * FROM presentaciones ORDER BY fecha_domingo DESC",
            ),
            ("comentarios.json", "SELECT * FROM comentarios ORDER BY fecha_creacion DESC"),
        ]:
            rows = conn.execute(query).fetchall()
            data = [dict(r) for r in rows]
            out = web_data_dir / tabla
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  {tabla}: {len(data)} registros")
    finally:
        conn.close()

    print(f"Exportación completada en {web_data_dir}")


if __name__ == "__main__":
    main()
