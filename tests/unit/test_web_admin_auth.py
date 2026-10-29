"""Tests para src/web_admin/auth.py."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi import HTTPException


@pytest.fixture
def auth_env(tmp_path: Path, monkeypatch):
    """Devuelve módulos auth/database/config apuntando a una DB temporal."""
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CCE_ADMIN_DEFAULT_PASSWORD", "pass-admin-test")
    # chdir para que pydantic-settings no cargue el .env del proyecto.
    monkeypatch.chdir(tmp_path)

    # Recargar src.config primero porque es la nueva fuente de verdad
    from src import config as core_config

    importlib.reload(core_config)
    from src.web_admin import config as auth_config

    importlib.reload(auth_config)
    from src.web_admin import database as db_mod

    importlib.reload(db_mod)
    from src.web_admin import auth as auth_mod

    auth_mod = importlib.reload(auth_mod)
    db_mod.init_admin_schema(auth_config.DB_PATH)
    return auth_mod, db_mod, auth_config


def test_hash_and_verify_password(auth_env) -> None:
    auth, _, _ = auth_env
    hashed = auth.hash_password("secret")
    assert hashed != "secret"
    assert auth._verify_password("secret", hashed) is True
    assert auth._verify_password("wrong", hashed) is False


def test_token_roundtrip(auth_env) -> None:
    auth, _, _ = auth_env
    token = auth.create_access_token("ana", "admin")
    payload = auth.decode_access_token(token)
    assert payload["sub"] == "ana"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_decode_expired_token(auth_env, monkeypatch) -> None:
    auth, _, _ = auth_env
    monkeypatch.setattr(auth, "ACCESS_TOKEN_EXPIRE_MINUTES", -1)
    token = auth.create_access_token("ana", "admin")
    with pytest.raises(HTTPException) as exc:
        auth.decode_access_token(token)
    assert exc.value.status_code == 401


def test_decode_invalid_token(auth_env) -> None:
    auth, _, _ = auth_env
    with pytest.raises(HTTPException) as exc:
        auth.decode_access_token("not.a.token")
    assert exc.value.status_code == 401


def test_authenticate_user_success(auth_env) -> None:
    auth, db_mod, _ = auth_env
    h = auth.hash_password("secret")
    db_mod.create_user("luis", h, full_name="Luis", role="admin")
    user = auth.authenticate_user("luis", "secret")
    assert user is not None
    assert user["username"] == "luis"
    assert user["role"] == "admin"


def test_authenticate_user_wrong_password(auth_env) -> None:
    auth, db_mod, _ = auth_env
    h = auth.hash_password("secret")
    db_mod.create_user("luis", h)
    assert auth.authenticate_user("luis", "wrong") is None


def test_authenticate_user_inactive(auth_env) -> None:
    auth, db_mod, _ = auth_env
    h = auth.hash_password("secret")
    uid = db_mod.create_user("luis", h)
    db_mod.update_user(uid, is_active=False)
    assert auth.authenticate_user("luis", "secret") is None


def test_get_current_user_missing_credentials(auth_env) -> None:
    auth, _, _ = auth_env
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(None)
    assert exc.value.status_code == 401


def test_get_current_user_valid(auth_env) -> None:
    auth, db_mod, _ = auth_env
    h = auth.hash_password("secret")
    db_mod.create_user("ana", h, full_name="Ana", role="viewer")

    class FakeCreds:
        credentials = auth.create_access_token("ana", "viewer")

    current = auth.get_current_user(FakeCreds())
    assert current["username"] == "ana"
    assert current["role"] == "viewer"


def test_get_current_user_expired(auth_env, monkeypatch) -> None:
    auth, db_mod, _ = auth_env
    h = auth.hash_password("secret")
    db_mod.create_user("ana", h)
    monkeypatch.setattr(auth, "ACCESS_TOKEN_EXPIRE_MINUTES", -1)
    token = auth.create_access_token("ana", "viewer")

    class FakeCreds:
        credentials = token

    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(FakeCreds())
    assert exc.value.status_code == 401


def test_require_admin(auth_env) -> None:
    auth, _, _ = auth_env
    assert auth.require_admin({"role": "admin"}) == {"role": "admin"}
    with pytest.raises(HTTPException) as exc:
        auth.require_admin({"role": "viewer"})
    assert exc.value.status_code == 403


def test_create_new_user(auth_env) -> None:
    auth, db_mod, _ = auth_env
    uid = auth.create_new_user("nuevo", "pass", full_name="Nuevo", role="viewer")
    assert uid == 1
    user = db_mod.get_user_by_username("nuevo")
    assert user is not None
    assert user.role == "viewer"

    with pytest.raises(ValueError):
        auth.create_new_user("nuevo", "pass")  # duplicado

    with pytest.raises(ValueError):
        auth.create_new_user("otro", "pass", role="superuser")


def test_seed_default_admin(auth_env) -> None:
    auth, db_mod, cfg = auth_env
    auth.seed_default_admin()
    admin = db_mod.get_user_by_username(cfg.DEFAULT_ADMIN_USERNAME)
    assert admin is not None
    assert admin.role == "admin"
    assert auth._verify_password("pass-admin-test", admin.password_hash)

    # Idempotente
    auth.seed_default_admin()
    assert db_mod.count_admins() == 1


def test_seed_sin_password_y_sin_admin_falla(auth_env, monkeypatch) -> None:
    """Sin CCE_ADMIN_DEFAULT_PASSWORD y sin admin, el seed debe fallar (S1)."""
    auth, db_mod, cfg = auth_env
    monkeypatch.delenv("CCE_ADMIN_DEFAULT_PASSWORD")
    from src import config as core_config

    importlib.reload(core_config)
    importlib.reload(cfg)
    importlib.reload(auth)

    with pytest.raises(RuntimeError, match="CCE_ADMIN_DEFAULT_PASSWORD"):
        auth.seed_default_admin()
    assert db_mod.get_user_by_username(cfg.DEFAULT_ADMIN_USERNAME) is None


def test_seed_con_admin_existente_no_requiere_password(auth_env, monkeypatch) -> None:
    """Si el admin ya existe, el seed no necesita la variable de entorno (S1)."""
    auth, db_mod, cfg = auth_env
    monkeypatch.delenv("CCE_ADMIN_DEFAULT_PASSWORD")
    from src import config as core_config

    importlib.reload(core_config)
    importlib.reload(cfg)
    importlib.reload(auth)

    db_mod.create_user(cfg.DEFAULT_ADMIN_USERNAME, auth.hash_password("otra-clave"), role="admin")
    auth.seed_default_admin()  # no debe lanzar error
    admin = db_mod.get_user_by_username(cfg.DEFAULT_ADMIN_USERNAME)
    assert admin is not None
    assert auth._verify_password("otra-clave", admin.password_hash)


def test_change_user_password(auth_env) -> None:
    auth, db_mod, _ = auth_env
    h = auth.hash_password("old")
    uid = db_mod.create_user("pepe", h)
    auth.change_user_password(uid, "new")
    updated = auth.authenticate_user("pepe", "new")
    assert updated is not None

    with pytest.raises(ValueError):
        auth.change_user_password(9999, "nope")
