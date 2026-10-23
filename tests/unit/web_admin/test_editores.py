"""Tests para utilidades compartidas de editores Flask."""

from __future__ import annotations

import sqlite3

import pytest

from src.web_admin.editores import (
    get_connection,
    get_momentos_cancion,
    git_commit,
    set_momentos_cancion,
)


@pytest.fixture
def tmp_db_path(tmp_path, monkeypatch):
    db_path = tmp_path / "db.sqlite3"
    monkeypatch.setattr("src.web_admin.editores.db.DB_PATH", db_path)
    # Crear tablas mínimas
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE canciones (
            id INTEGER PRIMARY KEY,
            titulo TEXT,
            letra_con_acordes TEXT,
            html_visual TEXT,
            tono TEXT,
            momento_liturgico TEXT,
            titulo_url TEXT,
            slug TEXT
        );
        CREATE TABLE cancion_momentos (
            cancion_id INTEGER,
            momento_liturgico TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO canciones (id, titulo, slug) VALUES (?, ?, ?)", (1, "Test", "test")
    )
    conn.commit()
    conn.close()
    return db_path


def test_get_connection_returns_row_factory():
    conn = get_connection()
    assert conn.row_factory is not None
    conn.close()


def test_get_momentos_cancion_returns_list(tmp_db_path):
    momentos = get_momentos_cancion(1)
    assert isinstance(momentos, list)


def test_set_momentos_cancion_replaces_existing(tmp_db_path):
    set_momentos_cancion(1, ["entrada", "comunion"])
    assert set(get_momentos_cancion(1)) == {"comunion", "entrada"}

    set_momentos_cancion(1, ["paz"])
    assert get_momentos_cancion(1) == ["paz"]


def test_set_momentos_cancion_ignores_empty(tmp_db_path):
    set_momentos_cancion(1, ["", "  ", "ofertorio"])
    assert get_momentos_cancion(1) == ["ofertorio"]


def test_git_commit_returns_sin_cambios_when_no_diff(tmp_path, monkeypatch):
    """git_commit debe devolver 'sin cambios' cuando no hay nada staged."""
    import subprocess

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "db.sqlite3").write_text("x")
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True)
    subprocess.run(["git", "add", "data/db.sqlite3"], check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], check=True, capture_output=True)

    from src.web_admin import editores as editores_mod

    monkeypatch.setattr(editores_mod.git, "PROJECT_DIR", tmp_path)
    result = git_commit("test commit")
    assert result == "sin cambios"
