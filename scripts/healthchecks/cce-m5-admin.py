#!/usr/bin/env python3
"""Healthcheck simple para el servicio CCE-M5 Admin API."""

import json
import sys
import urllib.request

URLS = [
    "http://127.0.0.1:4323/health",
    "http://127.0.0.1:4323/admin/login.html",
]


def check(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as exc:
        print(f"FAIL {url}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    checks = {u: check(u) for u in URLS}
    ok = all(checks.values())
    status = {"healthy": ok, "checks": checks}
    print(json.dumps(status))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
