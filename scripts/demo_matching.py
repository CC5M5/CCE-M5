#!/usr/bin/env python3
"""Script de demostración del motor de matching temático."""

import logging
import sqlite3

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from matching_engine import MatchingEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def probar_matching() -> None:
    """Prueba el motor de matching con la primera lectura disponible."""
    logger.info("=" * 70)
    logger.info("MOTOR DE MATCHING TEMATICO")
    logger.info("=" * 70)

    engine = MatchingEngine()

    try:
        with sqlite3.connect(str(engine.service.config.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, celebracion FROM lecturas LIMIT 1")
            lectura = cursor.fetchone()
    except sqlite3.Error:
        lectura = None

    if not lectura:
        logger.warning("No hay lecturas en la base de datos.")
        logger.info("Ejecutar primero: python src/scrapers/koinonia_scraper.py")
        return

    lectura_id = lectura["id"]
    celebracion = lectura["celebracion"]
    logger.info("Lectura: %s (ID: %s)", celebracion, lectura_id)

    matches = engine.encontrar_canciones_para_lectura(lectura_id, limite=5)

    if matches:
        logger.info("Encontradas %s coincidencias:", len(matches))
        for i, match in enumerate(matches, 1):
            logger.info("%s. %s", i, match["titulo"])
            logger.info("   Score: %s", match["score"])
            logger.info("   Temas: %s", ", ".join(match["temas_comunes"]))
            logger.info("   Momento liturgico: %s", match["momento_liturgico"])
    else:
        logger.info("No se encontraron coincidencias")

    logger.info("=" * 70)


if __name__ == "__main__":
    probar_matching()
