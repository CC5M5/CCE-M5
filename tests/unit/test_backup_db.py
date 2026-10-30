"""Tests para scripts/backup_db.py (backup WAL-consistente)."""

import gzip
import os
import sqlite3
import time
from pathlib import Path

import pytest

from scripts import backup_db


def _make_db(path: Path, rows: list[tuple[int, str]]) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
    conn.executemany("INSERT INTO t (id, val) VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


def _read_back(gz_path: Path) -> list[tuple[int, str]]:
    tmp = gz_path.with_suffix(".sqlitedec")
    with gzip.open(gz_path, "rb") as f, open(tmp, "wb") as out:
        out.write(f.read())
    conn = sqlite3.connect(tmp)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        assert integrity == "ok"
        return conn.execute("SELECT id, val FROM t ORDER BY id").fetchall()
    finally:
        conn.close()
        tmp.unlink()


def test_backup_crea_gzip_consistente(tmp_path: Path):
    src = tmp_path / "src.sqlite3"
    _make_db(src, [(1, "a"), (2, "b")])
    dest_dir = tmp_path / "backups"

    dest = backup_db.main(["--src", str(src), "--dest-dir", str(dest_dir)])

    assert dest.suffix == ".gz"
    assert dest.exists()
    assert _read_back(dest) == [(1, "a"), (2, "b")]
    assert (os.stat(dest).st_mode & 0o777) == 0o600


def test_backup_incluye_datos_wal_cometidos(tmp_path: Path):
    """El backup de una DB viva en WAL incluye lo ya commitado."""
    src = tmp_path / "src.sqlite3"
    _make_db(src, [(1, "a")])
    live = sqlite3.connect(src)
    live.execute("PRAGMA journal_mode=WAL")
    live.execute("INSERT INTO t (id, val) VALUES (2, 'b')")
    live.commit()  # queda visible aunque la conexión siga abierta
    dest_dir = tmp_path / "backups"

    try:
        dest = backup_db.main(["--src", str(src), "--dest-dir", str(dest_dir)])
    finally:
        live.close()

    assert _read_back(dest) == [(1, "a"), (2, "b")]


def test_backup_sin_src_sale_1(tmp_path: Path):
    with pytest.raises(SystemExit) as exc_info:
        backup_db.main(
            ["--src", str(tmp_path / "no-existe.sqlite3"), "--dest-dir", str(tmp_path)]
        )
    assert exc_info.value.code == 1


def test_backup_retencion_por_dias(tmp_path: Path):
    src = tmp_path / "src.sqlite3"
    _make_db(src, [(1, "a")])
    dest_dir = tmp_path / "backups"
    old = dest_dir / "db_20200101_000000.sqlite3.gz"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes(b"antiguo")
    old_mtime = time.time() - 100 * 86400
    os.utime(old, (old_mtime, old_mtime))

    backup_db.main(["--src", str(src), "--dest-dir", str(dest_dir), "--keep-days", "30"])

    assert not old.exists()
    new = list(dest_dir.glob("db_*.sqlite3.gz"))
    assert len(new) == 1
