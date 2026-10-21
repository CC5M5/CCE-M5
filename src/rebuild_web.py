"""Reconstrucción compartida del sitio Astro tras cambios en la base de datos.

Usado por:
- Editor de acordes (Flask, puerto 4322)
- Editor de diapositivas (Flask, puerto 4324)
- Admin API / cancionero web (FastAPI, puerto 4323)

Exporta SQLite a JSON, corre `npm run build` y reinicia el servidor web
estático en el puerto 4321.

Variables de entorno opcionales:
  CCE_PROJECT_DIR  - raíz del proyecto (por defecto: directorio padre de este archivo)
  CCE_NODE_BIN     - directorio con node/npm (por defecto: /usr/bin)
  CCE_BASE_PATH    - base path de Astro (por defecto: /)
  CCE_SITE_URL     - URL base del site local (por defecto: http://localhost:4321)
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CCE_PROJECT_DIR", Path(__file__).resolve().parents[1]))
NODE_BIN = os.environ.get("CCE_NODE_BIN", "/usr/bin")


def rebuild_web() -> str:
    """Exporta datos, reconstruye Astro y reinicia el servidor web en 4321."""
    try:
        env = os.environ.copy()
        env["BASE_PATH"] = os.environ.get("CCE_BASE_PATH", "/")
        env["SITE_URL"] = os.environ.get("CCE_SITE_URL", "http://localhost:4321")
        env["PATH"] = f"{NODE_BIN}:{env.get('PATH', '')}"

        export_script = PROJECT_DIR / "scripts" / "export_data_for_web.py"
        subprocess.run(
            ["python3", str(export_script)],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        npm_cmd = os.path.join(NODE_BIN, "npm")
        subprocess.run(
            [npm_cmd, "run", "build"],
            cwd=PROJECT_DIR / "web",
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        # Reiniciar el servicio systemd del servidor web estático para servir la nueva build.
        subprocess.run(
            ["systemctl", "--user", "restart", "cce-m5-web.service"],
            check=False,
            capture_output=True,
        )
        time.sleep(2)

        return "rebuild OK"
    except subprocess.CalledProcessError as exc:
        err = exc.stderr or exc.stdout or ""
        err_short = err.strip().splitlines()[-1] if err else "error desconocido"
        return f"ERROR rebuild: {err_short}"
    except Exception as exc:
        return f"ERROR rebuild: {exc}"
