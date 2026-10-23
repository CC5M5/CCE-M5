import logging
import os
import secrets

import src.config as _core_config

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"


def __getattr__(name: str):
    """Delega la lectura de variables a src.config.settings."""
    s = _core_config.settings
    if name == "PROJECT_DIR":
        return s.project_dir
    if name == "DATA_DIR":
        return s.data_dir
    if name == "DB_PATH":
        return s.db_path
    if name == "BACKUPS_DIR":
        return s.backups_dir
    if name == "ACCESS_TOKEN_EXPIRE_MINUTES":
        return s.jwt_ttl_minutes
    if name == "DEFAULT_ADMIN_USERNAME":
        return s.default_admin_username
    if name == "DEFAULT_ADMIN_PASSWORD":
        return s.default_admin_password
    if name == "DEFAULT_ADMIN_NAME":
        return s.default_admin_name
    if name == "GITHUB_TOKEN_COMENTARIOS":
        return s.github_token_comentarios
    if name == "GITHUB_COMENTARIOS_OWNER":
        return s.github_comentarios_owner
    if name == "GITHUB_COMENTARIOS_REPO":
        return s.github_comentarios_repo
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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

    s = _core_config.settings
    secret_file = s.data_dir / ".admin_jwt_secret"
    try:
        if secret_file.exists():
            return secret_file.read_text().strip()
    except Exception as exc:
        logger.warning("No se pudo leer %s: %s", secret_file, exc)

    generated = secrets.token_urlsafe(48)
    try:
        s.data_dir.mkdir(parents=True, exist_ok=True)
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
