"""Healthcheck más completo para CCE-M5 admin API.

Además de responder "ok", verifica que la base de datos SQLite es accesible y
pasa `PRAGMA integrity_check`, y opcionalmente que la web estática servida por
el contenedor está viva.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.config import settings


def check_database(db_path: Path | None = None) -> dict[str, object]:
    """Verifica que la BD es legible y pasa integrity_check."""
    target = db_path or settings.db_path
    if not target.exists():
        return {"ok": False, "error": f"No existe la base de datos: {target}"}

    try:
        conn = sqlite3.connect(str(target), timeout=5.0)
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            integrity = row[0] if row else "unknown"
            if integrity != "ok":
                return {"ok": False, "error": f"integrity_check: {integrity}"}

            tables = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ]
            return {"ok": True, "tables": len(tables)}
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"ok": False, "error": f"sqlite error: {exc}"}


def check_static_web(web_dir: Path | None = None, *, required: bool = False) -> dict[str, object]:
    """Verifica que existe un build estático de la web.

    Si `required` es False, una web ausente se reporta como ok pero con un aviso,
    para no degradar el healthcheck en entornos donde solo corre la API.
    """
    target = web_dir or settings.web_dir / "dist"
    index = target / "index.html"
    if not index.exists():
        result = {"ok": not required, "error": f"No se encontró {index}"}
        if not required:
            result["note"] = "web estática no es requerida para este healthcheck"
        return result
    return {"ok": True, "index_html_size": index.stat().st_size}


def full_health_report(*, require_static_web: bool = False) -> dict[str, object]:
    """Devuelve el estado combinado de API + BD + web estática."""
    db_result = check_database()
    web_result = check_static_web(required=require_static_web)
    ok = db_result["ok"] and web_result["ok"]
    return {
        "status": "ok" if ok else "degraded",
        "service": "cce-m5-admin",
        "database": db_result,
        "static_web": web_result,
    }
