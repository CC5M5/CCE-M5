"""Tests para src/web_admin/config.py."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest


def test_project_dir_default() -> None:
    import importlib
    from src.web_admin import config as cfg
    importlib.reload(cfg)
    assert cfg.PROJECT_DIR == Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"


def test_project_dir_from_env(tmp_path: Path) -> None:
    with patch.dict(os.environ, {"CCE_PROJECT_DIR": str(tmp_path)}):
        # Importar de nuevo para capturar env
        import importlib
        from src.web_admin import config as cfg

        importlib.reload(cfg)
        assert cfg.PROJECT_DIR == tmp_path


def test_load_jwt_secret_from_env() -> None:
    with patch.dict(os.environ, {"CCE_ADMIN_JWT_SECRET": "x" * 48}):
        from src.web_admin.config import _load_jwt_secret
        assert _load_jwt_secret() == "x" * 48


def test_load_jwt_secret_short_warning(tmp_path: Path) -> None:
    with patch.dict(os.environ, {"CCE_PROJECT_DIR": str(tmp_path), "CCE_ADMIN_JWT_SECRET": "corta"}):
        from src.web_admin.config import _load_jwt_secret
        assert _load_jwt_secret() == "corta"


def test_default_admin_values(tmp_path: Path) -> None:
    with patch.dict(
        os.environ,
        {
            "CCE_PROJECT_DIR": str(tmp_path),
            "CCE_ADMIN_DEFAULT_USER": "admin",
            "CCE_ADMIN_DEFAULT_PASSWORD": "secret",
            "CCE_ADMIN_DEFAULT_NAME": "Admin",
        },
    ):
        import importlib
        from src.web_admin import config as cfg

        importlib.reload(cfg)
        assert cfg.DEFAULT_ADMIN_USERNAME == "admin"
        assert cfg.DEFAULT_ADMIN_PASSWORD == "secret"
        assert cfg.DEFAULT_ADMIN_NAME == "Admin"
