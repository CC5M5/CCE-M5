"""Backup WAL-consistente de data/db.sqlite3.

Usa `sqlite3.Connection.backup()` para producir una copia atómica y
consistente de la base de datos aunque esta esté viva en modo WAL,
la comprime con gzip en CCE_BACKUP_DIR, la deja con permisos 600 y
aplica retención de CCE_BACKUP_KEEP_DAYS días (por defecto 30).

Variables de entorno (o flags de línea de comandos):
  CCE_PROJECT_DIR       (default ~/proyectos/CCE-M5-Web-Presentaciones)
  CCE_BACKUP_DIR        (default ~/.config/cce-m5/backups/db)
  CCE_BACKUP_KEEP_DAYS  (default 30)
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DEFAULT_PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
DEFAULT_BACKUP_DIR = Path.home() / ".config" / "cce-m5" / "backups" / "db"
DEFAULT_KEEP_DAYS = 30


def _db_path(project_dir: Path) -> Path:
    return project_dir / "data" / "db.sqlite3"


def backup_database(src: Path, dest_plain: Path) -> None:
    """Copia consistente de `src` en `dest_plain` (archivo SQLite sin comprimir).

    Verifica `PRAGMA integrity_check` en la copia antes de dejarla en su sitio.
    """
    source = sqlite3.connect(str(src))
    try:
        part = dest_plain.with_name(dest_plain.name + ".part")
        dest = sqlite3.connect(str(part))
        try:
            source.backup(dest)
        finally:
            dest.close()

        verify = sqlite3.connect(str(part))
        try:
            integrity = verify.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            verify.close()
        if integrity != "ok":
            part.unlink(missing_ok=True)
            raise sqlite3.DatabaseError(f"integrity_check de la copia falló: {integrity}")

        os.replace(part, dest_plain)
    finally:
        source.close()


def _prune_old_backups(dest_dir: Path, keep_days: int) -> None:
    """Elimina backups `db_*.sqlite3.gz` más antiguos que `keep_days` días."""
    cutoff = time.time() - keep_days * 86400
    for path in dest_dir.glob("db_*.sqlite3.gz"):
        if path.stat().st_mtime < cutoff:
            path.unlink()


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=None)
    parser.add_argument("--dest-dir", type=Path, default=None)
    parser.add_argument("--keep-days", type=int, default=None)
    args = parser.parse_args(argv)

    src = args.src or _db_path(Path(os.environ.get("CCE_PROJECT_DIR", str(DEFAULT_PROJECT_DIR))))
    dest_dir = Path(
        args.dest_dir
        or os.environ.get("CCE_BACKUP_DIR", str(DEFAULT_BACKUP_DIR))
    )
    keep_days = args.keep_days
    if keep_days is None:
        keep_days = int(os.environ.get("CCE_BACKUP_KEEP_DAYS", str(DEFAULT_KEEP_DAYS)))

    if not src.is_file():
        print(f"ERROR: no existe {src}", flush=True)
        raise SystemExit(1)

    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"db_{ts}.sqlite3.gz"
    plain = dest_dir / f"db_{ts}.sqlite3"

    backup_database(src, plain)
    with gzip.open(dest, "wb") as out, open(plain, "rb") as f:
        shutil.copyfileobj(f, out)
    plain.unlink()
    os.chmod(dest, 0o600)

    _prune_old_backups(dest_dir, keep_days)
    print(f"Backup creado: {dest}")
    return dest


if __name__ == "__main__":
    main()
