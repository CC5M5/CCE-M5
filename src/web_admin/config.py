from __future__ import annotations

"""Configuración del panel de administración."""

import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

# Rutas del proyecto
DEFAULT_PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
PROJECT_DIR = Path(os.environ.get("CCE_PROJECT_DIR", DEFAULT_PROJECT_DIR))
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
BACKUPS_DIR = PROJECT_DIR / "backups"

# Auth
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("CCE_ADMIN_TOKEN_TTL", "480"))


def _load_jwt_secret() -> str:
    """Devuelve el JWT secret. Preferencia: env > archivo persistente > generado."""
    env_secret = os.environ.get("CCE_ADMIN_JWT_SECRET")
    if env_secret:
        if len(env_secret.encode("utf-8")) < 32:
            logger.warning(
                "CCE_ADMIN_JWT_SECRET tiene menos de 32 bytes; "
                "el estándar recomienda una clave más larga."
            )
        return env_secret

    secret_file = DATA_DIR / ".admin_jwt_secret"
    try:
        if secret_file.exists():
            return secret_file.read_text().strip()
    except Exception as exc:
        logger.warning("No se pudo leer %s: %s", secret_file, exc)

    generated = secrets.token_urlsafe(48)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        secret_file.write_text(generated)
        logger.warning(
            "No se definió CCE_ADMIN_JWT_SECRET. Se generó un secreto aleatorio en %s "
            "que se perderá si borras ese archivo. Para producción define CCE_ADMIN_JWT_SECRET.",
            secret_file,
        )
    except Exception as exc:
        logger.error("No se pudo persistir JWT secret generado: %s", exc)
    return generated


JWT_SECRET = _load_jwt_secret()

# Usuario inicial por defecto (debe cambiarse en producción)
DEFAULT_ADMIN_USERNAME = os.environ.get("CCE_ADMIN_DEFAULT_USER", "rafael.torres")
DEFAULT_ADMIN_PASSWORD = os.environ.get("CCE_ADMIN_DEFAULT_PASSWORD", "1234")
DEFAULT_ADMIN_NAME = os.environ.get("CCE_ADMIN_DEFAULT_NAME", "Rafael Torres")
