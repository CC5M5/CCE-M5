"""Regression test: the canonical seed contains the 2026-11-01 presentation (spec S1)."""

import sqlite3
from pathlib import Path

SEED = Path(__file__).resolve().parents[2] / "data" / "seeds" / "db.empty.sqlite3"


def _conn():
    return sqlite3.connect(f"file:{SEED}?mode=ro", uri=True)


def test_seed_contains_2026_11_01_as_publicada():
    conn = _conn()
    row = conn.execute(
        "SELECT id, estado FROM presentaciones WHERE fecha_domingo = '2026-11-01'"
    ).fetchone()
    assert row is not None, "2026-11-01 missing from canonical seed"
    assert row[1] == "publicada"


def test_seed_2026_11_01_has_composition_slides():
    conn = _conn()
    n = conn.execute(
        """
        SELECT COUNT(*)
        FROM presentacion_slides ps
        JOIN presentaciones p ON ps.presentacion_id = p.id
        WHERE p.fecha_domingo = '2026-11-01'
        """
    ).fetchone()[0]
    assert n == 28
