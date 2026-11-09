"""Tests para src/canciones_manager.py."""

from __future__ import annotations

import importlib
import os
import sqlite3
from pathlib import Path

import pytest

from src import db_manager


@pytest.fixture
def canciones_manager(tmp_path: Path, monkeypatch):
    """Devuelve canciones_manager apuntando a una DB temporal."""
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))
    importlib.reload(db_manager)
    from src import canciones_manager as cm

    importlib.reload(cm)
    # Forzar DB_PATH y PROJECT_DIR temporales (se calculan en importación)
    monkeypatch.setattr(cm, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(cm, "DB_PATH", tmp_path / "data" / "db.sqlite3")
    # Copiar schema.sql del proyecto para que init_database lo use
    schema_src = Path(__file__).resolve().parents[2] / "data" / "schema.sql"
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())
    db_manager.init_database(cm.DB_PATH)
    return cm


def test_slugify(canciones_manager) -> None:
    assert canciones_manager.slugify("Aleluya, Aleluya") == "aleluya-aleluya"
    assert canciones_manager.slugify("  MARÍA  ") == "maria"
    assert canciones_manager.slugify("") == ""


def test_regenerar_derivados_con_acordes(canciones_manager) -> None:
    texto = """
Am
Aleluya, aleluya
""".strip()
    derivados = canciones_manager._regenerar_derivados(texto)
    assert "html_visual" in derivados
    assert "estructura_json" in derivados
    assert derivados["letra_sin_acordes"].strip() == "Aleluya, aleluya"
    assert derivados["tono"] is not None


def test_crear_y_obtener_cancion(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(
        titulo="Canción de prueba",
        letra_con_acordes="\nAm\nLínea de prueba\n",
        momentos=["entrada", "comunion"],
        tono="Am",
    )
    cancion = canciones_manager.crear_cancion(data)
    assert cancion["id"] > 0
    assert cancion["titulo"] == "Canción de prueba"
    assert cancion["slug"] == "cancion-de-prueba"
    assert set(cancion["momentos"]) == {"entrada", "comunion"}
    assert cancion["tono"] == "Am"

    obtenida = canciones_manager.obtener_cancion(cancion["id"])
    assert obtenida["titulo"] == "Canción de prueba"


def test_crear_cancion_sin_titulo(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(titulo="   ", letra_con_acordes="Am\nTexto")
    with pytest.raises(ValueError, match="título"):
        canciones_manager.crear_cancion(data)


def test_actualizar_cancion(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(
        titulo="Original",
        letra_con_acordes="\nAm\nOriginal\n",
    )
    creada = canciones_manager.crear_cancion(data)

    actualizada = canciones_manager.actualizar_cancion(
        creada["id"],
        canciones_manager.CancionCreateUpdate(
            titulo="Actualizada",
            letra_con_acordes="\nC\nActualizada\n",
            momentos=["gloria"],
            tono="C",
        ),
    )
    assert actualizada["titulo"] == "Actualizada"
    assert actualizada["tono"] == "C"
    assert actualizada["momentos"] == ["gloria"]


def test_actualizar_cancion_inexistente(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(
        titulo="X", letra_con_acordes="Am\nX"
    )
    with pytest.raises(ValueError, match="No existe canción"):
        canciones_manager.actualizar_cancion(9999, data)


def test_eliminar_cancion(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(
        titulo="Para borrar", letra_con_acordes="Am\nBorrar"
    )
    creada = canciones_manager.crear_cancion(data)
    canciones_manager.eliminar_cancion(creada["id"])

    with pytest.raises(ValueError, match="No existe canción"):
        canciones_manager.obtener_cancion(creada["id"])

    with pytest.raises(ValueError, match="No existe canción"):
        canciones_manager.eliminar_cancion(creada["id"])


def test_listar_canciones(canciones_manager) -> None:
    base = canciones_manager.listar_canciones()
    base_len = len(base)

    canciones_manager.crear_cancion(
        canciones_manager.CancionCreateUpdate(
            titulo="Bbb", letra_con_acordes="Am\nBbb"
        )
    )
    canciones_manager.crear_cancion(
        canciones_manager.CancionCreateUpdate(
            titulo="Aaa", letra_con_acordes="Am\nAaa"
        )
    )

    lista = canciones_manager.listar_canciones()
    assert len(lista) == base_len + 2
    titulos = {c["titulo"] for c in lista}
    assert "Aaa" in titulos
    assert "Bbb" in titulos


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


def test_obtener_cancion_inexistente_cierra_la_conexion(
    canciones_manager, monkeypatch
) -> None:
    """obtener_cancion debe cerrar su conexión aunque la canción no exista.

    DA-007: un `conn = _get_connection()` sin finally no cierra en el camino
    del error; sin close() determinista la conexión queda viva hasta GC
    (ciclo del _lru_cache_wrapper de CPython 3.13) y mantiene el -wal.
    Señal: sin GC no debe quedar ni conexión abierta ni file descriptor
    apuntando a la BD temporal.
    """
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("conteo de fds requiere /proc/self/fd (Linux)")

    opened: list[sqlite3.Connection] = []
    real_connect = sqlite3.connect

    def _traced(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", _traced)

    root = Path(canciones_manager.PROJECT_DIR)
    baseline = _sqlite_fd_count(root)
    assert baseline == 0, f"{baseline} fds apuntan a la BD antes de la llamada"

    with pytest.raises(ValueError, match="No existe canción"):
        canciones_manager.obtener_cancion(9999)

    for conn in opened:
        try:
            conn.execute("SELECT 1")
            is_open = True
        except sqlite3.ProgrammingError:
            is_open = False
        assert not is_open, (
            "obtener_cancion deja su conexión abierta sin GC: el -wal queda vivo (DA-007)"
        )

    remaining = _sqlite_fd_count(root)
    assert remaining == 0, (
        f"quedan {remaining} file descriptors apuntando a la BD tras la llamada "
        f"sin GC: la conexión no se cerró de forma determinista"
    )
