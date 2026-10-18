"""Configuración centralizada de logging para CCE-M5.

Uso:
    from log_config import get_logger

    logger = get_logger(__name__)
    logger.info("mensaje")
"""

import logging
import sys

# Nivel por defecto: INFO; puede sobrescribirse con la variable de entorno CCE_LOG_LEVEL
DEFAULT_LOG_LEVEL = "INFO"
LOG_LEVEL = getattr(logging, (getenv_level := (__import__('os').environ.get('CCE_LOG_LEVEL') or DEFAULT_LOG_LEVEL)).upper(), logging.INFO)


def _ensure_handler():
    """Asegura un único handler de consola en el root logger."""
    root = logging.getLogger()
    # Evitar duplicar handlers si ya hay uno de tipo StreamHandler apuntando a stderr
    if any(isinstance(h, logging.StreamHandler) and h.stream is sys.stderr for h in root.handlers):
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(LOG_LEVEL)


# Configurar root logger al importar el módulo
_ensure_handler()


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger configurado con el nombre del módulo."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    return logger
