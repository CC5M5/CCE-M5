"""Pruebas unitarias para src/auto_rebuild_presentaciones.py.

Usan una base de datos temporal para no modificar data/db.sqlite3.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[2]


def _schema_base() -> str:
    schema_path = PROJECT_DIR / "data" / "schema.sql"
    if schema_path.exists():
        return schema_path.read_text()
    return ""


def _schema_slides() -> str:
    schema_path = PROJECT_DIR / "data" / "schema_slides.sql"
    if schema_path.exists():
        return schema_path.read_text()
    return ""


def _create_db(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    for statement in (_schema_base() + "\n" + _schema_slides()).split(";"):
        stmt = statement.strip()
        if stmt:
            c.execute(stmt)
    # Tablas/migraciones que existen en producción pero no en schema.sql base
    c.execute("""
        CREATE TABLE IF NOT EXISTS cancion_momentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cancion_id INTEGER NOT NULL,
            momento_liturgico TEXT NOT NULL,
            UNIQUE(cancion_id, momento_liturgico),
            FOREIGN KEY (cancion_id) REFERENCES canciones(id) ON DELETE CASCADE
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_cancion_momentos_cancion ON cancion_momentos(cancion_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cancion_momentos_momento ON cancion_momentos(momento_liturgico)")
    c.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cols_canciones = [r[1] for r in c.execute("PRAGMA table_info(canciones)").fetchall()]
    for col in ["html_visual", "estructura_json"]:
        if col not in cols_canciones:
            c.execute(f"ALTER TABLE canciones ADD COLUMN {col} TEXT")
    conn.commit()


def _insert_cancion(conn: sqlite3.Connection, titulo: str, momentos: list[str]) -> int:
    c = conn.cursor()
    c.execute(
        "INSERT INTO canciones (titulo, titulo_url, letra_con_acordes, letra_sin_acordes, html_visual, tono) VALUES (?, ?, ?, ?, ?, ?)",
        (titulo, "test", "letra", "LETRA LIMPIA", "<div>LETRA</div>", "Do"),
    )
    cid = c.lastrowid
    for m in momentos:
        c.execute(
            "INSERT INTO cancion_momentos (cancion_id, momento_liturgico) VALUES (?, ?)",
            (cid, m),
        )
    conn.commit()
    return cid


def _insert_presentacion(conn: sqlite3.Connection, fecha: str, canciones: dict, lectura_id: int = 1) -> int:
    c = conn.cursor()
    c.execute(
        "INSERT INTO presentaciones (fecha_domingo, lectura_id, estado, canciones_json) VALUES (?, ?, ?, ?)",
        (fecha, lectura_id, "generado", json.dumps(canciones)),
    )
    conn.commit()
    return c.lastrowid


def _insert_lectura(conn: sqlite3.Connection, fecha: str) -> int:
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO lecturas (
            fecha, domingo, temporada, color_liturgico,
            primera_lectura_cita, primera_lectura_texto,
            salmo_cita, salmo_antifona, salmo_texto,
            segunda_lectura_cita, segunda_lectura_texto,
            evangelio_cita, evangelio_texto
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fecha,
            "Domingo de prueba",
            "ordinario",
            "verde",
            "Gn 1,1",
            "En el principio...",
            "Sal 1",
            "Antífona",
            "Bienaventurado...",
            "Rom 8,1",
            "No hay condenación...",
            "Mt 5,1",
            "Viendo las multitudes...",
        ),
    )
    conn.commit()
    return c.lastrowid


def test_crear_slides_para_cancion():
    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
        conn = sqlite3.connect(tmp.name)
        _create_db(conn)
        cid = _insert_cancion(conn, "Canción de prueba", ["entrada", "comunion"])
        conn.close()

        with patch(
            "src.auto_rebuild_presentaciones.DB_PATH",
            Path(tmp.name),
        ):
            from src.auto_rebuild_presentaciones import crear_slides_para_cancion
            slides = crear_slides_para_cancion(cid)

        assert len(slides) == 2
        tipos = {s[0] for s in slides}
        assert tipos == {"entrada", "comunion"}

        conn = sqlite3.connect(tmp.name)
        c = conn.cursor()
        c.execute("SELECT tipo, subtipo, titulo FROM slides")
        rows = c.fetchall()
        conn.close()

        assert any(r[1] == f"cancion_{cid}" for r in rows)


def test_encontrar_presentaciones_afectadas():
    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
        conn = sqlite3.connect(tmp.name)
        _create_db(conn)
        cid = _insert_cancion(conn, "Otra prueba", ["entrada"])
        lid = _insert_lectura(conn, "2099-01-01")
        _insert_presentacion(conn, "2099-01-01", {"entrada": cid}, lid)
        lid2 = _insert_lectura(conn, "2020-01-01")
        _insert_presentacion(conn, "2020-01-01", {"entrada": cid}, lid2)
        conn.close()

        with patch(
            "src.auto_rebuild_presentaciones.DB_PATH",
            Path(tmp.name),
        ):
            from src.auto_rebuild_presentaciones import encontrar_presentaciones_afectadas
            afectadas = encontrar_presentaciones_afectadas(cid, solo_futuras=True)

        assert len(afectadas) == 1
        assert afectadas[0]["fecha_domingo"] == "2099-01-01"


def test_crear_slides_para_cancion_con_salmo():
    """Comprueba que 'salmo' se trata como momento con slide tras la modificación."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
        conn = sqlite3.connect(tmp.name)
        _create_db(conn)
        cid = _insert_cancion(conn, "Salmo canción", ["salmo"])
        conn.close()

        with patch(
            "src.auto_rebuild_presentaciones.DB_PATH",
            Path(tmp.name),
        ):
            from src.auto_rebuild_presentaciones import crear_slides_para_cancion
            slides = crear_slides_para_cancion(cid)

        assert len(slides) == 1
        assert slides[0][0] == "salmo"
