"""Tests para src/web_admin/api.py."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import db_manager


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    """TestClient de FastAPI apuntando a una DB temporal."""
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))

    # Recargar config -> db_manager -> database -> auth -> api en orden
    from src.web_admin import config as auth_config

    importlib.reload(auth_config)
    importlib.reload(db_manager)
    from src.web_admin import database as db_mod

    importlib.reload(db_mod)
    from src.web_admin import auth as auth_mod

    importlib.reload(auth_mod)
    from src.web_admin import api

    importlib.reload(api)

    # Forzar canciones_manager a la DB temporal (lo importan los handlers)
    from src import canciones_manager as cm

    importlib.reload(cm)
    monkeypatch.setattr(cm, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(cm, "DB_PATH", tmp_path / "data" / "db.sqlite3")

    # Copiar schema.sql real
    schema_src = Path("/home/pciath/proyectos/CCE-M5-Web-Presentaciones/data/schema.sql")
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())

    # Inicializar DBs
    db_manager.init_database(auth_config.DB_PATH)
    db_manager.init_database(cm.DB_PATH)

    # Mockear rebuild_web para no tocar el filesystem real
    monkeypatch.setattr("src.rebuild_web.rebuild_web", lambda: None)

    with TestClient(api.app) as tc:
        yield tc


def _login(
    client: TestClient,
    username: str | None = None,
    password: str | None = None,
) -> str:
    from src.web_admin.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME

    u = username or DEFAULT_ADMIN_USERNAME
    pw = password or DEFAULT_ADMIN_PASSWORD
    r = client.post("/auth/login", json={"username": u, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_default_admin(client) -> None:
    token = _login(client)
    assert token


def test_login_invalid(client) -> None:
    r = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_me(client) -> None:
    from src.web_admin.config import DEFAULT_ADMIN_USERNAME

    token = _login(client)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == DEFAULT_ADMIN_USERNAME
    assert data["role"] == "admin"


def test_me_unauthorized(client) -> None:
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_create_and_list_users(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/users",
        json={"username": "viewer1", "password": "pass", "role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "viewer"

    r = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    usernames = {u["username"] for u in r.json()}
    assert "viewer1" in usernames


def test_update_user(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/users",
        json={"username": "viewer2", "password": "pass", "role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    uid = r.json()["id"]
    r = client.patch(
        f"/users/{uid}",
        json={"full_name": "Viewer Dos", "role": "admin"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Viewer Dos"
    assert r.json()["role"] == "admin"


def test_delete_user_forbidden_self(client) -> None:
    admin_token = _login(client)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    uid = r.json()["id"]
    r = client.delete(f"/users/{uid}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 409


def test_change_password(client) -> None:
    from src.web_admin.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME

    admin_token = _login(client)
    r = client.post(
        "/auth/change-password",
        json={"current_password": DEFAULT_ADMIN_PASSWORD, "new_password": "newpass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200

    # login con nueva pass
    r = client.post(
        "/auth/login",
        json={"username": DEFAULT_ADMIN_USERNAME, "password": "newpass"},
    )
    assert r.status_code == 200


def test_workflow_crud(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/workflows",
        json={"fecha_domingo": "2026-01-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    wf = r.json()["workflow"]
    assert wf["fecha_domingo"] == "2026-01-01"

    r = client.get(f"/workflows/{wf['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["workflow"]["id"] == wf["id"]


def test_workflow_duplicate_requires_force(client) -> None:
    admin_token = _login(client)
    payload = {"fecha_domingo": "2026-02-01"}
    r = client.post("/workflows", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200

    r = client.post("/workflows", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 409

    r = client.post(
        "/workflows", json={**payload, "force": True}, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert r.status_code == 200


def test_goto_step(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/workflows",
        json={"fecha_domingo": "2026-03-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wf_id = r.json()["workflow"]["id"]

    r = client.post(
        f"/workflows/{wf_id}/goto-step",
        json={"workflow_id": wf_id, "step": "fetch_lectures"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["workflow"]["current_step"] == "fetch_lectures"


def test_canciones_crud(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/canciones",
        json={
            "titulo": "Canción API",
            "letra_con_acordes": "\nAm\nLínea uno\n",
            "momentos": ["entrada"],
            "tono": "Am",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201, r.text
    cancion = r.json()
    assert cancion["titulo"] == "Canción API"

    r = client.get(f"/canciones/{cancion['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["titulo"] == "Canción API"

    r = client.patch(
        f"/canciones/{cancion['id']}",
        json={"titulo": "Canción API actualizada"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["titulo"] == "Canción API actualizada"

    r = client.delete(f"/canciones/{cancion['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200

    r = client.get(f"/canciones/{cancion['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 404
