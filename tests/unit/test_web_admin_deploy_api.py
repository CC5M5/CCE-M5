"""Tests de los endpoints admin de deploy a GitHub Pages (workflow_dispatch, estado y publicar seed).

Los llamados a la API de GitHub y los comandos git se parchean: no hay
efectos reales sobre GitHub ni sobre el repo del proyecto.
"""

import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = REPO_DIR
sys.path.insert(0, str(PROJECT_DIR / "src"))
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

DEFAULT_ADMIN_PASSWORD = "pass-admin-test"
SEED_REL = "data/seeds/db.empty.sqlite3"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient de FastAPI apuntando a un proyecto temporal, con DB inicializada."""
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CCE_ADMIN_DEFAULT_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    monkeypatch.chdir(tmp_path)

    (tmp_path / "web" / "dist").mkdir(parents=True, exist_ok=True)
    (tmp_path / "web" / "dist" / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    schema_src = PROJECT_DIR / "data" / "schema.sql"
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_bytes(schema_src.read_bytes())

    from src import config as core_config

    importlib.reload(core_config)
    from src.web_admin import config as auth_config

    importlib.reload(auth_config)
    from src import db_manager

    importlib.reload(db_manager)
    from src.web_admin import database as db_mod

    importlib.reload(db_mod)
    from src.web_admin import auth as auth_mod

    importlib.reload(auth_mod)
    from src.web_admin import api

    importlib.reload(api)
    import seed_sync

    importlib.reload(seed_sync)

    from src import canciones_manager as cm

    importlib.reload(cm)
    monkeypatch.setattr(cm, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(cm, "DB_PATH", tmp_path / "data" / "db.sqlite3")

    # Inicializar la BD desde schema.sql y checkpoint WAL para que el main
    # file refleje todo el contenido (seed_sync valida tamaño del main file).
    db_manager.init_database(auth_config.DB_PATH)
    conn = db_manager.create_connection(auth_config.DB_PATH)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()

    # Sobreescribir el admin con el password de prueba para que _login sea fiable.
    conn = db_manager.create_connection(auth_config.DB_PATH)
    with conn:
        conn.execute(
            "DELETE FROM admin_users WHERE username = ?",
            (auth_config.DEFAULT_ADMIN_USERNAME,),
        )
        conn.execute(
            "INSERT INTO admin_users (username, password_hash, full_name, role, is_active)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                auth_config.DEFAULT_ADMIN_USERNAME,
                auth_mod._hash_password(auth_config.DEFAULT_ADMIN_PASSWORD),
                auth_config.DEFAULT_ADMIN_NAME,
                "admin",
                1,
            ),
        )
    conn.close()

    # Mockear rebuild_web para no tocar el filesystem real.
    monkeypatch.setattr("src.rebuild_web.rebuild_web", lambda *a, **k: {"status": "ok (mock)"})

    with TestClient(api.app) as tc:
        yield tc


def _checkpoint_db(db_path: Path) -> None:
    """Fuerza checkpoint WAL para que el main file refleje todo el contenido."""
    import src.db_manager
    conn = src.db_manager.create_connection(db_path)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()


def _login(client: TestClient) -> str:
    from src.web_admin.config import DEFAULT_ADMIN_USERNAME

    res = client.post(
        "/auth/login",
        json={
            "username": DEFAULT_ADMIN_USERNAME,
            "password": DEFAULT_ADMIN_PASSWORD,
        },
    )
    assert res.status_code == 200
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mock_github(monkeypatch, response=None, error=None):
    """Parchea _github_api_request del módulo api. Devuelve el log de llamadas."""
    import src.web_admin.api as api
    calls = []

    def fake(url, *, method="GET", payload=None):
        calls.append({"url": url, "method": method, "payload": payload})
        if error is not None:
            raise error
        return response if response is not None else {}

    monkeypatch.setattr(api, "_github_api_request", fake)
    return calls


def _mock_git(monkeypatch, *, is_repo=True, branch="main", porcelain="", push_ok=True):
    """Parchea subprocess.run para los comandos git que usa el módulo api."""
    import subprocess as _subprocess
    calls = []

    def fake(args, **kwargs):
        calls.append(list(args))
        if args[:2] == ["git", "rev-parse"] and "is-inside-work-tree" in args:
            if is_repo:
                return _subprocess.CompletedProcess(args, 0, stdout="true\n", stderr="")
            return _subprocess.CompletedProcess(
                args, 1, stdout="", stderr="fatal: no es un repositorio git\n"
            )
        if args[:2] == ["git", "rev-parse"] and "HEAD" in args:
            return _subprocess.CompletedProcess(args, 0, stdout=f"{branch}\n", stderr="")
        if args[:2] == ["git", "rev-parse"] and "--verify" in args:
            return _subprocess.CompletedProcess(args, 0, stdout="ref ok\n", stderr="")
        if args[:2] == ["git", "rev-list"]:
            return _subprocess.CompletedProcess(args, 0, stdout="1\n", stderr="")
        if args[:2] == ["git", "status"]:
            return _subprocess.CompletedProcess(args, 0, stdout=porcelain, stderr="")
        if args[:2] == ["git", "add"]:
            return _subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:2] == ["git", "commit"]:
            return _subprocess.CompletedProcess(args, 0, stdout=f"[{branch}] chore(seed)", stderr="")
        if args[:2] == ["git", "push"]:
            if push_ok:
                return _subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            return _subprocess.CompletedProcess(
                args, 1, stdout="",
                stderr="fatal: unable to access 'https://github.com/CC5M5/CCE-M5.git': Fallo al conectar",
            )
        return _subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(_subprocess, "run", fake)
    return calls


# ---------------------------------------------------------------------------
# POST /admin/deploy
# ---------------------------------------------------------------------------

def test_deploy_sin_token_devuelve_401(client):
    res = client.post("/admin/deploy")
    assert res.status_code == 401


def test_deploy_triggera_workflow_dispatch_en_main(client, monkeypatch):
    token = _login(client)
    calls = _mock_github(
        monkeypatch,
        response={"html_url": "https://github.com/CC5M5/CCE-M5/actions/runs/42"},
    )
    res = client.post("/admin/deploy", headers=_auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data["triggered"] is True
    assert "actions/workflows/deploy.yml" in data["run"]["html_url"]
    call = calls[0]
    assert call["method"] == "POST"
    assert call["url"] == (
        "https://api.github.com/repos/CC5M5/CCE-M5/actions/workflows/deploy.yml/dispatches"
    )
    assert call["payload"] == {"ref": "main"}


def test_deploy_sin_token_github_devuelve_503(client):
    token = _login(client)
    res = client.post("/admin/deploy", headers=_auth(token))
    assert res.status_code == 503
    assert "GITHUB_TOKEN_CC5M5" in res.json()["detail"]


def test_deploy_repo_no_encontrado_devuelve_404(client, monkeypatch):
    token = _login(client)
    import src.web_admin.api as api
    _mock_github(monkeypatch, error=api.GithubApiError(404, {"message": "Not Found"}))
    res = client.post("/admin/deploy", headers=_auth(token))
    assert res.status_code == 404


def test_deploy_token_sin_permisos_devuelve_403(client, monkeypatch):
    token = _login(client)
    import src.web_admin.api as api
    _mock_github(
        monkeypatch,
        error=api.GithubApiError(403, {"message": "Resource not accessible"}),
    )
    res = client.post("/admin/deploy", headers=_auth(token))
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/deploy/status
# ---------------------------------------------------------------------------

def test_status_sin_token_devuelve_401(client):
    assert client.get("/admin/deploy/status").status_code == 401


def test_status_incluye_deploy_seed_y_git(client, monkeypatch):
    token = _login(client)
    _mock_github(
        monkeypatch,
        response={
            "workflow_runs": [
                {
                    "status": "completed",
                    "conclusion": "success",
                    "html_url": "https://github.com/CC5M5/CCE-M5/actions/runs/1",
                    "head_branch": "main",
                    "created_at": "2026-11-08T10:00:00Z",
                }
            ]
        },
    )
    res = client.get("/admin/deploy/status", headers=_auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data["deploy"]["latest_run"]["conclusion"] == "success"
    assert data["deploy"]["latest_run"]["html_url"].endswith("/actions/runs/1")
    assert data["seed"]["exists"] is False
    assert data["seed"]["up_to_date"] is False
    assert data["git"]["is_repo"] is False


def test_status_sin_token_github_mantiene_seed_y_git(client):
    token = _login(client)
    res = client.get("/admin/deploy/status", headers=_auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data["deploy"]["latest_run"] is None
    assert data["seed"]["exists"] is False
    assert data["git"]["is_repo"] is False


def test_status_seed_al_dia_muestra_up_to_date(client, monkeypatch):
    token = _login(client)
    _mock_github(monkeypatch, response={"workflow_runs": []})
    import seed_sync
    seed_sync._apply_sync()
    res = client.get("/admin/deploy/status", headers=_auth(token))
    assert res.status_code == 200
    assert res.json()["seed"]["exists"] is True
    assert res.json()["seed"]["up_to_date"] is True


# ---------------------------------------------------------------------------
# POST /admin/publish
# ---------------------------------------------------------------------------

def test_publish_sin_token_devuelve_401(client):
    assert client.post("/admin/publish").status_code == 401


def test_publish_sin_token_github_devuelve_503(client):
    token = _login(client)
    res = client.post("/admin/publish", headers=_auth(token))
    assert res.status_code == 503


def test_publish_fuera_de_main_devuelve_409(client, monkeypatch):
    token = _login(client)
    _mock_github(monkeypatch, response={})
    _mock_git(monkeypatch, branch="dev")
    res = client.post("/admin/publish", headers=_auth(token))
    assert res.status_code == 409
    assert "main" in res.json()["detail"]


def test_publish_sin_cambios_no_comite(client, monkeypatch):
    token = _login(client)
    _mock_github(monkeypatch, response={})
    calls = _mock_git(monkeypatch, porcelain="")
    res = client.post("/admin/publish", headers=_auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data["committed"] is False
    assert data["pushed"] is False
    assert not any(c[:2] == ["git", "commit"] for c in calls)


def test_publish_publica_seed_comite_y_push(client, monkeypatch):
    token = _login(client)
    _mock_github(monkeypatch, response={})
    calls = _mock_git(monkeypatch, porcelain=f"M  {SEED_REL}\n")
    res = client.post("/admin/publish", headers=_auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data["committed"] is True
    assert data["pushed"] is True
    assert data["files"] == [SEED_REL]
    seed_path = Path(os.environ["CCE_PROJECT_DIR"]) / SEED_REL
    assert seed_path.exists()
    import seed_sync
    assert seed_sync._validate_source(seed_path) == []
    assert any(c[:2] == ["git", "add"] and SEED_REL in c for c in calls)
    assert any(c[:2] == ["git", "commit"] for c in calls)
    assert any(c[:2] == ["git", "push"] and c[2:] == ["origin", "main"] for c in calls)


def test_publish_push_falla_devuelve_500(client, monkeypatch):
    token = _login(client)
    _mock_github(monkeypatch, response={})
    _mock_git(monkeypatch, porcelain=f"M  {SEED_REL}\n", push_ok=False)
    res = client.post("/admin/publish", headers=_auth(token))
    assert res.status_code == 500
    assert "push" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# _github_api_request (helper de la API de GitHub)
# ---------------------------------------------------------------------------

def _fake_httpx_response(status_code: int = 200):
    class _FakeResponse:
        pass

    resp = _FakeResponse()
    resp.status_code = status_code
    resp.text = f'{{"message": "fake {status_code}"}}'
    return resp


def test_github_api_request_orden_de_argumentos_httpx(client, monkeypatch):
    """httpx.request(method, url, ...) recibe metodo y url por posicion en ese
    orden; si no, httpx lanza 'multiple values for argument method'."""
    import httpx

    import src.web_admin.api as api

    monkeypatch.setattr(api, "GITHUB_TOKEN_COMENTARIOS", "token-prueba")
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append({"method": method, "url": url, "kwargs": kwargs})
        return _fake_httpx_response(200)

    monkeypatch.setattr(httpx, "request", fake_request)

    api._github_api_request("https://api.github.com/repos/CC5M5/CCE-M5")
    assert calls[-1]["method"] == "GET"
    assert calls[-1]["url"] == "https://api.github.com/repos/CC5M5/CCE-M5"

    api._github_api_request(
        "https://api.github.com/repos/CC5M5/CCE-M5/actions/workflows/deploy.yml/dispatches",
        method="POST",
        payload={"ref": "main"},
    )
    assert calls[-1]["method"] == "POST"
    assert calls[-1]["kwargs"]["json"] == {"ref": "main"}


def test_github_api_request_error_4xx_lanza_github_api_error(client, monkeypatch):
    """Comportamiento previo del helper: 4xx de GitHub -> GithubApiError."""
    import httpx

    import src.web_admin.api as api

    monkeypatch.setattr(api, "GITHUB_TOKEN_COMENTARIOS", "token-prueba")

    def fake_request(method, url, **kwargs):
        return _fake_httpx_response(404)

    monkeypatch.setattr(httpx, "request", fake_request)

    with pytest.raises(api.GithubApiError) as excinfo:
        api._github_api_request("https://api.github.com/repos/CC5M5/CCE-M5")
    assert excinfo.value.status_code == 404


def test_publish_bd_fuente_invalida_devuelve_409(client, monkeypatch):
    token = _login(client)
    _mock_github(monkeypatch, response={})
    _mock_git(monkeypatch)
    db_path = Path(os.environ["CCE_PROJECT_DIR"]) / "data" / "db.sqlite3"
    # Vaciar una tabla principal hace la BD fuente inválida para la seed
    # ("Tabla principal vacía") sin romper admin_users: el admin sigue
    # pudiendo autenticarse para llegar al 409 del endpoint.
    conn = sqlite3.connect(str(db_path))
    conn.execute("DELETE FROM canciones")
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    res = client.post("/admin/publish", headers=_auth(token))
    assert res.status_code == 409
    assert "base de datos" in res.json()["detail"].lower() or "fuente" in res.json()["detail"].lower()
