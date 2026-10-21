#!/usr/bin/env python3
"""Importa una exportación JSON de la base de datos a una SQLite vacía.

Uso:
    python scripts/import_full_database.py --input /tmp/cce-m5-export.json
    python scripts/import_full_database.py --input /tmp/cce-m5-export.json --db /ruta/custom/db.sqlite3
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import sys
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


def _quote_identifier(name: str) -> str:
    """Escapa un identificador SQL (nombre de tabla/columna)."""
    return '"' + name.replace('"', '""') + '"'


def _create_schema(conn: sqlite3.Connection, schema: dict[str, str]) -> None:
    """Recrea tablas e índices del esquema exportado. Crea tablas primero."""
    tables = {name: sql for name, sql in schema.items() if sql and sql.strip().upper().startswith("CREATE TABLE")}
    indexes = {name: sql for name, sql in schema.items() if sql and sql.strip().upper().startswith("CREATE INDEX")}
    for sql in tables.values():
        conn.execute(sql)
    for sql in indexes.values():
        conn.execute(sql)


def _clear_tables(conn: sqlite3.Connection, tables: list[str]) -> None:
    """Borra datos de todas las tablas en orden inverso para evitar FK errors."""
    for table in reversed(tables):
        conn.execute(f"DELETE FROM {_quote_identifier(table)}")


def _insert_table(conn: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> int:
    """Inserta filas en una tabla. Ignora filas con ID duplicado (INSERT OR REPLACE)."""
    if not rows:
        return 0
    columns = list(rows[0].keys())
    quoted_cols = ", ".join(_quote_identifier(c) for c in columns)
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT OR REPLACE INTO {_quote_identifier(table)} ({quoted_cols}) VALUES ({placeholders})"
    values = [[row.get(c) for c in columns] for row in rows]
    conn.executemany(sql, values)
    return len(rows)


def import_database(input_path: Path, db_path: Path, *, wipe: bool = False) -> dict[str, Any]:
    """Importa el JSON a la base de datos. Crea DB si no existe."""
    data = json.loads(input_path.read_text(encoding="utf-8"))
    schema = data.get("schema", {})
    tables = data.get("data", {})

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        if wipe:
            # Si se pide wipe, recreamos el esquema desde cero.
            for name in sorted(schema.keys(), reverse=True):
                conn.execute(f"DROP TABLE IF EXISTS {_quote_identifier(name)}")
            _create_schema(conn, schema)
        else:
            # Asumimos que la BD ya existe con el esquema adecuado.
            # Si no, lo creamos.
            existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if not existing:
                _create_schema(conn, schema)

        # Orden de inserción: tablas padre primero, luego hijas.
        # Usamos el orden del esquema exportado (alfabético) que es seguro gracias a PRAGMA foreign_keys=OFF.
        conn.execute("PRAGMA foreign_keys = OFF")
        _clear_tables(conn, list(tables.keys()))
        counts = {}
        for table, rows in tables.items():
            counts[table] = _insert_table(conn, table, rows)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
    finally:
        conn.close()

    return {
        "db_path": str(db_path),
        "input_path": str(input_path),
        "tables": counts,
        "total_rows": sum(counts.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Importa una exportación JSON de CCE-M5 a SQLite.")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Ruta al JSON exportado con scripts/export_full_database.py",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=settings.db_path,
        help="Ruta a la base de datos destino (default: settings.db_path)",
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Borra y recrea el esquema antes de importar (destructivo)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma automáticamente la importación",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"No existe el archivo de entrada: {args.input}", file=__import__("sys").stderr)
        return 1

    if args.db.exists() and not args.yes:
        answer = input(f"{args.db} ya existe. ¿Sobrescribir datos? [s/N]: ")
        if answer.lower() not in {"s", "si", "yes", "y"}:
            print("Importación cancelada.")
            return 0

    result = import_database(args.input, args.db, wipe=args.wipe)
    print(f"Importado {args.input} -> {args.db}")
    print(f"Tablas: {len(result['tables'])} | Filas totales: {result['total_rows']}")
    for table, count in sorted(result["tables"].items()):
        print(f"  {table}: {count} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
