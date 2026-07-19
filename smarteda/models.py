"""Modelos de datos (DTOs), enums y contratos de integración.

Estos objetos son la **frontera** entre el backend (Julian) y el resto del
equipo. Jose consume `AnalysisReport` para graficar y Rachel implementa el
contrato `DescriptiveStatsProvider`. Nadie necesita conocer el código interno:
basta con estos tipos.

Se usan dataclasses normales (no `frozen`) porque contienen `DataFrame` y
`ndarray`, que no son hasheables; congelarlas provocaría problemas de
comparación e igualdad sin aportar beneficio real en este proyecto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd


class VariableType(str, Enum):
    """Tipo lógico de una variable/columna detectado automáticamente."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    TEXT = "text"
    UNKNOWN = "unknown"


@dataclass
class ColumnProfile:
    """Perfil de una sola columna."""

    name: str
    dtype: VariableType
    missing_count: int
    missing_ratio: float
    unique_count: int
    sample_values: list[Any]


@dataclass
class DatasetProfile:
    """Perfil del dataset completo con las columnas agrupadas por tipo."""

    n_rows: int
    n_cols: int
    columns: list[ColumnProfile]
    numeric_columns: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)
    datetime_columns: list[str] = field(default_factory=list)
    boolean_columns: list[str] = field(default_factory=list)
    text_columns: list[str] = field(default_factory=list)


@dataclass
class VariableRelationship:
    """Relación fuerte entre dos variables numéricas."""

    var_a: str
    var_b: str
    coefficient: float
    method: str  # "pearson" | "spearman"
    strength: str  # "débil" | "moderada" | "fuerte"
    direction: str  # "positiva" | "negativa"


@dataclass
class CategoricalDependency:
    """Cuánta variación de una variable numérica explica una categórica.

    Se mide con eta cuadrado (proporción de varianza explicada, rango 0-1).
    """

    categorical: str
    numeric: str
    eta_squared: float


@dataclass
class CorrelationResult:
    """Resultado de correlación para un método (Pearson o Spearman)."""

    method: str
    matrix: pd.DataFrame
    strong_pairs: list[VariableRelationship] = field(default_factory=list)


@dataclass
class ClusteringResult:
    """Resultado de un algoritmo de agrupamiento."""

    algorithm: str
    labels: np.ndarray
    n_clusters: int
    features_used: list[str]
    cluster_sizes: dict[int, int]
    silhouette: float | None
    params: dict[str, Any]
    projection_2d: np.ndarray | None  # coords 2D (PCA) para el scatter de Jose


@dataclass
class AnomalyResult:
    """Resultado de un método de detección de anomalías."""

    method: str
    outlier_mask: np.ndarray  # booleano por fila
    outlier_count: int
    outlier_ratio: float
    columns_analyzed: list[str]
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DescriptiveResult:
    """Estadística descriptiva. La llena Rachel mediante su proveedor."""

    statistics: dict[str, dict[str, float]]


@dataclass
class Insight:
    """Hallazgo expresado en lenguaje natural para el usuario final."""

    category: str  # "dataset" | "missing" | "correlation" | "clustering" | "anomaly" | "dependency"
    message: str
    severity: str = "info"  # "info" | "warning"


@dataclass
class AnalysisReport:
    """Contrato principal: todo lo que el backend entrega al frontend."""

    profile: DatasetProfile
    correlations: dict[str, CorrelationResult] = field(default_factory=dict)
    dependencies: list[CategoricalDependency] = field(default_factory=list)
    clustering: ClusteringResult | None = None
    anomalies: list[AnomalyResult] = field(default_factory=list)
    descriptive: DescriptiveResult | None = None
    insights: list[Insight] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class DescriptiveStatsProvider(Protocol):
    """Contrato de integración para Rachel.

    Rachel programa la estadística descriptiva "para apoyar a Julian" (según la
    división de trabajo). Solo debe crear una clase con este método; el motor la
    llamará automáticamente. No necesita tocar ningún otro archivo del backend.

    Ejemplo mínimo de implementación por parte de Rachel::

        class BasicDescriptiveStats:
            def compute(self, df, profile) -> DescriptiveResult:
                stats = {}
                for col in profile.numeric_columns:
                    s = df[col]
                    stats[col] = {
                        "mean": float(s.mean()),
                        "median": float(s.median()),
                        "std": float(s.std()),
                        "min": float(s.min()),
                        "max": float(s.max()),
                    }
                return DescriptiveResult(statistics=stats)

    Y se conecta así::

        engine = AnalysisEngine(descriptive_provider=BasicDescriptiveStats())
    """

    def compute(self, df: pd.DataFrame, profile: DatasetProfile) -> DescriptiveResult:
        ...
