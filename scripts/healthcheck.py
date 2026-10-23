#!/usr/bin/env python3
"""Healthcheck ligero para los servicios CCE-M5.

Se ejecuta desde systemd, cron o docker HEALTHCHECK y devuelve 0 si todos
los endpoints responden, 1 en caso contrario.

Uso:
    python scripts/healthcheck.py
    python scripts/healthcheck.py --base-url http://localhost:4323 --web-url http://localhost:4321
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from urllib.error import HTTPError, URLError

ENDPOINTS = [
    ("/health", "admin API"),
    ("/editor-acordes/", "editor acordes"),
    ("/editor-diapositivas/", "editor diapositivas"),
]


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Healthcheck CCE-M5")
    parser.add_argument("--admin-url", default="http://127.0.0.1:4323", help="URL base del admin API")
    parser.add_argument("--web-url", default="http://127.0.0.1:4321", help="URL base del servidor web")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout por petición")
    args = parser.parse_args(argv)

    all_ok = True

    for path, name in ENDPOINTS:
        url = args.admin_url.rstrip("/") + path
        status, err = _fetch(url, timeout=args.timeout)
        ok = status == 200
        if not ok:
            all_ok = False
            print(f"FAIL {name}: {url} -> {status} {err or ''}")
        else:
            print(f"OK   {name}: {url} -> {status}")

    web_status, web_err = _fetch(args.web_url, timeout=args.timeout)
    if web_status == 200:
        print(f"OK   web: {args.web_url} -> {web_status}")
    else:
        all_ok = False
        print(f"FAIL web: {args.web_url} -> {web_status} {web_err or ''}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
