#!/usr/bin/env python3
"""
Demo del scraper de Blogspot: obtiene la pagina principal y muestra los enlaces
encontrados, sin guardar en la base de datos.
"""

import json
import logging
import os
from pathlib import Path

from scraper_blogspot import CancioneroScraper, BASE_URL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def probar_scraper(url: str = BASE_URL) -> None:
    """Prueba rapida del scraper listando canciones encontradas."""
    with CancioneroScraper() as scraper:
        html = scraper._get_page(url)
        if not html:
            logger.error("No se pudo obtener la pagina principal")
            return

        canciones = scraper.extraer_enlaces_canciones(html)
        logger.info(f"Total de canciones encontradas: {len(canciones)}")
        for i, cancion in enumerate(canciones[:10], 1):
            logger.info(f"{i}. {cancion['titulo']} -> {cancion['url']}")

        if len(canciones) > 10:
            logger.info(f"... y {len(canciones) - 10} mas")

        print(json.dumps(canciones, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    probar_scraper()
