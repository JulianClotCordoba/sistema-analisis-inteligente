"""Correlaciones y relaciones entre variables.

Incluye:
- Matrices de correlación de Pearson y Spearman entre variables numéricas.
- Extracción de pares fuertemente correlacionados.
- Dependencia categórica -> numérica mediante eta cuadrado (cuánta variación de
  una variable numérica explica una categórica).
"""

from __future__ import annotations

import pandas as pd

from ..config import AnalysisConfig
from ..logger import get_logger
from ..models import (
    CategoricalDependency,
    CorrelationResult,
    DatasetProfile,
    VariableRelationship,
)

logger = get_logger(__name__)


class CorrelationAnalyzer:
    """Calcula correlaciones y dependencias a partir del dataset y su perfil."""

    def __init__(self, config: AnalysisConfig | None = None) -> None:
        self.config = config or AnalysisConfig()

    def correlations(
        self, df: pd.DataFrame, profile: DatasetProfile
    ) -> dict[str, CorrelationResult]:
        """Devuelve un `CorrelationResult` por cada método configurado."""
        numeric_cols = profile.numeric_columns
        results: dict[str, CorrelationResult] = {}
        if len(numeric_cols) < 2:
            logger.info("Menos de 2 columnas numéricas: se omiten correlaciones.")
            return results

        numeric_df = df[numeric_cols]
        for method in self.config.correlation_methods:
            matrix = numeric_df.corr(method=method)
            pairs = self._strong_pairs(matrix, method)
            results[method] = CorrelationResult(
                method=method, matrix=matrix, strong_pairs=pairs
            )
            logger.info(
                "Correlación %s: %d par(es) fuerte(s) encontrados", method, len(pairs)
            )
        return results

    def dependencies(
        self, df: pd.DataFrame, profile: DatasetProfile
    ) -> list[CategoricalDependency]:
        """Calcula la dependencia categórica -> numérica (eta cuadrado)."""
        deps: list[CategoricalDependency] = []
        for cat in profile.categorical_columns:
            for num in profile.numeric_columns:
                eta2 = self._eta_squared(df[cat], df[num])
                if eta2 is not None and eta2 >= self.config.dependency_threshold:
                    deps.append(
                        CategoricalDependency(
                            categorical=cat, numeric=num, eta_squared=eta2
                        )
                    )
        deps.sort(key=lambda d: d.eta_squared, reverse=True)
        logger.info("Dependencias categóricas relevantes: %d", len(deps))
        return deps

    # ----------------------------- helpers -----------------------------

    def _strong_pairs(
        self, matrix: pd.DataFrame, method: str
    ) -> list[VariableRelationship]:
        """Extrae los pares con |coeficiente| >= umbral (sin duplicar)."""
        threshold = self.config.strong_correlation_threshold
        pairs: list[VariableRelationship] = []
        cols = list(matrix.columns)
        for i, a in enumerate(cols):
            for b in cols[i + 1 :]:
                coef = matrix.loc[a, b]
                if pd.isna(coef) or abs(coef) < threshold:
                    continue
                pairs.append(
                    VariableRelationship(
                        var_a=a,
                        var_b=b,
                        coefficient=float(coef),
                        method=method,
                        strength=self._strength_label(abs(coef)),
                        direction="positiva" if coef > 0 else "negativa",
                    )
                )
        pairs.sort(key=lambda p: abs(p.coefficient), reverse=True)
        return pairs

    @staticmethod
    def _strength_label(abs_coef: float) -> str:
        if abs_coef >= 0.7:
            return "fuerte"
        if abs_coef >= 0.4:
            return "moderada"
        return "débil"

    @staticmethod
    def _eta_squared(categorical: pd.Series, numeric: pd.Series) -> float | None:
        """Eta cuadrado: proporción de varianza de `numeric` explicada por grupos.

        Devuelve un valor en [0, 1] o `None` si no se puede calcular.
        """
        data = pd.DataFrame({"cat": categorical, "num": numeric}).dropna()
        if data["cat"].nunique() < 2 or len(data) < 3:
            return None

        grand_mean = data["num"].mean()
        ss_total = float(((data["num"] - grand_mean) ** 2).sum())
        if ss_total == 0:
            return None

        ss_between = 0.0
        for _, group in data.groupby("cat", observed=True):
            ss_between += len(group) * (group["num"].mean() - grand_mean) ** 2

        return float(ss_between / ss_total)
