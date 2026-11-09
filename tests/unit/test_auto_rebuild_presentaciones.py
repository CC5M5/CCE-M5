"""Tests para src/auto_rebuild_presentaciones.py."""

from __future__ import annotations

import importlib
import json
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src import db_manager


@pytest.fixture
def arb_module(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))
    # Copiar schema.sql real al proyecto temporal
    schema_src = Path(__file__).resolve().parents[2] / "data" / "schema.sql"
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())
    importlib.reload(db_manager)
    from src import auto_rebuild_presentaciones as arb

    importlib.reload(arb)
    db_manager.init_database(arb.DB_PATH)
    return arb


def test_limpiar_letra_priorities(arb_module) -> None:
    arb = arb_module
    assert arb._limpiar_letra("<p>Hola</p>", None, None) == "Hola"
    assert arb._limpiar_letra(None, "letra limpia", None) == "letra limpia"
    assert arb._limpiar_letra(None, None, "con acordes") == "con acordes"
    assert arb._limpiar_letra(None, None, None) == ""


def test_canciones_asignadas(arb_module) -> None:
    arb = arb_module
    assert arb._canciones_asignadas(None) == {}
    assert arb._canciones_asignadas("invalid") == {}
    assert arb._canciones_asignadas('{"entrada": {"id": 5}, "comunion": 7, "paz": "9"}') == {
        "entrada": 5,
        "comunion": 7,
        "paz": 9,
    }
    assert arb._canciones_asignadas("[]") == {}


def test_crear_slides_para_cancion(arb_module) -> None:
    arb = arb_module
    conn = db_manager.create_connection(arb.DB_PATH)
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO canciones (titulo, html_visual, letra_sin_acordes, letra_con_acordes) VALUES (?, ?, ?, ?)",
            ("Aleluya", "<b>Aleluya</b>", "Aleluya", "Am\nAleluya"),
        )
        cid = cur.lastrowid
        cur.executemany(
            "INSERT INTO cancion_momentos (cancion_id, momento_liturgico) VALUES (?, ?)",
            [(cid, "entrada"), (cid, "comunion"), (cid, "acto_penitencial")],
        )
    conn.close()

    slides = arb.crear_slides_para_cancion(cid)
    assert len(slides) == 3
    momentos = {s[0] for s in slides}
    assert momentos == {"entrada", "comunion", "perdon"}

    # Idempotente
    slides2 = arb.crear_slides_para_cancion(cid)
    assert len(slides2) == 3


def test_encontrar_presentaciones_afectadas(arb_module) -> None:
    arb = arb_module
    conn = db_manager.create_connection(arb.DB_PATH)
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO canciones (titulo) VALUES (?)", ("Canción A",)
        )
        cid = cur.lastrowid
        future = (date.today() + timedelta(days=7)).isoformat()
        past = (date.today() - timedelta(days=7)).isoformat()
        cur.execute(
            "INSERT INTO presentaciones (fecha_domingo, canciones_json) VALUES (?, ?)",
            (future, json.dumps({"entrada": {"id": cid}})),
        )
        cur.execute(
            "INSERT INTO presentaciones (fecha_domingo, canciones_json) VALUES (?, ?)",
            (past, json.dumps({"entrada": {"id": cid}})),
        )
    conn.close()

    afectadas = arb.encontrar_presentaciones_afectadas(cid, solo_futuras=True)
    assert len(afectadas) == 1
    assert afectadas[0]["fecha_domingo"] == future

    todas = arb.encontrar_presentaciones_afectadas(cid, solo_futuras=False)
    assert len(todas) == 2


def test_auto_rebuild_tras_cancion(arb_module, monkeypatch) -> None:
    arb = arb_module
    conn = db_manager.create_connection(arb.DB_PATH)
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO canciones (titulo, html_visual) VALUES (?, ?)",
            ("Canción B", "<p>Texto</p>"),
        )
        cid = cur.lastrowid
        cur.execute(
            "INSERT INTO cancion_momentos (cancion_id, momento_liturgico) VALUES (?, ?)",
            (cid, "entrada"),
        )
        future = (date.today() + timedelta(days=7)).isoformat()
        cur.execute(
            "INSERT INTO presentaciones (fecha_domingo, canciones_json) VALUES (?, ?)",
            (future, json.dumps({"entrada": {"id": cid}})),
        )
    conn.close()

    with (
        patch.object(arb_module, "proponer_composicion", return_value=[{"tipo": "entrada", "slide_id": 1}]),
        patch.object(arb_module, "guardar_composicion"),
        patch.object(arb_module.GeneradorDesdeComposicion, "generar_desde_presentacion", return_value=None),
    ):
        result = arb.auto_rebuild_tras_cancion(cid, solo_futuras=True)

    assert len(result["slides_creadas"]) == 1
    assert future in result["presentaciones_afectadas"]
    assert result["resultados"][0]["status"] == "ok"


def _sqlite_fd_count(root: Path) -> int:
    """Cuenta file descriptors del proceso que apuntan a la BD bajo root.

    Cubre `db.sqlite3`, `db.sqlite3-wal` y `db.sqlite3-shm`. `close()` libera
    el fd de forma determinista incluso con ciclos de referencias (el
    functools._lru_cache_wrapper de CPython 3.13), así que esta señal no
    depende de GC. Devuelve -1 si `/proc/self/fd` no está disponible.
    """
    fd_dir = Path("/proc/self/fd")
    if not fd_dir.is_dir():
        return -1
    prefix = os.path.abspath(str(root))
    count = 0
    for entry in os.listdir(fd_dir):
        try:
            target = os.readlink(fd_dir / entry)
        except OSError:
            continue
        if target.startswith(prefix) and target.endswith(
            (".sqlite3", ".sqlite3-wal", ".sqlite3-shm")
        ):
            count += 1
    return count


def test_crear_slides_para_cancion_cierra_la_conexion_en_error(
    arb_module, tmp_path, monkeypatch
) -> None:
    """crear_slides_para_cancion debe cerrar su conexión aunque falle la BD.

    DA-007: con una BD vacía (sin tablas) el SELECT inicial lanza
    sqlite3.OperationalError con la conexión abierta; sin close() determinista
    la conexión queda viva hasta GC (ciclo del _lru_cache_wrapper de CPython
    3.13) y mantiene el -wal. Señal: sin GC no debe quedar ni conexión abierta
    ni file descriptor apuntando a la BD temporal.
    """
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("conteo de fds requiere /proc/self/fd (Linux)")

    arb = arb_module
    empty_db = tmp_path / "empty.sqlite3"
    sqlite3.connect(str(empty_db)).close()
    monkeypatch.setattr(arb, "DB_PATH", empty_db)

    opened: list[sqlite3.Connection] = []
    real_connect = sqlite3.connect

    def _traced(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", _traced)

    baseline = _sqlite_fd_count(tmp_path)
    assert baseline == 0, f"{baseline} fds apuntan a la BD antes de la llamada"

    with pytest.raises(sqlite3.OperationalError):
        arb.crear_slides_para_cancion(1)

    for conn in opened:
        try:
            conn.execute("SELECT 1")
            is_open = True
        except sqlite3.ProgrammingError:
            is_open = False
        assert not is_open, (
            "crear_slides_para_cancion deja su conexión abierta sin GC: "
            "el -wal queda vivo (DA-007)"
        )

    remaining = _sqlite_fd_count(tmp_path)
    assert remaining == 0, (
        f"quedan {remaining} file descriptors apuntando a la BD tras la llamada "
        f"sin GC: la conexión no se cerró de forma determinista"
    )
