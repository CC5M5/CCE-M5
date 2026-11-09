"""Tests de cierre determinista de conexiones SQLite (DA-007) para los generadores.

Cobren composicion_catalogo, generar_desde_composicion, pdf_musicos y
presentacion/builder. Estilo fd-conteo (/proc/self/fd) con espía de
sqlite3.connect, modelado en
test_db_manager::test_init_database_cierra_la_conexion_que_abre y
test_web_admin_api::test_lifespan_startup_cierra_conexiones: una conexión
viva hasta GC (ciclo del functools._lru_cache_wrapper de CPython 3.13)
mantiene el -wal; el close() determinista no.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from src import db_manager

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_SCHEMA = _REPO_ROOT / "data" / "schema.sql"


def _init_tmp_db(db_path: Path) -> None:
    """Crea la BD temporal con el esquema real del repo, leyendo el archivo
    directamente por ruta absoluta del repo: no pasa por src.config ni por
    db_manager porque la suite completa recarga src.config con un proyecto
    temporal muerto (test_editores_endpoints) y re-derivar SCHEMA_PATH/DB_PATH
    de ese estado inicializa una BD sin el esquema completo."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_REAL_SCHEMA.read_text())
        conn.commit()
    finally:
        conn.close()


def _sqlite_fd_count(root: Path) -> int:
    """Cuenta file descriptors del proceso que apuntan a la BD bajo root.

    Cubre `db.sqlite3`, `db.sqlite3-wal` y `db.sqlite3-shm`. `close()` libera
    el fd de forma determinista incluso con ciclos de referencias, así que
    esta señal no depende de GC. Devuelve -1 si `/proc/self/fd` no está
    disponible.
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


def _spy_sqlite_connect(monkeypatch: pytest.MonkeyPatch) -> list[sqlite3.Connection]:
    """Espía sqlite3.connect y devuelve la lista de conexiones abiertas."""
    opened: list[sqlite3.Connection] = []
    real_connect = sqlite3.connect

    def _traced(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", _traced)
    return opened


def _assert_conexiones_cerradas(opened: list[sqlite3.Connection], contexto: str) -> None:
    for conn in opened:
        try:
            conn.execute("SELECT 1")
            is_open = True
        except sqlite3.ProgrammingError:
            is_open = False
        assert not is_open, (
            f"{contexto} deja su conexión abierta sin GC: el -wal queda vivo (DA-007)"
        )


@pytest.fixture
def cc_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """composicion_catalogo apuntando a una BD temporal con una presentación.

    Sin reload de src.config/db_manager (la suite completa los recarga con un
    proyecto temporal muerto); solo se parchea el global DB_PATH del módulo
    objetivo."""
    db_path = tmp_path / "data" / "db.sqlite3"
    _init_tmp_db(db_path)

    from src.generators import composicion_catalogo as cc

    monkeypatch.setattr(cc, "DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO presentaciones (fecha_domingo, canciones_json) VALUES (?, ?)",
                ("2026-11-15", json.dumps({"entrada": 1})),
            )
    finally:
        conn.close()
    return cc


@pytest.fixture
def gcd_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """generar_desde_composicion apuntando a una BD temporal (sin presentaciones)."""
    db_path = tmp_path / "data" / "db.sqlite3"
    _init_tmp_db(db_path)

    from src.generators import generar_desde_composicion as gcd

    monkeypatch.setattr(gcd, "DB_PATH", db_path)
    return gcd


@pytest.fixture
def pdf_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """pdf_musicos: su get_connection() lee el global DB_PATH de db_manager.

    Sin reload de db_manager ni pdf_musicos: el reload crea identidades
    nuevas de las clases de excepción y otros tests (test_pdf_musicos_fonts)
    ya importaron las del módulo original."""
    db_path = tmp_path / "data" / "db.sqlite3"
    _init_tmp_db(db_path)

    from src.generators import pdf_musicos

    monkeypatch.setattr(db_manager, "DB_PATH", db_path)
    return pdf_musicos


@pytest.fixture
def builder_module():
    """presentacion/builder: cada test pinta su propio DB_PATH (BD vacía)."""
    from src.generators.presentacion import builder

    return builder


def test_guardar_composicion_cierra_la_conexion_en_error(
    cc_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """guardar_composicion debe cerrar su conexión aunque el item sea inválido.

    Un item con slide_id pero sin "numero" lanza KeyError con la conexión
    abierta. DA-007: sin close() determinista la conexión queda viva hasta
    GC y mantiene el -wal.
    """
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("conteo de fds requiere /proc/self/fd (Linux)")

    opened = _spy_sqlite_connect(monkeypatch)
    baseline = _sqlite_fd_count(tmp_path)
    assert baseline == 0, f"{baseline} fds apuntan a la BD antes de la llamada"

    with pytest.raises(KeyError):
        cc_module.guardar_composicion("2026-11-15", [{"slide_id": 1}])

    _assert_conexiones_cerradas(opened, "guardar_composicion")

    remaining = _sqlite_fd_count(tmp_path)
    assert remaining == 0, (
        f"quedan {remaining} file descriptors apuntando a la BD tras la llamada "
        f"sin GC: la conexión no se cerró de forma determinista"
    )


def test_generar_desde_presentacion_cierra_la_conexion_en_error(
    gcd_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """generar_desde_presentacion debe cerrar su conexión si la fecha no existe.

    Con una fecha sin presentación, la lectura inicial lanza ValueError con
    la conexión abierta. DA-007: sin close() determinista la conexión queda
    viva hasta GC y mantiene el -wal.
    """
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("conteo de fds requiere /proc/self/fd (Linux)")

    opened = _spy_sqlite_connect(monkeypatch)
    baseline = _sqlite_fd_count(tmp_path)
    assert baseline == 0, f"{baseline} fds apuntan a la BD antes de la llamada"

    with pytest.raises(ValueError, match="No existe presentación"):
        gcd_module.GeneradorDesdeComposicion().generar_desde_presentacion("1999-01-03")

    _assert_conexiones_cerradas(opened, "generar_desde_presentacion")

    remaining = _sqlite_fd_count(tmp_path)
    assert remaining == 0, (
        f"quedan {remaining} file descriptors apuntando a la BD tras la llamada "
        f"sin GC: la conexión no se cerró de forma determinista"
    )


def test_generar_hoja_musicos_cierra_la_conexion_en_error(
    pdf_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """generar_hoja_musicos debe cerrar la conexión de get_connection().

    `with get_connection() as conn:` solo gestiona la transacción y no
    cierra: si _cargar_canciones lanza CancionNoEncontradaError (canción
    inexistente), la conexión queda viva hasta GC. DA-007.
    """
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("conteo de fds requiere /proc/self/fd (Linux)")

    opened = _spy_sqlite_connect(monkeypatch)
    baseline = _sqlite_fd_count(tmp_path)
    assert baseline == 0, f"{baseline} fds apuntan a la BD antes de la llamada"

    with pytest.raises(pdf_module.CancionNoEncontradaError):
        pdf_module.generar_hoja_musicos(
            "1999-01-03",
            {"entrada": 9999},
            output_path=tmp_path / "hoja_musicos.pdf",
        )

    _assert_conexiones_cerradas(opened, "generar_hoja_musicos")

    remaining = _sqlite_fd_count(tmp_path)
    assert remaining == 0, (
        f"quedan {remaining} file descriptors apuntando a la BD tras la llamada "
        f"sin GC: la conexión no se cerró de forma determinista"
    )


def test_builder_generar_cierra_la_conexion_en_error(
    builder_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """builder.generar (vía _get_lectura) debe cerrar su conexión si falla la BD.

    Con una BD vacía (sin tablas) el SELECT de lecturas lanza
    sqlite3.OperationalError con la conexión abierta. DA-007: sin close()
    determinista la conexión queda viva hasta GC y mantiene el -wal.
    """
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("conteo de fds requiere /proc/self/fd (Linux)")

    empty_db = tmp_path / "empty.sqlite3"
    sqlite3.connect(str(empty_db)).close()
    monkeypatch.setattr(builder_module, "DB_PATH", empty_db)

    opened = _spy_sqlite_connect(monkeypatch)
    baseline = _sqlite_fd_count(tmp_path)
    assert baseline == 0, f"{baseline} fds apuntan a la BD antes de la llamada"

    with pytest.raises(sqlite3.OperationalError):
        builder_module.generar(None, None, "2026-01-04", 1, {})

    _assert_conexiones_cerradas(opened, "builder.generar")

    remaining = _sqlite_fd_count(tmp_path)
    assert remaining == 0, (
        f"quedan {remaining} file descriptors apuntando a la BD tras la llamada "
        f"sin GC: la conexión no se cerró de forma determinista"
    )
