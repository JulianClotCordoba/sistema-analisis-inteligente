"""Detección automática de tipos de variable y perfilado del dataset.

El perfilado inspecciona cada columna y decide si es numérica, categórica,
temporal, booleana o de texto libre. Ese perfil guía después qué análisis se
puede aplicar a cada columna.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api import types as ptypes

from .config import AnalysisConfig
from .logger import get_logger
from .models import ColumnProfile, DatasetProfile, VariableType

logger = get_logger(__name__)

# Palabras que, si son los únicos valores de una columna de texto, la marcan
# como booleana.
_BOOLEAN_TOKENS = {"true", "false", "yes", "no", "si", "sí", "1", "0", "t", "f"}
# Umbral: si la razón (valores únicos / filas) supera esto, se considera texto
# libre en lugar de categórica.
_CATEGORICAL_UNIQUE_RATIO = 0.5


class DataProfiler:
    """Genera el perfil del dataset detectando el tipo de cada columna."""

    def __init__(self, config: AnalysisConfig | None = None) -> None:
        self.config = config or AnalysisConfig()

    def profile(self, df: pd.DataFrame) -> DatasetProfile:
        """Construye el `DatasetProfile` de un DataFrame."""
        columns: list[ColumnProfile] = []
        for name in df.columns:
            series = df[name]
            dtype = self._detect_type(series)
            columns.append(
                ColumnProfile(
                    name=str(name),
                    dtype=dtype,
                    missing_count=int(series.isna().sum()),
                    missing_ratio=float(series.isna().mean()),
                    unique_count=int(series.nunique(dropna=True)),
                    sample_values=self._sample_values(series),
                )
            )

        profile = DatasetProfile(
            n_rows=int(df.shape[0]),
            n_cols=int(df.shape[1]),
            columns=columns,
        )
        self._group_by_type(profile)
        logger.info(
            "Perfil generado: %d numéricas, %d categóricas, %d temporales, %d booleanas",
            len(profile.numeric_columns),
            len(profile.categorical_columns),
            len(profile.datetime_columns),
            len(profile.boolean_columns),
        )
        return profile

    # ----------------------------- helpers -----------------------------

    def _detect_type(self, series: pd.Series) -> VariableType:
        """Decide el tipo lógico de una columna."""
        non_null = series.dropna()
        if non_null.empty:
            return VariableType.UNKNOWN

        if ptypes.is_bool_dtype(series):
            return VariableType.BOOLEAN
        if ptypes.is_datetime64_any_dtype(series):
            return VariableType.DATETIME
        if ptypes.is_numeric_dtype(series):
            return VariableType.NUMERIC

        # Columnas de texto/objeto: intentamos refinar.
        if self._looks_boolean(non_null):
            return VariableType.BOOLEAN
        if self._looks_datetime(non_null):
            return VariableType.DATETIME

        unique_ratio = non_null.nunique() / len(non_null)
        if unique_ratio <= _CATEGORICAL_UNIQUE_RATIO:
            return VariableType.CATEGORICAL
        return VariableType.TEXT

    @staticmethod
    def _looks_boolean(non_null: pd.Series) -> bool:
        """Detecta columnas booleanas escritas como texto (yes/no, si/no...)."""
        values = {str(v).strip().lower() for v in non_null.unique()}
        return len(values) <= 2 and values.issubset(_BOOLEAN_TOKENS)

    @staticmethod
    def _looks_datetime(non_null: pd.Series) -> bool:
        """Detecta fechas escritas como texto, evitando confundir números.

        Solo intenta parsear si los valores contienen separadores típicos de
        fecha/hora, para no clasificar identificadores numéricos como fechas.
        """
        sample = non_null.astype(str).head(50)
        if not sample.str.contains(r"[-/:]").any():
            return False
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        return parsed.notna().mean() >= 0.9

    def _sample_values(self, series: pd.Series) -> list[Any]:
        """Devuelve algunos valores de muestra, en tipos nativos de Python."""
        sample = series.dropna().unique()[: self.config.max_sample_values]
        return [self._to_native(v) for v in sample]

    @staticmethod
    def _to_native(value: Any) -> Any:
        """Convierte tipos de numpy/pandas a tipos nativos serializables."""
        if hasattr(value, "item"):
            try:
                return value.item()
            except (ValueError, AttributeError):
                return str(value)
        return value

    @staticmethod
    def _group_by_type(profile: DatasetProfile) -> None:
        """Rellena las listas agrupadas por tipo dentro del perfil."""
        mapping = {
            VariableType.NUMERIC: profile.numeric_columns,
            VariableType.CATEGORICAL: profile.categorical_columns,
            VariableType.DATETIME: profile.datetime_columns,
            VariableType.BOOLEAN: profile.boolean_columns,
            VariableType.TEXT: profile.text_columns,
        }
        for col in profile.columns:
            target = mapping.get(col.dtype)
            if target is not None:
                target.append(col.name)
