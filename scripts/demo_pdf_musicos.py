#!/usr/bin/env python3
"""
Script demo para generar la hoja de músicos de una celebración de ejemplo.

Utiliza canciones reales que ya existen en data/db.sqlite3, asignándolas a
los 12 momentos litúrgicos para validar el posicionamiento de acordes y el
formato A4 del generador.

Uso:
    python scripts/demo_pdf_musicos.py
"""

import logging
import sys
from pathlib import Path

# Asegura que el proyecto raíz está en sys.path cuando se ejecuta directamente.
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.generators.pdf_musicos import generar_hoja_musicos


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Canciones disponibles en la base de datos actual (ids reales):
    # 2 - A TU AMPARO Y PROTECCIÓN (Do)
    # 3 - AQUÍ ESTOY, SEÑOR (SALMO 39) (Sol)     -> adecuado para Salmo
    # 4 - CANTAD CON GOZO (RE)                   -> Adviento / Aleluya
    # 5 - EL ESPÍRITU DEL SEÑOR, PENTECOSTÉS (KAIROI) (G)
    # 6 - HOY COMO AYER (C)                    -> Paz / comunidad
    # 7 - MARÍA, MÚSICA DE DIOS (DO)            -> Canto a María
    # 8 - PREPARAD EL CAMINO (SOL)             -> Entrada / Adviento
    # 9 - GLORIA TE DAMOS GRACIAS, SEÑOR (R. CARISMÁTICA) (A) -> Gloria / Santo
    #
    # Solo hay 8 canciones reales (ids 2..9) frente a 12 momentos litúrgicos,
    # así que inevitablemente algunas se repiten.  Se ha intentado asignar
    # canciones que encajen con el carácter del momento (p. ej. salmo, gloria,
    # maría) y se completan los huecos con las restantes sin repetir
    # excesivamente.
    canciones_por_momento = {
        "Entrada": 8,          # Preparad el camino
        "Perdón": 2,           # A tu amparo
        "Gloria": 9,           # Gloria te damos
        "Salmo": 3,            # Aquí estoy, Señor (Salmo 39)
        "Aleluya": 4,          # Cantad con gozo
        "Ofertorio": 6,        # Hoy como ayer
        "Santo": 9,            # Gloria te damos (repetición necesaria)
        "Padre Nuestro": 5,    # El Espíritu del Señor
        "Paz": 6,              # Hoy como ayer (repetición necesaria)
        "Comunión": 2,         # A tu amparo (repetición necesaria)
        "Canto a María": 7,    # María, música de Dios
        "Despedida": 8,        # Preparad el camino (repetición necesaria)
    }

    notas = [
        "Tono general: Do",
        "Evento especial: Confirmación de Pedro (modificar Gloria y Comunión)",
        "Ensayo: Sábado 19:00h",
    ]

    output = generar_hoja_musicos(
        fecha_domingo="2026-09-13",
        canciones_por_momento=canciones_por_momento,
        notas=notas,
        celebracion="Domingo XXIV T.O.",
    )

    print(f"PDF generado: {output}")


if __name__ == "__main__":
    main()
