"""Preprocesamiento de datos para los algoritmos de Machine Learning.

Los algoritmos basados en distancia (K-Means, DBSCAN) e Isolation Forest
necesitan datos numéricos, sin valores faltantes y en una escala comparable.
Esta capa aísla ese trabajo para que el resto del análisis no lo repita.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from .exceptions import InsufficientDataError
from .logger import get_logger
from .models import DatasetProfile

logger = get_logger(__name__)


class Preprocessor:
    """Prepara una matriz numérica escalada a partir del dataset."""

    def numeric_frame(self, df: pd.DataFrame, profile: DatasetProfile) -> pd.DataFrame:
        """Devuelve solo las columnas numéricas con la mediana imputada.

        Se usa para Z-Score e IQR, que trabajan sobre los valores originales.
        """
        numeric_cols = profile.numeric_columns
        if not numeric_cols:
            raise InsufficientDataError("El dataset no tiene columnas numéricas.")
        frame = df[numeric_cols].copy()
        imputer = SimpleImputer(strategy="median")
        imputed = imputer.fit_transform(frame)
        return pd.DataFrame(imputed, columns=numeric_cols, index=df.index)

    def feature_matrix(
        self, df: pd.DataFrame, profile: DatasetProfile
    ) -> tuple[np.ndarray, list[str]]:
        """Construye la matriz escalada para clustering / Isolation Forest.

        Returns:
            (X escalada, nombres de las columnas usadas).
        """
        numeric = self.numeric_frame(df, profile)
        scaler = StandardScaler()
        matrix = scaler.fit_transform(numeric)
        logger.info(
            "Matriz de características: %d filas x %d columnas numéricas",
            matrix.shape[0],
            matrix.shape[1],
        )
        return matrix, list(numeric.columns)

    @staticmethod
    def project_2d(matrix: np.ndarray, random_state: int = 42) -> np.ndarray | None:
        """Proyecta la matriz a 2 dimensiones con PCA para visualización.

        Devuelve `None` si no hay al menos 2 columnas para proyectar.
        """
        if matrix.shape[1] < 2:
            return None
        pca = PCA(n_components=2, random_state=random_state)
        return pca.fit_transform(matrix)
