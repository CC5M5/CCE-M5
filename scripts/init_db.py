#!/usr/bin/env python3
"""
Script de inicialización de la base de datos.

Uso:
    python scripts/init_db.py
    CCE_PROJECT_DIR=/ruta/al/proyecto python scripts/init_db.py
"""

from __future__ import annotations

from src.db_manager import init_database
from src.log_config import get_logger

logger = get_logger(__name__)


def main() -> int:
    init_database()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
