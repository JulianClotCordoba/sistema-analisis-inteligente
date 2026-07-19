"""Excepciones propias del sistema.

Se definen excepciones específicas para que el frontend (Jose) y la capa de
integración (Rachel) puedan distinguir con claridad qué tipo de error ocurrió
y mostrar mensajes útiles al usuario, en lugar de recibir errores genéricos.
"""

from __future__ import annotations


class SmartEdaError(Exception):
    """Excepción base de la que heredan todas las demás del proyecto."""


class FileValidationError(SmartEdaError):
    """El archivo no existe, no es un archivo o no se puede leer."""


class UnsupportedFileFormatError(SmartEdaError):
    """La extensión del archivo no está soportada (solo CSV/TSV/Excel)."""


class EmptyDatasetError(SmartEdaError):
    """El archivo se cargó pero no contiene filas o columnas."""


class InsufficientDataError(SmartEdaError):
    """No hay datos suficientes (p. ej. columnas numéricas) para un análisis."""
