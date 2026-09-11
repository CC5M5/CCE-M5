#!/usr/bin/env python3
"""
Script de demostración del generador de presentaciones PPTX.
"""

import logging
from pathlib import Path

from presentacion_fieles import GeneradorPPTX

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def probar_generador() -> None:
    """Prueba el generador con datos de ejemplo."""
    logger.info("=" * 70)
    logger.info("GENERADOR DE PRESENTACIONES PPTX")
    logger.info("=" * 70)

    generador = GeneradorPPTX()

    generador.crear_diapositiva_titulo(
        "Domingo XXIV del Tiempo Ordinario",
        "14 de septiembre de 2026",
        "verde",
    )

    generador.crear_diapositiva_cancion(
        "PREPARAD EL CAMINO",
        "PREPARAD EL CAMINO AL SEÑOR\nY ESCUCHAD LA PALABRA DE DIOS.(Bis)",
        "Entrada",
        "blanco",
    )

    output_dir = Path(__file__).parent.parent.parent / "presentaciones"
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "prueba_presentacion.pptx"
    generador.prs.save(str(filepath))

    logger.info("Presentación de prueba: %s", filepath)
    logger.info("Diapositivas: %s", len(generador.prs.slides))
    logger.info("=" * 70)


if __name__ == "__main__":
    probar_generador()
