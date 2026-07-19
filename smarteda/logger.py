"""Logging básico y centralizado.

Se usa el módulo estándar `logging` (sin dependencias externas) para dejar
trazas claras de cada etapa del análisis. Un único punto de configuración evita
que cada módulo repita la misma inicialización.
"""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def get_logger(name: str = "smarteda", level: int = logging.INFO) -> logging.Logger:
    """Devuelve un logger configurado.

    Args:
        name: Nombre del logger (normalmente el nombre del módulo).
        level: Nivel mínimo de log (por defecto INFO).

    Returns:
        Un `logging.Logger` listo para usar, con un único handler de consola.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(level)
    return logger
