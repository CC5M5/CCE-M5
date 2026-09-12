#!/usr/bin/env python3
"""
Script de inicialización de la base de datos.

Uso:
    python scripts/init_db.py
    CCE_PROJECT_DIR=/ruta/al/proyecto python scripts/init_db.py
"""

import logging
import sys
from pathlib import Path

# Añadir src al path para importar db_manager
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from db_manager import init_database


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    init_database()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
