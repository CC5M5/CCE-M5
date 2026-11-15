"""Regression test: the canonical seed contains the 2026-11-01 presentation (spec S1).

El estado de la presentación lo marca el workflow semanal del usuario
(publicada/generado/borrador) y cambia con el ciclo; el seed es espejo
de la DB viva y no debe congelar un estado histórico. La regresión que
se vigila aquí es que el seed siga conteniendo esa presentación con su
composición completa (decisión del usuario, 2026-11-15: antes se fijaba
"publicada", estado que el workflow ya había movido a "generado").
"""

import sqlite3
from pathlib import Path

SEED = Path(__file__).resolve().parents[2] / "data" / "seeds" / "db.empty.sqlite3"


def _conn():
    return sqlite3.connect(f"file:{SEED}?mode=ro", uri=True)


def test_seed_contains_2026_11_01():
    conn = _conn()
    row = conn.execute(
        "SELECT id, estado FROM presentaciones WHERE fecha_domingo = '2026-11-01'"
    ).fetchone()
    assert row is not None, "2026-11-01 missing from canonical seed"
    assert row[1] in ("publicada", "generado", "borrador")


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
