"""Autenticación JWT + bcrypt para el panel de administración."""

from __future__ import annotations

import datetime
import logging
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.web_admin.config import (
    DEFAULT_ADMIN_NAME,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    JWT_ALGORITHM,
    JWT_SECRET,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from src.web_admin.database import create_user, get_user_by_username, init_admin_schema

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _hash_password(password: str) -> str:
    return hash_password(password)


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(username: str, role: str) -> str:
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": username,
        "role": role,
        "exp": expires,
        "iat": datetime.datetime.now(datetime.timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc


def seed_default_admin() -> None:
    """Crea el usuario administrador inicial si no existe."""
    init_admin_schema()
    existing = get_user_by_username(DEFAULT_ADMIN_USERNAME)
    if existing:
        logger.info("Usuario admin '%s' ya existe", DEFAULT_ADMIN_USERNAME)
        return

    hashed = _hash_password(DEFAULT_ADMIN_PASSWORD)
    user_id = create_user(
        username=DEFAULT_ADMIN_USERNAME,
        password_hash=hashed,
        full_name=DEFAULT_ADMIN_NAME,
        role="admin",
    )
    logger.info("Usuario admin inicial creado: %s (id=%d)", DEFAULT_ADMIN_USERNAME, user_id)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = get_user_by_username(username)
    if not user or not user.is_active:
        return None
    if not _verify_password(password, user.password_hash):
        return None
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
    }


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="No se proporcionó token")
    payload = decode_access_token(credentials.credentials)
    user = get_user_by_username(payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
    }


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")
    return current_user


# ---------------------------------------------------------------------------
# Helpers de gestión de usuarios
# ---------------------------------------------------------------------------


def create_new_user(
    username: str,
    password: str,
    full_name: Optional[str] = None,
    role: str = "viewer",
) -> int:
    init_admin_schema()
    if role not in ("admin", "viewer"):
        raise ValueError("Rol no válido")
    existing = get_user_by_username(username)
    if existing:
        raise ValueError("El usuario ya existe")
    hashed = hash_password(password)
    return create_user(username=username, password_hash=hashed, full_name=full_name, role=role)


def change_user_password(user_id: int, new_password: str) -> None:
    from src.web_admin.database import get_user_by_id, set_user_password

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Usuario no encontrado")
    set_user_password(user_id, hash_password(new_password))
