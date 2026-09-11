#!/usr/bin/env python3
"""Script de demostracion del scraper de Koinonia."""

import logging
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from scrapers.koinonia_scraper import KoinoniaClient, KoinoniaRepository, KoinoniaScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Obtiene y guarda las lecturas del proximo domingo."""
    with KoinoniaClient() as client:
        scraper = KoinoniaScraper(client=client, repo=KoinoniaRepository())
        lecturas = scraper.obtener_proximo_domingo()

    if lecturas:
        scraper.guardar_en_db(lecturas)
        logger.info("Celebracion: %s", lecturas.get('celebracion', 'No detectada'))
        logger.info("Temporada: %s", lecturas.get('temporada', 'No detectada'))
    else:
        logger.error("No se pudieron obtener las lecturas")


if __name__ == "__main__":
    main()
