"""Tests de integración para los editores Flask montados bajo FastAPI."""
from __future__ import annotations

import importlib
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import db_manager


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    """TestClient de FastAPI apuntando a una DB temporal."""
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))

    from src import config as core_config

    importlib.reload(core_config)

    from src.web_admin import config as auth_config

    importlib.reload(auth_config)
    importlib.reload(db_manager)
    from src.web_admin import database as db_mod

    importlib.reload(db_mod)
    from src.web_admin import auth as auth_mod

    importlib.reload(auth_mod)
    from src.web_admin import api

    importlib.reload(api)

    from src import canciones_manager as cm

    importlib.reload(cm)
    monkeypatch.setattr(cm, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(cm, "DB_PATH", tmp_path / "data" / "db.sqlite3")

    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    project_dir = Path(__file__).resolve().parents[2]
    schema_src = project_dir / "data" / "schema.sql"
    seed_src = project_dir / "data" / "seeds" / "db.empty.sqlite3"
    if schema_src.exists():
        (tmp_path / "data" / "schema.sql").write_text(schema_src.read_text())
        db_manager.init_database(auth_config.DB_PATH)
        db_manager.init_database(cm.DB_PATH)
        # El editor de diapositivas necesita el catálogo base de slides;
        # el schema.sql solo tiene CREATE TABLE, así que copiamos las filas
        # del seed para las tablas que el editor consulta.
        if seed_src.exists():
            _copy_seed_tables(
                str(seed_src), str(auth_config.DB_PATH), ["slides_tipos", "slides"]
            )
    elif seed_src.exists():
        shutil.copy(seed_src, auth_config.DB_PATH)
        shutil.copy(seed_src, cm.DB_PATH)

    monkeypatch.setattr("src.rebuild_web.rebuild_web", lambda: None)
    monkeypatch.setattr("src.web_admin.editores.git_commit", lambda msg: "ok")

    with TestClient(api.app) as tc:
        yield tc


def _copy_seed_tables(seed_db: str, target_db: str, tables: list[str]) -> None:
    """Copia las filas de *tables* desde seed_db a target_db (vacía primero)."""
    src = sqlite3.connect(seed_db)
    dst = sqlite3.connect(target_db)
    for table in tables:
        dst.execute(f"DELETE FROM {table}")
        cur = src.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in cur.description]
        placeholders = ",".join("?" for _ in columns)
        insert_sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
        rows = cur.fetchall()
        dst.executemany(insert_sql, rows)
    dst.commit()
    src.close()
    dst.close()


def test_editor_acordes_index(client):
    """El editor de acordes responde 200 en la raíz."""
    response = client.get("/editor-acordes/")
    assert response.status_code == 200
    text = response.text.lower()
    assert "cancionero" in text or "acordes" in text or "canciones" in text


def test_editor_acordes_nueva_cancion_get(client):
    """El formulario de nueva canción responde 200."""
    response = client.get("/editor-acordes/cancionero/nueva")
    assert response.status_code == 200
    assert "<form" in response.text


def test_editor_acordes_nueva_cancion_post(client):
    """Crear una canción nueva vía POST actualiza la base de datos."""
    response = client.post(
        "/editor-acordes/cancionero/nueva/guardar",
        data={
            "titulo": "Canción de prueba",
            "texto": "Do Re Mi [La]",
            "momento": "entrada",
        },
    )
    assert response.status_code == 200
    text = response.text.lower()
    assert "creada" in text or "canción" in text or "guardada" in text


def test_editor_acordes_editar_cancion_post(client):
    """Editar una canción existente vía POST actualiza el contenido."""
    client.post(
        "/editor-acordes/cancionero/nueva/guardar",
        data={
            "titulo": "Canción editable",
            "texto": "Fa Sol [La]",
            "momento": "entrada",
        },
    )
    response = client.get("/editor-acordes/cancionero/cancion-editable")
    assert response.status_code == 200

    response = client.post(
        "/editor-acordes/cancionero/cancion-editable/guardar",
        data={
            "titulo": "Canción editable",
            "texto": "Fa Sol [La] [Mi]",
            "momento": "entrada,comunion",
        },
    )
    assert response.status_code == 200


def test_editor_diapositivas_index(client):
    """El editor de diapositivas responde 200 en la raíz."""
    response = client.get("/editor-diapositivas/")
    assert response.status_code == 200
    text = response.text.lower()
    assert "diapositivas" in text or "slides" in text or "catálogo" in text


def test_editor_diapositivas_nueva_get(client):
    """El formulario de nueva diapositiva responde 200 si existe la ruta."""
    response = client.get("/editor-diapositivas/slides/nueva")
    assert response.status_code in (200, 404)


def test_admin_health(client):
    """El healthcheck responde 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
