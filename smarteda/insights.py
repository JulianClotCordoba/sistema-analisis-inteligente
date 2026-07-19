"""Generación automática de insights en lenguaje natural.

Traduce los resultados numéricos del análisis a frases en español, del estilo
de los "ejemplos de salida esperada" de la propuesta. Es lo que permite que un
usuario sin conocimientos estadísticos entienda los hallazgos.
"""

from __future__ import annotations

from .config import AnalysisConfig
from .logger import get_logger
from .models import (
    AnomalyResult,
    CategoricalDependency,
    ClusteringResult,
    CorrelationResult,
    DatasetProfile,
    Insight,
)

logger = get_logger(__name__)


class InsightGenerator:
    """Construye la lista de insights a partir de los resultados del análisis."""

    def __init__(self, config: AnalysisConfig | None = None) -> None:
        self.config = config or AnalysisConfig()

    def generate(
        self,
        profile: DatasetProfile,
        correlations: dict[str, CorrelationResult],
        dependencies: list[CategoricalDependency],
        clustering: ClusteringResult | None,
        anomalies: list[AnomalyResult],
    ) -> list[Insight]:
        """Genera todos los insights disponibles según los resultados."""
        insights: list[Insight] = []
        insights.extend(self._dataset_insights(profile))
        insights.extend(self._missing_insights(profile))
        insights.extend(self._correlation_insights(correlations))
        insights.extend(self._dependency_insights(dependencies))
        insights.extend(self._clustering_insights(clustering))
        insights.extend(self._anomaly_insights(anomalies))
        logger.info("Insights generados: %d", len(insights))
        return insights

    # --------------------------- generadores ---------------------------

    @staticmethod
    def _dataset_insights(profile: DatasetProfile) -> list[Insight]:
        msg = (
            f"El conjunto de datos contiene {profile.n_rows} registros y "
            f"{profile.n_cols} variables "
            f"({len(profile.numeric_columns)} numéricas, "
            f"{len(profile.categorical_columns)} categóricas, "
            f"{len(profile.datetime_columns)} temporales)."
        )
        return [Insight(category="dataset", message=msg)]

    @staticmethod
    def _missing_insights(profile: DatasetProfile) -> list[Insight]:
        insights: list[Insight] = []
        for col in profile.columns:
            if col.missing_ratio > 0:
                pct = col.missing_ratio * 100
                insights.append(
                    Insight(
                        category="missing",
                        message=(
                            f"La variable '{col.name}' tiene {pct:.1f}% de "
                            f"valores faltantes."
                        ),
                        severity="warning" if col.missing_ratio > 0.2 else "info",
                    )
                )
        return insights

    @staticmethod
    def _correlation_insights(
        correlations: dict[str, CorrelationResult]
    ) -> list[Insight]:
        insights: list[Insight] = []
        seen: set[frozenset[str]] = set()
        for result in correlations.values():
            for rel in result.strong_pairs:
                key = frozenset({rel.var_a, rel.var_b})
                if key in seen:
                    continue
                seen.add(key)
                insights.append(
                    Insight(
                        category="correlation",
                        message=(
                            f"Existe una correlación {rel.strength} {rel.direction} "
                            f"(r={rel.coefficient:.2f}) entre '{rel.var_a}' y "
                            f"'{rel.var_b}'."
                        ),
                    )
                )
        return insights

    @staticmethod
    def _dependency_insights(
        dependencies: list[CategoricalDependency],
    ) -> list[Insight]:
        insights: list[Insight] = []
        for dep in dependencies:
            pct = dep.eta_squared * 100
            insights.append(
                Insight(
                    category="dependency",
                    message=(
                        f"La variable '{dep.categorical}' explica un {pct:.0f}% "
                        f"de la variación en '{dep.numeric}'."
                    ),
                )
            )
        return insights

    @staticmethod
    def _clustering_insights(clustering: ClusteringResult | None) -> list[Insight]:
        if clustering is None or clustering.n_clusters == 0:
            return []
        features = ", ".join(clustering.features_used)
        msg = (
            f"Se detectaron {clustering.n_clusters} agrupaciones principales "
            f"usando {clustering.algorithm.upper()} sobre las variables: {features}."
        )
        insights = [Insight(category="clustering", message=msg)]
        if clustering.silhouette is not None:
            quality = (
                "buena" if clustering.silhouette >= 0.5
                else "moderada" if clustering.silhouette >= 0.25
                else "baja"
            )
            insights.append(
                Insight(
                    category="clustering",
                    message=(
                        f"La calidad de la agrupación es {quality} "
                        f"(silhouette={clustering.silhouette:.2f})."
                    ),
                )
            )
        return insights

    @staticmethod
    def _anomaly_insights(anomalies: list[AnomalyResult]) -> list[Insight]:
        insights: list[Insight] = []
        for result in anomalies:
            pct = result.outlier_ratio * 100
            insights.append(
                Insight(
                    category="anomaly",
                    message=(
                        f"El método {result.method.upper()} detectó un {pct:.1f}% "
                        f"de registros con valores atípicos "
                        f"({result.outlier_count} de {len(result.outlier_mask)})."
                    ),
                    severity="warning" if result.outlier_ratio > 0.1 else "info",
                )
            )
        return insights
