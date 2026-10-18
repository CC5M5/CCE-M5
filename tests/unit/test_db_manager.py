"""Tests para src/db_manager.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from src import db_manager


@pytest.fixture
def tmp_project(tmp_path: Path, monkeypatch):
    """Redirige db_manager a un proyecto temporal."""
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))
    import importlib

    importlib.reload(db_manager)
    return tmp_path


def test_create_connection_and_pragmas(tmp_project: Path) -> None:
    db_path = tmp_project / "data" / "test.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = db_manager.create_connection(db_path)
    assert conn is not None

    # Verificar pragmas
    journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert journal.lower() == "wal"
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1
    conn.close()


def test_validate_integrity_ok(tmp_project: Path) -> None:
    db_path = tmp_project / "data" / "test.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = db_manager.create_connection(db_path)
    db_manager._validate_integrity(conn)
    conn.close()


def test_init_database_with_schema_sql(tmp_project: Path) -> None:
    data_dir = tmp_project / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    schema_sql = """
        CREATE TABLE IF NOT EXISTS lecturas (id INTEGER PRIMARY KEY, fecha DATE UNIQUE);
        CREATE TABLE IF NOT EXISTS canciones (id INTEGER PRIMARY KEY, titulo TEXT);
    """
    (data_dir / "schema.sql").write_text(schema_sql)

    db_manager.init_database()
    db_path = data_dir / "db.sqlite3"
    assert db_path.exists()
    conn = db_manager.create_connection(db_path)
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "lecturas" in tables
    assert "canciones" in tables
    conn.close()


def test_init_database_without_schema_sql(tmp_project: Path) -> None:
    db_path = tmp_project / "data" / "db.sqlite3"
    db_manager.init_database(db_path)
    assert db_path.exists()
    conn = db_manager.create_connection(db_path)
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "lecturas" in tables
    assert "canciones" in tables
    assert "presentaciones" in tables
    assert "comentarios" in tables
    assert "automation_log" in tables
    assert "schema_version" in tables
    conn.close()


def test_add_column_if_missing(tmp_project: Path) -> None:
    db_path = tmp_project / "data" / "test.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = db_manager.create_connection(db_path)
    with conn:
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, nombre TEXT)")
    db_manager._add_column_if_missing(conn, "test_table", "nuevo", "TEXT")
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(test_table)").fetchall()}
    assert "nuevo" in cols
    # Idempotente
    db_manager._add_column_if_missing(conn, "test_table", "nuevo", "TEXT")
    conn.close()


def test_get_connection(tmp_project: Path) -> None:
    db_path = tmp_project / "data" / "db.sqlite3"
    db_manager.init_database(db_path)
    conn = db_manager.get_connection()
    assert conn is not None
    conn.close()
