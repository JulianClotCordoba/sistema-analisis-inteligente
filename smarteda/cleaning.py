"""Limpieza básica del dataset.

Cubre el requisito de "limpieza básica" que menciona el alcance de la propuesta,
como parte del procesamiento automático previo al análisis. Son operaciones
seguras y no destructivas del contenido útil:

- Recorta espacios en blanco de las columnas de texto.
- Convierte cadenas vacías en valores faltantes (NaN).
- Elimina columnas y filas completamente vacías.
- Elimina filas duplicadas exactas.

La imputación de faltantes para los algoritmos de ML se realiza aparte, en la
capa de preprocesamiento, porque solo aplica al subconjunto numérico.
"""

from __future__ import annotations

import pandas as pd
from pandas.api import types as ptypes

from .logger import get_logger

logger = get_logger(__name__)


def _is_text_column(series: pd.Series) -> bool:
    """True si la columna es de texto (no numérica, booleana ni temporal)."""
    return not (
        ptypes.is_numeric_dtype(series)
        or ptypes.is_bool_dtype(series)
        or ptypes.is_datetime64_any_dtype(series)
    )


def basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica una limpieza básica y devuelve un nuevo DataFrame limpio."""
    cleaned = df.copy()
    rows_before, cols_before = cleaned.shape

    # 1) Recortar espacios y normalizar cadenas vacías a NaN en columnas de texto.
    for col in cleaned.columns:
        if not _is_text_column(cleaned[col]):
            continue
        cleaned[col] = cleaned[col].apply(
            lambda v: v.strip() if isinstance(v, str) else v
        )
        cleaned[col] = cleaned[col].replace("", pd.NA)

    # 2) Eliminar columnas y filas totalmente vacías.
    cleaned = cleaned.dropna(axis=1, how="all")
    cleaned = cleaned.dropna(axis=0, how="all")

    # 3) Eliminar filas duplicadas exactas.
    cleaned = cleaned.drop_duplicates()

    # 4) Reindexar para que las máscaras posicionales del análisis sean válidas.
    cleaned = cleaned.reset_index(drop=True)

    removed_rows = rows_before - cleaned.shape[0]
    removed_cols = cols_before - cleaned.shape[1]
    if removed_rows or removed_cols:
        logger.info(
            "Limpieza básica: -%d fila(s), -%d columna(s)", removed_rows, removed_cols
        )
    return cleaned