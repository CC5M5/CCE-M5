"""Tests para utilidades compartidas de editores Flask."""

from __future__ import annotations

import json
import sqlite3
import subprocess

import pytest

from src.web_admin.editores import (
    get_connection,
    get_momentos_cancion,
    git_commit,
    set_momentos_cancion,
)
from src.web_admin.editores import git as git_mod


def _git_init(path: subprocess._FILE) -> None:
    """Inicializa un repo git en path y renombra la rama a main."""
    subprocess.run(["git", "init"], check=True, capture_output=True, cwd=path)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
        cwd=path,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True,
        capture_output=True,
        cwd=path,
    )
    subprocess.run(
        ["git", "branch", "-M", "main"],
        check=True,
        capture_output=True,
        cwd=path,
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


@pytest.fixture
def tmp_git_project(tmp_path, monkeypatch):
    """Crea un repo temporal con los JSON versionados ya commiteados."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "web" / "data").mkdir(parents=True)
    (tmp_path / "web" / "data" / "canciones.json").write_text(
        json.dumps([{"id": 1, "titulo": "Test"}]), encoding="utf-8"
    )
    (tmp_path / "web" / "data" / "cancion_momentos.json").write_text("[]", encoding="utf-8")
    (tmp_path / "web" / "data" / "presentaciones.json").write_text("[]", encoding="utf-8")
    (tmp_path / "web" / "data" / "comentarios.json").write_text("[]", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "db.sqlite3").write_text("x")

    _git_init(tmp_path)
    subprocess.run(
        ["git", "add", *git_mod.DEFAULT_VERSIONED_PATHS],
        check=True,
        capture_output=True,
        cwd=tmp_path,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        check=True,
        capture_output=True,
        cwd=tmp_path,
    )

    monkeypatch.setattr(git_mod, "PROJECT_DIR", tmp_path)
    return tmp_path


def test_git_commit_returns_sin_cambios_when_no_diff(tmp_git_project, monkeypatch):
    """git_commit debe devolver 'sin cambios' cuando los JSON no cambian."""
    monkeypatch.setattr(git_mod, "_git_push", lambda: ("ok", ""))
    result = git_commit("test commit")
    assert result == "sin cambios"


def test_git_commit_stages_json_not_sqlite(tmp_git_project, monkeypatch):
    """git_commit debe añadir los JSON versionados y nunca data/db.sqlite3."""
    project = tmp_git_project
    monkeypatch.setattr(git_mod, "_git_push", lambda: ("ok", ""))

    # Forzamos un cambio en los JSON.
    (project / "web" / "data" / "canciones.json").write_text(
        json.dumps([{"id": 1, "titulo": "Test modificado"}]), encoding="utf-8"
    )

    result = git_commit("test commit")
    assert result != "sin cambios"
    assert not result.startswith("ERROR")

    log = subprocess.run(
        ["git", "log", "--oneline", "-1", "--name-only"],
        check=True,
        capture_output=True,
        text=True,
        cwd=project,
    ).stdout.strip()
    assert "web/data/canciones.json" in log
    assert "data/db.sqlite3" not in log
