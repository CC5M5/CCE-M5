"""Tests para scripts/seed_sync.py."""

from __future__ import annotations

import sqlite3

import pytest

import scripts.seed_sync as seed_sync


@pytest.fixture
def sample_db(tmp_path):
    """Crea una BD mínima con tablas core y runtime para probar el seed."""
    db_path = tmp_path / "sample.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE canciones (id INTEGER PRIMARY KEY, titulo TEXT, letra_con_acordes TEXT);
        CREATE TABLE lecturas (id INTEGER PRIMARY KEY, fecha TEXT, primera_lectura_texto TEXT);
        CREATE TABLE slides (id INTEGER PRIMARY KEY, titulo TEXT, contenido TEXT);
        CREATE TABLE admin_users (id INTEGER PRIMARY KEY, username TEXT);
        CREATE TABLE automation_log (id INTEGER PRIMARY KEY, mensaje TEXT);
        CREATE TABLE workflow_runs (id INTEGER PRIMARY KEY, fecha_domingo TEXT);
        CREATE TABLE workflow_logs (id INTEGER PRIMARY KEY, message TEXT);
        CREATE TABLE workflow_backups (id INTEGER PRIMARY KEY, backup_path TEXT);

        INSERT INTO canciones VALUES (1, 'Canción 1', 'letra...'), (2, 'Canción 2', 'letra...');
        INSERT INTO lecturas VALUES (1, '2026-10-25', 'texto largo');
        INSERT INTO slides VALUES (1, 'Slide 1', 'contenido');
        INSERT INTO admin_users VALUES (1, 'admin');
        INSERT INTO workflow_runs VALUES (1, '2026-10-25');
        INSERT INTO workflow_logs VALUES (1, 'log');
        INSERT INTO workflow_backups VALUES (1, '/tmp/bak');
        """
    )
    # Rellenar con contenido hasta superar el umbral mínimo de validación.
    big_text = "x" * 2000
    for i in range(3, 60):
        conn.execute(
            "INSERT INTO canciones (id, titulo, letra_con_acordes) VALUES (?, ?, ?)",
            (i, f"Canción {i}", big_text),
        )
    for i in range(2, 30):
        conn.execute(
            "INSERT INTO lecturas (id, fecha, primera_lectura_texto) VALUES (?, ?, ?)",
            (i, f"2026-01-{i:02d}", big_text),
        )
    for i in range(2, 40):
        conn.execute(
            "INSERT INTO slides (id, titulo, contenido) VALUES (?, ?, ?)",
            (i, f"Slide {i}", big_text),
        )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def clean_paths(tmp_path, monkeypatch):
    """Redirige SOURCE_PATH y SEED_PATH a tmp_path."""
    monkeypatch.setattr(seed_sync, "SOURCE_PATH", tmp_path / "source.sqlite3")
    monkeypatch.setattr(seed_sync, "SEED_PATH", tmp_path / "seed.sqlite3")


def test_validate_source_rejects_empty(tmp_path):
    empty_db = tmp_path / "empty.sqlite3"
    sqlite3.connect(str(empty_db)).close()
    errors = seed_sync._validate_source(empty_db)
    assert any("muy pequeña" in err for err in errors)


def test_validate_source_accepts_valid_db(sample_db):
    errors = seed_sync._validate_source(sample_db)
    assert not errors


def test_build_canonical_seed_cleans_runtime_tables(sample_db, tmp_path):
    seed_path = tmp_path / "seed.sqlite3"
    removed = seed_sync._build_canonical_seed(sample_db, seed_path)
    assert removed["admin_users"] == 1
    assert removed["workflow_runs"] == 1
    assert removed["workflow_logs"] == 1
    assert removed["workflow_backups"] == 1

    conn = sqlite3.connect(str(seed_path))
    try:
        assert conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM canciones").fetchone()[0] == 59
    finally:
        conn.close()


def test_compare_detects_outdated_seed(sample_db, tmp_path, monkeypatch):
    monkeypatch.setattr(seed_sync, "SOURCE_PATH", sample_db)
    seed = tmp_path / "seed.sqlite3"
    monkeypatch.setattr(seed_sync, "SEED_PATH", seed)

    info = seed_sync._compare()
    assert info["seed_outdated"] is True
    assert info["source_ok"] is True


def test_apply_sync_creates_seed(sample_db, tmp_path, monkeypatch):
    monkeypatch.setattr(seed_sync, "SOURCE_PATH", sample_db)
    seed = tmp_path / "seed.sqlite3"
    monkeypatch.setattr(seed_sync, "SEED_PATH", seed)

    assert seed_sync.main(["--apply"]) == 0
    assert seed.exists()
    conn = sqlite3.connect(str(seed))
    try:
        assert conn.execute("SELECT COUNT(*) FROM canciones").fetchone()[0] == 59
        assert conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0] == 0
    finally:
        conn.close()


def test_check_returns_error_when_outdated(sample_db, tmp_path, monkeypatch):
    monkeypatch.setattr(seed_sync, "SOURCE_PATH", sample_db)
    seed = tmp_path / "seed.sqlite3"
    monkeypatch.setattr(seed_sync, "SEED_PATH", seed)

    assert seed_sync.main(["--check"]) == 1
