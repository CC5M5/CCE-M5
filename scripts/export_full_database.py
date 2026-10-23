#!/usr/bin/env python3
"""Exporta la base de datos SQLite completa a un archivo JSON portable.

Uso:
    python scripts/export_full_database.py
    python scripts/export_full_database.py --output /tmp/cce-m5-export.json
    python scripts/export_full_database.py --db /ruta/custom/db.sqlite3 --output ./backup.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _load_settings():
    """Carga src.config.settings sin depender de PYTHONPATH."""
    project_root = Path(__file__).resolve().parents[1]
    module_path = project_root / "src" / "config.py"
    spec = importlib.util.spec_from_file_location("src.config", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar src.config desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["src.config"] = module
    spec.loader.exec_module(module)
    return module.settings


settings = _load_settings()


def _default_encoder(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _get_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [row[0] for row in cur.fetchall()]


def _get_schema(conn: sqlite3.Connection) -> dict[str, str]:
    cur = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%' ORDER BY type, name"
    )
    return {name: sql or "" for name, sql in cur.fetchall()}


def _export_table(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute(f"SELECT * FROM {table}")
    rows = [dict(row) for row in cur.fetchall()]
    conn.row_factory = None
    return rows


def export_database(db_path: Path, output_path: Path) -> dict[str, Any]:
    """Exporta esquema y datos a un diccionario JSON-serializable."""
    # No usamos PARSE_DECLTYPES para evitar conversiones problemáticas de TIMESTAMP.
    conn = sqlite3.connect(str(db_path))
    try:
        tables = _get_tables(conn)
        export = {
            "meta": {
                "source_db": str(db_path),
                "exported_at": datetime.now().isoformat(),
            },
            "schema": _get_schema(conn),
            "data": {table: _export_table(conn, table) for table in tables},
        }
    finally:
        conn.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(export, ensure_ascii=False, indent=2, default=_default_encoder),
        encoding="utf-8",
    )
    return export


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exporta la BD SQLite de CCE-M5 a JSON.")
    parser.add_argument(
        "--db",
        type=Path,
        default=settings.db_path,
        help="Ruta a la base de datos SQLite (default: settings.db_path)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=settings.project_dir / "backups" / "full_export.json",
        help="Ruta de salida del JSON (default: project_dir/backups/full_export.json)",
    )
    args = parser.parse_args(argv)

    export = export_database(args.db, args.output)
    total_rows = sum(len(rows) for rows in export["data"].values())
    print(f"Exportado {args.db} -> {args.output}")
    print(f"Tablas: {len(export['data'])} | Filas totales: {total_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
