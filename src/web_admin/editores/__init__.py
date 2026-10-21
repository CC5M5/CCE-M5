"""Utilidades compartidas para los editores legacy Flask de CCE-M5."""

from __future__ import annotations

from src.web_admin.editores.db import get_connection, get_momentos_cancion, set_momentos_cancion
from src.web_admin.editores.git import git_commit

__all__ = ["get_connection", "get_momentos_cancion", "git_commit", "set_momentos_cancion"]
