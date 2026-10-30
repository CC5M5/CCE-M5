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
import sys
import time

from src.config import settings

PROJECT_DIR = settings.project_dir
NODE_BIN = settings.node_bin
WEB_DIR = settings.web_dir


def rebuild_web() -> str:
    """Exporta datos, reconstruye Astro y reinicia el servidor web en 4321."""
    try:
        env = os.environ.copy()
        env["BASE_PATH"] = settings.base_path
        env["SITE_URL"] = settings.site_url
        env["PATH"] = f"{NODE_BIN}:{env.get('PATH', '')}"

        export_script = PROJECT_DIR / "scripts" / "export_data_for_web.py"
        subprocess.run(
            [sys.executable, str(export_script)],
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
        try:
            subprocess.run(
                ["systemctl", "--user", "restart", "cce-m5-web.service"],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError:
            # Entornos sin systemd (p. ej. Docker): la build quedó lista en web/dist.
            return "rebuild OK (sin reinicio: systemctl no disponible)"
        except subprocess.CalledProcessError as exc:
            err = exc.stderr or exc.stdout or ""
            err_short = err.strip().splitlines()[-1] if err else "error desconocido"
            if ": " in err_short:
                err_short = err_short.rsplit(": ", 1)[-1]
            return f"rebuild OK con error al reiniciar web: {err_short}"
        time.sleep(2)

        return "rebuild OK"
    except subprocess.CalledProcessError as exc:
        err = exc.stderr or exc.stdout or ""
        err_short = err.strip().splitlines()[-1] if err else "error desconocido"
        return f"ERROR rebuild: {err_short}"
    except Exception as exc:
        return f"ERROR rebuild: {exc}"
