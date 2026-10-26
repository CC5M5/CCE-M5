"""Tests para scripts/healthcheck_docker.py."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import scripts.healthcheck_docker as hc


@pytest.fixture
def good_db(tmp_path: Path) -> Path:
    db = tmp_path / "good.sqlite3"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def bad_db(tmp_path: Path) -> Path:
    db = tmp_path / "bad.sqlite3"
    db.write_bytes(b"not a sqlite file")
    return db


def test_check_database_ok(good_db: Path) -> None:
    ok, msg = hc._check_database(good_db)
    assert ok is True
    assert msg == "ok"


def test_check_database_missing(tmp_path: Path) -> None:
    ok, msg = hc._check_database(tmp_path / "missing.sqlite3")
    assert ok is False
    assert "No existe" in msg


def test_check_database_bad(bad_db: Path) -> None:
    ok, msg = hc._check_database(bad_db)
    assert ok is False
    assert "error SQLite" in msg


def test_check_web_ok(tmp_path: Path) -> None:
    # healthcheck_docker usa urllib: no podemos mockear fácilmente la URL sin servidor.
    # Verificamos al menos que la función maneja un servidor inexistente.
    ok, msg = hc._check_web("http://127.0.0.1:59999", timeout=0.1)
    assert ok is False
    assert "no responde" in msg


def test_main_skip_editors_with_bad_web(good_db: Path) -> None:
    # La BD es válida, la web no, los editores se saltan.
    assert hc.main(["--db-path", str(good_db), "--web-url", "http://127.0.0.1:59999", "--skip-editors", "--timeout", "0.1"]) == 1
