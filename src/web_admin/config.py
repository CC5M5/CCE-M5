"""Configuración del panel de administración."""

from __future__ import annotations

import os
from pathlib import Path

# Rutas del proyecto
DEFAULT_PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
PROJECT_DIR = Path(os.environ.get("CCE_PROJECT_DIR", DEFAULT_PROJECT_DIR))
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
BACKUPS_DIR = PROJECT_DIR / "backups"

# Auth
JWT_SECRET = os.environ.get("CCE_ADMIN_JWT_SECRET", "cambia-esta-clave-en-produccion")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("CCE_ADMIN_TOKEN_TTL", "480"))

# Usuario inicial por defecto (debe cambiarse en producción)
DEFAULT_ADMIN_USERNAME = os.environ.get("CCE_ADMIN_DEFAULT_USER", "rafael.torres")
DEFAULT_ADMIN_PASSWORD = os.environ.get("CCE_ADMIN_DEFAULT_PASSWORD", "1234")
DEFAULT_ADMIN_NAME = os.environ.get("CCE_ADMIN_DEFAULT_NAME", "Rafael Torres")
