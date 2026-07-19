"""Configuración del análisis.

`AnalysisConfig` reúne todos los parámetros ajustables en un solo objeto con
valores por defecto sensatos. Así el sistema funciona sin configurar nada
(`AnalysisEngine().analyze("datos.csv")`), pero Jose o Rachel pueden ajustarlo
si lo necesitan, sin tocar el código interno.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AnalysisConfig:
    """Parámetros que controlan qué se ejecuta y cómo."""

    # --- Correlaciones ---
    correlation_methods: list[str] = field(default_factory=lambda: ["pearson", "spearman"])
    strong_correlation_threshold: float = 0.7  # |r| a partir del cual se reporta

    # Dependencia categórica -> numérica (eta cuadrado)
    dependency_threshold: float = 0.14  # 0.14 ~ efecto "grande" según Cohen

    # --- Clustering ---
    clustering_algorithm: str = "kmeans"  # "kmeans" | "dbscan"
    kmeans_k: int | None = None  # None => se elige automáticamente por silhouette
    kmeans_k_range: tuple[int, int] = (2, 10)
    dbscan_eps: float | None = None  # None => se estima por la "rodilla" de k-distancias
    dbscan_min_samples: int = 5

    # --- Detección de anomalías ---
    anomaly_methods: list[str] = field(
        default_factory=lambda: ["zscore", "iqr", "isolation_forest"]
    )
    zscore_threshold: float = 3.0
    iqr_multiplier: float = 1.5
    isolation_contamination: float | str = "auto"

    # --- General ---
    random_state: int = 42  # reproducibilidad en toda corrida
    enable_basic_cleaning: bool = True  # limpieza básica automática tras la carga
    max_sample_values: int = 5  # valores de muestra por columna en el perfil
    min_rows_for_ml: int = 5  # mínimo de filas para intentar clustering/IsolationForest
