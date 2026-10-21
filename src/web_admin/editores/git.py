"""Helpers de git para los editores Flask legacy."""

from __future__ import annotations

import re
import subprocess

from src.config import settings

PROJECT_DIR = settings.project_dir


def git_commit(message: str, *, extra_paths: list[str] | None = None) -> str:
    """Hace git add + commit + push. Devuelve el hash o un mensaje de error.

    Args:
        message: Mensaje principal del commit (se antepone el prefijo adecuado).
        extra_paths: Rutas adicionales (relativas a project_dir) a incluir en el add.
    """
    try:
        paths = ["data/db.sqlite3", *(extra_paths or [])]
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
            return "sin cambios"

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
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        m = re.search(r"\[main ([a-f0-9]+)\]", result.stdout)
        return m.group(1) if m else "commit OK"
    except subprocess.CalledProcessError as exc:
        err = exc.stderr or exc.stdout or ""
        if (
            "nothing to commit" in err
            or "working tree clean" in err
            or "No changes" in err
            or "sin cambios agregados" in err
        ):
            return "sin cambios"
        return f"ERROR: {err}"
