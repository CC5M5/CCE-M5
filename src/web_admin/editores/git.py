"""Helpers de git para los editores Flask legacy."""

from __future__ import annotations

import re
import subprocess

from src.config import settings

PROJECT_DIR = settings.project_dir

# Rutas versionadas que alimentan el build estático de Astro/GitHub Pages.
# data/db.sqlite3 es un binario de runtime y está en .gitignore; nunca se commitea.
DEFAULT_VERSIONED_PATHS = [
    "web/data/canciones.json",
    "web/data/cancion_momentos.json",
    "web/data/presentaciones.json",
    "web/data/comentarios.json",
]


def _existing_paths(rel_paths: list[str]) -> list[str]:
    """Devuelve solo las rutas que existen en disco para evitar errores de git add."""
    existing: list[str] = []
    for p in rel_paths:
        if (PROJECT_DIR / p).exists():
            existing.append(p)
    return existing


def _git_stage_and_commit(message: str, paths: list[str]) -> tuple[str, str]:
    """Ejecuta git add + commit. Devuelve (status, output_or_error).

    Args:
        message: Mensaje principal del commit.
        paths: Rutas relativas a PROJECT_DIR para añadir.

    Returns:
        ("ok", hash_corto) o ("error", mensaje_de_error).
    """
    try:
        subprocess.run(
            ["git", "add", *paths],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=PROJECT_DIR,
            check=False,
            capture_output=True,
            text=True,
        )
        if diff_check.returncode == 0:
            return ("ok", "sin cambios")

        result = subprocess.run(
            [
                "git",
                "commit",
                "-m",
                message,
                "-m",
                "Actualización manual desde editor CCE-M5.",
            ],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        m = re.search(r"\[main ([a-f0-9]+)\]", result.stdout)
        return ("ok", m.group(1) if m else "commit OK")
    except subprocess.CalledProcessError as exc:
        err = exc.stderr or exc.stdout or ""
        if (
            "nothing to commit" in err
            or "working tree clean" in err
            or "No changes" in err
            or "sin cambios agregados" in err
        ):
            return ("ok", "sin cambios")
        return ("error", err)


def _git_push() -> tuple[str, str]:
    """Hace git push origin main. Devuelve (status, output_or_error)."""
    try:
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        return ("ok", "")
    except subprocess.CalledProcessError as exc:
        err = exc.stderr or exc.stdout or ""
        return ("error", err)


def git_commit(message: str, *, extra_paths: list[str] | None = None) -> str:
    """Hace git add + commit + push de los datos versionados.

    Args:
        message: Mensaje principal del commit.
        extra_paths: Rutas adicionales (relativas a project_dir) a incluir en el add.

    Returns:
        Hash corto del commit, "sin cambios" o un mensaje de error.
    """
    paths = _existing_paths([*DEFAULT_VERSIONED_PATHS, *(extra_paths or [])])
    if not paths:
        return "sin cambios"

    status, result = _git_stage_and_commit(message, paths)
    if status == "error" or result == "sin cambios":
        return result if status == "ok" else f"ERROR: {result}"

    push_status, push_err = _git_push()
    if push_status == "error":
        return f"ERROR: {push_err}"

    return result
