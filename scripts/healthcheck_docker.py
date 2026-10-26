#!/usr/bin/env python3
"""Healthcheck para el contenedor Docker de CCE-M5.

Verifica:
1. Admin API responde en /health con status ok.
2. La base de datos SQLite es accesible y pasa PRAGMA integrity_check.
3. El servidor web estático sirve index.html.
4. Los editores legacy Flask montados responden.

Salida: 0 si todo bien, 1 en caso contrario.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError

DEFAULT_ADMIN_URL = "http://127.0.0.1:4323"
DEFAULT_WEB_URL = "http://127.0.0.1:4321"


def _fetch(url: str, timeout: float = 5.0) -> tuple[int, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, None
    except HTTPError as exc:
        return exc.code, str(exc)
    except URLError as exc:
        return 0, str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def _check_admin(admin_url: str, timeout: float) -> tuple[bool, str]:
    url = admin_url.rstrip("/") + "/health"
    status, err = _fetch(url, timeout=timeout)
    if status != 200:
        return False, f"admin API /health no responde: {status} {err or ''}"

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        return False, f"no se pudo leer /health: {exc}"

    if '"status": "ok"' not in body and '"status":"ok"' not in body:
        return False, f"/health no reporta ok: {body[:200]}"
    return True, "ok"


def _check_database(db_path: Path) -> tuple[bool, str]:
    if not db_path.exists():
        return False, f"No existe la base de datos: {db_path}"
    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            result = row[0] if row else "unknown"
            if result != "ok":
                return False, f"integrity_check falló: {result}"
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return False, f"error SQLite: {exc}"
    return True, "ok"


def _check_web(web_url: str, timeout: float) -> tuple[bool, str]:
    status, err = _fetch(web_url.rstrip("/") + "/", timeout=timeout)
    if status != 200:
        return False, f"web estática no responde: {status} {err or ''}"
    return True, "ok"


def _check_editors(admin_url: str, timeout: float) -> tuple[bool, str]:
    failures = []
    for path in ("/editor-acordes/", "/editor-diapositivas/"):
        status, err = _fetch(admin_url.rstrip("/") + path, timeout=timeout)
        if status not in (200, 302, 307, 308):
            failures.append(f"{path}: {status} {err or ''}")
    if failures:
        return False, "; ".join(failures)
    return True, "ok"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Healthcheck Docker CCE-M5")
    parser.add_argument("--admin-url", default=DEFAULT_ADMIN_URL, help="URL base del admin API")
    parser.add_argument("--web-url", default=DEFAULT_WEB_URL, help="URL base del servidor web")
    parser.add_argument("--db-path", default="/app/data/db.sqlite3", help="Ruta a la BD SQLite")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout por petición")
    parser.add_argument("--skip-editors", action="store_true", help="No comprobar editores legacy")
    args = parser.parse_args(argv)

    checks = [
        ("admin API", _check_admin(args.admin_url, args.timeout)),
        ("database", _check_database(Path(args.db_path))),
        ("static web", _check_web(args.web_url, args.timeout)),
    ]
    if not args.skip_editors:
        checks.append(("editors", _check_editors(args.admin_url, args.timeout)))

    all_ok = True
    for name, (ok, msg) in checks:
        status = "OK" if ok else "FAIL"
        print(f"{status:4} {name}: {msg}")
        if not ok:
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
