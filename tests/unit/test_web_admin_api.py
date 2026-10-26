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

    # Crear un web/dist mínimo para que el healthcheck de web estática pase.
    web_dist = tmp_path / "web" / "dist"
    web_dist.mkdir(parents=True, exist_ok=True)
    (web_dist / "index.html").write_text("<html></html>")

    # Recargar src.config primero porque es la nueva fuente de verdad
    from src import config as core_config

    importlib.reload(core_config)

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
    schema_src = Path(__file__).resolve().parents[2] / "data" / "schema.sql"
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())

    # Inicializar DBs
    db_manager.init_database(auth_config.DB_PATH)
    db_manager.init_database(cm.DB_PATH)

    # Sobreescribir el admin con el password por defecto para que _login
    # sea fiable incluso cuando el seed traiga un hash distinto.
    conn = db_manager.create_connection(auth_config.DB_PATH)
    with conn:
        conn.execute("DELETE FROM admin_users WHERE username = ?", (auth_config.DEFAULT_ADMIN_USERNAME,))
        conn.execute(
            "INSERT INTO admin_users (username, password_hash, full_name, role, is_active) VALUES (?, ?, ?, ?, ?)",
            (
                auth_config.DEFAULT_ADMIN_USERNAME,
                auth_mod._hash_password(auth_config.DEFAULT_ADMIN_PASSWORD),
                auth_config.DEFAULT_ADMIN_NAME,
                "admin",
                1,
            ),
        )
    conn.close()

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
    data = r.json()
    assert data["status"] == "ok"
    assert data["database"]["ok"] is True
    assert data["static_web"]["ok"] is True


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


def test_static_login_html(client) -> None:
    r = client.get("/admin/login.html")
    assert r.status_code in (200, 307, 302)


def test_root_redirect(client) -> None:
    r = client.get("/")
    assert r.status_code in (200, 307, 302)


def test_comentarios_sin_config(client, monkeypatch) -> None:
    monkeypatch.setattr("src.web_admin.api.GITHUB_TOKEN_COMENTARIOS", "")
    r = client.post("/comentarios", json={"tipo": "sugerencia", "mensaje": "hola", "presentacion": "2026-01-01", "nombre": "Ana", "email": "a@b.com"})
    assert r.status_code == 503


def test_workflow_advance_mockeado(client, monkeypatch) -> None:
    admin_token = _login(client)
    r = client.post(
        "/workflows",
        json={"fecha_domingo": "2026-04-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wf_id = r.json()["workflow"]["id"]

    from src.web_admin import api

    def fake_run_step(wid, action, data):
        return {
            "success": True,
            "workflow": {
                "id": wid,
                "fecha_domingo": "2026-04-01",
                "current_step": "verify_lectures",
                "status": "verify_lectures",
                "steps_data": {},
                "created_by": "admin",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
                "completed_at": None,
                "superseded_by": None,
            },
            "logs": [],
            "can_advance": True,
            "next_step_name": "verify_lectures",
            "warning": None,
        }

    monkeypatch.setattr(api, "run_step", fake_run_step)
    r = client.post(
        f"/workflows/{wf_id}/advance",
        json={"workflow_id": wf_id, "action": "next"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["workflow"]["current_step"] == "verify_lectures"


def test_workflow_advance_failure(client, monkeypatch) -> None:
    admin_token = _login(client)
    r = client.post(
        "/workflows",
        json={"fecha_domingo": "2026-05-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wf_id = r.json()["workflow"]["id"]

    from src.web_admin import api

    def fake_run_step(wid, action, data):
        return {"success": False, "error": "fallo simulado"}

    monkeypatch.setattr(api, "run_step", fake_run_step)
    r = client.post(
        f"/workflows/{wf_id}/advance",
        json={"workflow_id": wf_id, "action": "next"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


def test_workflow_backups(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/workflows",
        json={"fecha_domingo": "2026-06-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wf_id = r.json()["workflow"]["id"]
    r = client.get(f"/workflows/{wf_id}/backups", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert "backups" in r.json()


def test_fechas_presentaciones(client) -> None:
    token = _login(client)
    r = client.get("/presentacion/fechas", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "fechas" in r.json()


def test_create_user_invalid_role(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/users",
        json={"username": "bad", "password": "***", "role": "superadmin"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_update_user_not_found(client) -> None:
    admin_token = _login(client)
    r = client.patch(
        "/users/9999",
        json={"full_name": "Nadie"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404


def test_delete_user_not_found(client) -> None:
    admin_token = _login(client)
    r = client.delete("/users/9999", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 404


def test_viewer_cannot_create_users(client, monkeypatch) -> None:
    admin_token = _login(client)
    r = client.post(
        "/users",
        json={"username": "viewer3", "password": "***", "role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    uid = r.json()["id"]

    # cambiar a viewer
    r = client.patch(
        f"/users/{uid}",
        json={"role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200

    # login como viewer3
    r = client.post("/auth/login", json={"username": "viewer3", "password": "***"})
    viewer_token = r.json()["access_token"]

    r = client.post(
        "/users",
        json={"username": "nuevo", "password": "***", "role": "viewer"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 403


def test_login_validation(client) -> None:
    r = client.post("/auth/login", json={"username": "", "password": ""})
    assert r.status_code in (401, 422)


def test_workflow_index(client) -> None:
    token = _login(client)
    r = client.get("/workflows", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "workflows" in r.json()


def test_workflow_index_with_fecha(client) -> None:
    admin_token = _login(client)
    r = client.get("/workflows?fecha=2026-01-01", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert isinstance(r.json()["workflows"], list)


def test_workflow_detail_not_found(client) -> None:
    token = _login(client)
    r = client.get("/workflows/9999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_goto_step_invalid(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/workflows",
        json={"fecha_domingo": "2026-07-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wf_id = r.json()["workflow"]["id"]

    r = client.post(
        f"/workflows/{wf_id}/goto-step",
        json={"workflow_id": wf_id, "step": "invalido"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


def test_workflow_advance_inconsistent_id(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/workflows",
        json={"fecha_domingo": "2026-08-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wf_id = r.json()["workflow"]["id"]

    r = client.post(
        f"/workflows/{wf_id}/advance",
        json={"workflow_id": 9999, "action": "next"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_workflow_advance_not_found(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/workflows/9999/advance",
        json={"workflow_id": 9999, "action": "next"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404


def test_change_password_wrong_current(client) -> None:
    admin_token = _login(client)
    r = client.post(
        "/auth/change-password",
        json={"current_password": "wrong", "new_password": "newpass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 401


def test_change_password_too_short(client) -> None:
    from src.web_admin.config import DEFAULT_ADMIN_PASSWORD

    admin_token = _login(client)
    r = client.post(
        "/auth/change-password",
        json={"current_password": DEFAULT_ADMIN_PASSWORD, "new_password": "abc"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_list_canciones_empty(client) -> None:
    token = _login(client)
    r = client.get("/canciones", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    # El schema.sql semilla puede incluir canciones; solo verificamos
    # que la respuesta sea una lista de canciones valida.
    assert isinstance(data, list)
    for item in data:
        assert isinstance(item, dict)
        assert "id" in item and "titulo" in item


def test_update_user_last_admin(client) -> None:

    admin_token = _login(client)
    # obtener admin
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    uid = r.json()["id"]

    r = client.patch(
        f"/users/{uid}",
        json={"role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 409
