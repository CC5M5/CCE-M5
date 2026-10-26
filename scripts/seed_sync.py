#!/usr/bin/env python3
"""Mantiene `data/seeds/db.empty.sqlite3` sincronizado con `data/db.sqlite3`.

El seed es la base de datos canónica para CI, Docker y clones nuevos. Este script
la genera desde la BD de trabajo local cuando el usuario lo solicita, aplicando
validaciones para evitar pisar el seed accidentalmente con una BD vacía o corrupta.

El seed canónico contiene los datos litúrgicos y de canciones, pero limpia las
tablas de runtime/admin (usuarios, logs, workflow).

Uso:
    python scripts/seed_sync.py              # preview (solo informa diferencias)
    python scripts/seed_sync.py --apply      # actualiza el seed si es seguro
    python scripts/seed_sync.py --check    # exit 1 si el seed está desactualizado
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sqlite3
import sys
from pathlib import Path

from src.config import settings

SEED_PATH = settings.data_dir / "seeds" / "db.empty.sqlite3"
SOURCE_PATH = settings.db_path

MIN_SIZE_BYTES = 100_000
MIN_TABLES = 8

# Tablas de runtime/admin que no deben ir en un seed canónico limpio.
RUNTIME_TABLES = frozenset(
    {
        "admin_users",
        "automation_log",
        "workflow_runs",
        "workflow_logs",
        "workflow_backups",
    }
)


def _file_digest(path: Path) -> tuple[int, str]:
    """Devuelve (size_bytes, sha256) de un archivo."""
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def _count_tables(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return int(cur.fetchone()[0])


def _row_counts(conn: sqlite3.Connection) -> dict[str, int | str]:
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    counts: dict[str, int | str] = {}
    for table in tables:
        try:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.Error as exc:
            counts[table] = f"error: {exc}"
    return counts


def _validate_source(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        errors.append(f"No existe la BD fuente: {path}")
        return errors

    size = path.stat().st_size
    if size < MIN_SIZE_BYTES:
        errors.append(
            f"BD fuente muy pequeña ({size} bytes < {MIN_SIZE_BYTES}); "
            "parece vacía o corrupta."
        )

    conn = sqlite3.connect(str(path))
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            errors.append(f"integrity_check falló: {integrity}")

        if _count_tables(conn) < MIN_TABLES:
            errors.append("BD fuente no tiene el número mínimo de tablas esperado")

        counts = _row_counts(conn)
        for core_table in ("canciones", "lecturas", "slides"):
            count = counts.get(core_table, 0)
            if isinstance(count, int) and count == 0:
                errors.append(f"Tabla principal vacía: {core_table}")
    finally:
        conn.close()

    return errors


def _build_canonical_seed(source_path: Path, output_path: Path) -> dict[str, int]:
    """Copia la BD de trabajo a `output_path` limpiando tablas de runtime.

    Devuelve un diccionario {tabla: filas_borradas}.
    """
    if output_path.exists():
        output_path.unlink()
    shutil.copy2(source_path, output_path)
    conn = sqlite3.connect(str(output_path))
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        removed: dict[str, int] = {}
        for table in sorted(RUNTIME_TABLES):
            try:
                cur = conn.execute(f"DELETE FROM {table}")
                removed[table] = cur.rowcount
            except sqlite3.Error as exc:
                removed[table] = -1
                print(f"  advertencia: no se pudo limpiar {table}: {exc}", file=sys.stderr)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        conn.execute("VACUUM")
    finally:
        conn.close()
    return removed


def _compare() -> dict[str, object]:
    """Compara source vs seed y devuelve un resumen."""
    result: dict[str, object] = {
        "source_exists": SOURCE_PATH.exists(),
        "seed_exists": SEED_PATH.exists(),
        "source_size": 0,
        "seed_size": 0,
        "source_hash": "",
        "seed_hash": "",
        "seed_outdated": True,
        "source_ok": False,
        "source_errors": [],
    }

    if SOURCE_PATH.exists():
        result["source_size"], result["source_hash"] = _file_digest(SOURCE_PATH)
        result["source_errors"] = _validate_source(SOURCE_PATH)
        result["source_ok"] = not result["source_errors"]

    if SEED_PATH.exists():
        result["seed_size"], result["seed_hash"] = _file_digest(SEED_PATH)
        result["seed_outdated"] = result["source_hash"] != result["seed_hash"]
    else:
        result["seed_outdated"] = True

    return result


def _print_report(info: dict[str, object]) -> None:
    print(f"Fuente:  {SOURCE_PATH}")
    print(f"Seed:    {SEED_PATH}")
    print(f"Fuente existe:  {info['source_exists']}")
    print(f"Seed existe:    {info['seed_exists']}")
    print(f"Tamaño fuente:  {info['source_size']:,} bytes")
    print(f"Tamaño seed:    {info['seed_size']:,} bytes")
    print(f"Hash fuente:    {info['source_hash']}")
    print(f"Hash seed:      {info['seed_hash']}")
    print(f"Seed desactualizado: {info['seed_outdated']}")

    if info["source_errors"]:
        print("\nErrores de validación de la fuente:")
        for err in info["source_errors"]:
            print(f"  - {err}")

    if not info["source_errors"] and info["source_exists"]:
        counts = _row_counts(sqlite3.connect(str(SOURCE_PATH)))
        print("\nFilas en tablas principales:")
        for table in sorted(counts):
            print(f"  {table}: {counts[table]}")


def _apply_sync() -> int:
    info = _compare()
    if not info["seed_outdated"]:
        print("El seed ya está actualizado. No se realiza ningún cambio.")
        return 0

    errors = _validate_source(SOURCE_PATH)
    if errors:
        print("No se puede actualizar el seed por errores de validación:")
        for err in errors:
            print(f"  - {err}")
        return 1

    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    backup = SEED_PATH.with_suffix(f".sqlite3.backup.{Path(__file__).stem}")
    if SEED_PATH.exists():
        shutil.copy2(SEED_PATH, backup)
        print(f"Backup del seed anterior: {backup}")

    removed = _build_canonical_seed(SOURCE_PATH, SEED_PATH)
    print(f"Seed actualizado: {SEED_PATH}")
    for table, count in sorted(removed.items()):
        if count >= 0:
            print(f"  - limpiadas {count} filas de {table}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sincroniza el seed de CCE-M5")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="Actualiza el seed si es seguro")
    group.add_argument("--check", action="store_true", help="Exit 1 si el seed no coincide")
    parser.add_argument(
        "--from-db",
        type=Path,
        default=None,
        help="Usar otra base de datos como fuente en lugar de data/db.sqlite3",
    )
    args = parser.parse_args(argv)

    global SOURCE_PATH
    if args.from_db:
        SOURCE_PATH = args.from_db.resolve()

    info = _compare()
    _print_report(info)

    if args.check:
        return 1 if info["seed_outdated"] else 0

    if args.apply:
        if not info["seed_outdated"]:
            print("\nEl seed ya está actualizado. No se realiza ningún cambio.")
            return 0
        print("\nAplicando sincronización...")
        return _apply_sync()

    return 0


if __name__ == "__main__":
    sys.exit(main())
