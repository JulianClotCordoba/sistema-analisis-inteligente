"""Carga dinámica y validación de archivos de datos tabulares.

Soporta CSV, TSV y Excel (.xlsx/.xls). Acepta tanto una ruta en disco como un
objeto tipo archivo (por ejemplo, el que entrega Streamlit al subir un archivo),
para que la integración con el frontend de Jose sea directa.
"""

from __future__ import annotations

from pathlib import Path
from typing import IO, Any, Union

import pandas as pd

from .exceptions import (
    EmptyDatasetError,
    FileValidationError,
    UnsupportedFileFormatError,
)
from .logger import get_logger

logger = get_logger(__name__)

# Extensiones soportadas -> tipo interno de lector.
_CSV_EXTENSIONS = {".csv", ".tsv", ".txt"}
_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
SUPPORTED_EXTENSIONS = _CSV_EXTENSIONS | _EXCEL_EXTENSIONS

Source = Union[str, Path, IO[Any]]


def _resolve_name(source: Source) -> str:
    """Obtiene el nombre del archivo desde una ruta o un objeto tipo archivo."""
    if isinstance(source, (str, Path)):
        return str(source)
    name = getattr(source, "name", None)
    if not name:
        raise FileValidationError(
            "No se pudo determinar el nombre del archivo para inferir su formato."
        )
    return str(name)


def _validate_path(path: Path) -> None:
    """Valida que una ruta exista y sea un archivo legible."""
    if not path.exists():
        raise FileValidationError(f"El archivo no existe: {path}")
    if not path.is_file():
        raise FileValidationError(f"La ruta no es un archivo: {path}")


def _validate_dataframe(df: pd.DataFrame, name: str) -> None:
    """Valida que el DataFrame cargado tenga contenido real."""
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise EmptyDatasetError(f"El archivo '{name}' no contiene datos (filas o columnas).")


def load_dataset(source: Source, **read_kwargs: Any) -> pd.DataFrame:
    """Carga un archivo tabular en un DataFrame de pandas.

    Args:
        source: Ruta al archivo o un objeto tipo archivo (con atributo `name`).
        **read_kwargs: Argumentos extra que se pasan al lector de pandas
            (por ejemplo `sep`, `sheet_name`, `encoding`).

    Returns:
        Un `pandas.DataFrame` con los datos cargados.

    Raises:
        FileValidationError: Si la ruta no existe o no es un archivo.
        UnsupportedFileFormatError: Si la extensión no está soportada.
        EmptyDatasetError: Si el archivo no contiene datos.
    """
    name = _resolve_name(source)
    suffix = Path(name).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileFormatError(
            f"Formato no soportado: '{suffix}'. "
            f"Use uno de: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
        )

    # Si es una ruta, validamos su existencia antes de leer.
    if isinstance(source, (str, Path)):
        _validate_path(Path(source))

    logger.info("Cargando archivo '%s' (formato %s)", name, suffix)

    try:
        if suffix in _CSV_EXTENSIONS:
            sep = read_kwargs.pop("sep", "\t" if suffix == ".tsv" else ",")
            df = pd.read_csv(source, sep=sep, **read_kwargs)
        else:  # Excel
            df = pd.read_excel(source, **read_kwargs)
    except UnicodeDecodeError as exc:
        raise FileValidationError(
            f"No se pudo decodificar '{name}'. Pruebe indicando encoding='latin-1'."
        ) from exc
    except ValueError as exc:
        # pandas lanza ValueError ante contenido corrupto o motor faltante.
        raise FileValidationError(f"No se pudo leer '{name}': {exc}") from exc

    _validate_dataframe(df, name)
    logger.info("Archivo cargado: %d filas x %d columnas", df.shape[0], df.shape[1])
    return df
