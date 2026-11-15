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
    # S5/S6: posiciones guardadas de la imagen y el texto (JSON en per-mille);
    # None o inválido significa el diseño fijo (NULL en la BD).
    imagen_pos: str | None = None
    texto_pos: str | None = None
