"""Detección de anomalías (valores atípicos) por tres métodos.

- Z-Score: marca filas donde alguna variable se aleja más de N desviaciones
  estándar de su media.
- IQR: marca filas fuera del rango [Q1 - k*IQR, Q3 + k*IQR].
- Isolation Forest: modelo de ML que aísla observaciones raras.

Los tres comparten la interfaz `AnomalyDetector` y devuelven un `AnomalyResult`
con una máscara booleana por fila, para que Jose pueda resaltar los atípicos.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ..config import AnalysisConfig
from ..logger import get_logger
from ..models import AnomalyResult

logger = get_logger(__name__)


class AnomalyDetector(ABC):
    """Interfaz común para los detectores de anomalías."""

    name: str = "base"

    def __init__(self, config: AnalysisConfig) -> None:
        self.config = config

    @abstractmethod
    def detect(self, numeric_df: pd.DataFrame) -> AnomalyResult:
        """Recibe un DataFrame numérico (sin NaN) y devuelve el resultado."""

    def _result(
        self, mask: np.ndarray, columns: list[str], details: dict
    ) -> AnomalyResult:
        count = int(mask.sum())
        total = len(mask)
        ratio = float(count / total) if total else 0.0
        logger.info(
            "%s: %d atípicos de %d (%.1f%%)", self.name, count, total, ratio * 100
        )
        return AnomalyResult(
            method=self.name,
            outlier_mask=mask,
            outlier_count=count,
            outlier_ratio=ratio,
            columns_analyzed=columns,
            details=details,
        )


class ZScoreDetector(AnomalyDetector):
    """Marca como atípica una fila si alguna columna supera el umbral de z."""

    name = "zscore"

    def detect(self, numeric_df: pd.DataFrame) -> AnomalyResult:
        threshold = self.config.zscore_threshold
        mask = np.zeros(len(numeric_df), dtype=bool)
        per_column: dict[str, int] = {}
        for col in numeric_df.columns:
            values = numeric_df[col].to_numpy(dtype=float)
            std = values.std()
            if std == 0:
                continue
            z = np.abs((values - values.mean()) / std)
            col_mask = z > threshold
            per_column[col] = int(col_mask.sum())
            mask |= col_mask
        return self._result(
            mask,
            list(numeric_df.columns),
            {"threshold": threshold, "outliers_per_column": per_column},
        )


class IQRDetector(AnomalyDetector):
    """Marca como atípica una fila fuera del rango intercuartílico ampliado."""

    name = "iqr"

    def detect(self, numeric_df: pd.DataFrame) -> AnomalyResult:
        multiplier = self.config.iqr_multiplier
        mask = np.zeros(len(numeric_df), dtype=bool)
        bounds: dict[str, dict[str, float]] = {}
        for col in numeric_df.columns:
            values = numeric_df[col]
            q1, q3 = values.quantile(0.25), values.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - multiplier * iqr, q3 + multiplier * iqr
            bounds[col] = {"lower": float(lower), "upper": float(upper)}
            mask |= ((values < lower) | (values > upper)).to_numpy()
        return self._result(
            mask,
            list(numeric_df.columns),
            {"multiplier": multiplier, "bounds": bounds},
        )


class IsolationForestDetector(AnomalyDetector):
    """Detección multivariada de atípicos con Isolation Forest."""

    name = "isolation_forest"

    def detect(self, numeric_df: pd.DataFrame) -> AnomalyResult:
        matrix = StandardScaler().fit_transform(numeric_df)
        model = IsolationForest(
            contamination=self.config.isolation_contamination,
            random_state=self.config.random_state,
        )
        predictions = model.fit_predict(matrix)  # -1 = atípico, 1 = normal
        mask = predictions == -1
        return self._result(
            mask,
            list(numeric_df.columns),
            {"contamination": self.config.isolation_contamination},
        )


_DETECTORS: dict[str, type[AnomalyDetector]] = {
    "zscore": ZScoreDetector,
    "iqr": IQRDetector,
    "isolation_forest": IsolationForestDetector,
}


def run_anomaly_detection(
    numeric_df: pd.DataFrame, config: AnalysisConfig
) -> list[AnomalyResult]:
    """Ejecuta todos los métodos de anomalías indicados en la configuración."""
    results: list[AnomalyResult] = []
    for method in config.anomaly_methods:
        detector_cls = _DETECTORS.get(method.lower())
        if detector_cls is None:
            logger.warning("Método de anomalías desconocido, se omite: %s", method)
            continue
        results.append(detector_cls(config).detect(numeric_df))
    return results
