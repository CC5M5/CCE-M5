#!/usr/bin/env python3
"""
Mock de lecturas para desarrollo y testing.
Usar cuando Koinonia no este disponible.
"""

from datetime import datetime, timedelta

LECTURAS_MOCK = {
    "20260914": {
        "fecha": "20260914",
        "celebracion": "Domingo XXIV del Tiempo Ordinario",
        "domingo": "XXIV Domingo Ordinario",
        "temporada": "ordinario",
        "ciclo": "C",
        "color_liturgico": "verde",
        "primera_lectura_cita": "Am 8, 4-7",
        "primera_lectura_texto": "Escuchad esto, los que pisoteáis al pobre y arruináis a los humildes del país...",
        "salmo_cita": "Sal 112 (113)",
        "salmo_antifona": "Dichoso el hombre que teme al Señor.",
        "salmo_texto": "Aleluia. Dichoso el hombre que teme al Señor...",
        "segunda_lectura_cita": "1 Tm 2, 1-8",
        "segunda_lectura_texto": "En primer lugar, os exhorto a que pidáis, oréis, intercedáis y déis gracias por todos...",
        "evangelio_cita": "Lc 16, 1-13",
        "evangelio_texto": "En aquel tiempo, Jesús dijo a sus discípulos: 'Había un hombre rico que tenía un administrador...'"
    },
    "20260921": {
        "fecha": "20260921",
        "celebracion": "Domingo XXV del Tiempo Ordinario",
        "domingo": "XXV Domingo Ordinario",
        "temporada": "ordinario",
        "ciclo": "C",
        "color_liturgico": "verde",
        "primera_lectura_cita": "Am 9, 11-15",
        "primera_lectura_texto": "Aquél día levantaré la tienda caída de David...",
        "salmo_cita": "Sal 84 (85)",
        "salmo_antifona": "El Señor hablará de paz a su pueblo.",
        "salmo_texto": "Escuchad lo que dice el Señor, palabras de paz...",
        "segunda_lectura_cita": "Ef 4, 1-7. 11-13",
        "segunda_lectura_texto": "Yo, preso por el Señor, os exhorto a que andéis como corresponde a la vocación...",
        "evangelio_cita": "Mc 9, 30-37",
        "evangelio_texto": "De camino, Jesús les decía: 'El Hijo del hombre va a ser entregado...'"
    }
}

def obtener_mock(fecha_codigo):
    """Obtiene lecturas mock para una fecha"""
    return LECTURAS_MOCK.get(fecha_codigo)

def generar_mock_aleatorio(fecha_codigo):
    """Genera un mock aleatorio si no existe"""
    return {
        "fecha": fecha_codigo,
        "celebracion": f"Domingo del Tiempo Ordinario",
        "domingo": "Domingo Ordinario",
        "temporada": "ordinario",
        "ciclo": "C",
        "color_liturgico": "verde",
        "primera_lectura_cita": "Gn 1, 1-10",
        "primera_lectura_texto": "En el principio creó Dios el cielo y la tierra...",
        "salmo_cita": "Sal 23 (24)",
        "salmo_antifona": "El Señor es mi pastor.",
        "salmo_texto": "El Señor es mi pastor, nada me falta...",
        "segunda_lectura_cita": "Fil 4, 4-9",
        "segunda_lectura_texto": "Estad siempre alegres en el Señor...",
        "evangelio_cita": "Mt 5, 1-12",
        "evangelio_texto": "Viendo Jesús a la multitud, subió al monte..."
    }

if __name__ == "__main__":
    # Test
    lecturas = obtener_mock("20260914")
    print(f"Mock para 14 Sep 2026: {lecturas['celebracion']}")
