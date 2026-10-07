"""Reconstrucción compartida del sitio Astro tras cambios en la base de datos.

Usado por:
- Editor de acordes (Flask, puerto 4322)
- Editor de diapositivas (Flask, puerto 4323)
- Admin API / cancionero web (FastAPI, puerto 4324)

Exporta SQLite a JSON, corre `npm run build` y reinicia el servidor web
estático en el puerto 4321.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
NODE_BIN = "/home/pciath/.nvm/versions/node/v22.23.3/bin"


def rebuild_web() -> str:
    """Exporta datos, reconstruye Astro y reinicia el servidor web en 4321."""
    try:
        env = os.environ.copy()
        env["BASE_PATH"] = "/"
        env["SITE_URL"] = "http://192.168.68.244:4321"
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

        subprocess.run(
            [f"{NODE_BIN}/npm", "run", "build"],
            cwd=PROJECT_DIR / "web",
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        subprocess.run(
            "ps aux | grep 'http.server 4321' | grep -v grep | awk '{print $2}' | xargs -r kill 2>/dev/null",
            shell=True,
            check=False,
            capture_output=True,
        )
        time.sleep(1)

        subprocess.Popen(
            ["/usr/bin/python3", "-m", "http.server", "4321",
             "--directory", str(PROJECT_DIR / "web" / "dist"),
             "--bind", "0.0.0.0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        return "rebuild OK"
    except subprocess.CalledProcessError as exc:
        err = exc.stderr or exc.stdout or ""
        err_short = err.strip().splitlines()[-1] if err else "error desconocido"
        return f"ERROR rebuild: {err_short}"
    except Exception as exc:
        return f"ERROR rebuild: {exc}"
