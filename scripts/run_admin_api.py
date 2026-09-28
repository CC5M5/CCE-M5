#!/usr/bin/env python3
"""Lanza la API de administración de CCE-M5.

Uso:
    python scripts/run_admin_api.py
    python scripts/run_admin_api.py --host 0.0.0.0 --port 4323
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.resolve()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import uvicorn
from src.web_admin.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from src.web_admin.database import init_admin_schema


def main() -> None:
    parser = argparse.ArgumentParser(description="API de administración CCE-M5")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=4323)
    args = parser.parse_args()

    init_admin_schema()
    print(f"API de administración en http://{args.host}:{args.port}")
    print(f"Usuario por defecto: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")
    print("⚠️  Cambia la contraseña en producción con CCE_ADMIN_DEFAULT_PASSWORD")

    uvicorn.run(
        "src.web_admin.api:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
