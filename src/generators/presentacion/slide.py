"""Modelo de diapositiva y utilidades básicas de formato de texto."""

from dataclasses import dataclass


@dataclass
class Slide:
    numero: int
    tipo: str
    titulo: str
    contenido: str
    cita: str = ""
    subtitulo: str = ""
    momento: str = ""
    imagen: str = ""
