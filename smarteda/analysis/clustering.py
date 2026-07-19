"""Algoritmos de agrupamiento: K-Means y DBSCAN.

Ambos comparten una interfaz común (`ClusteringAlgorithm`) porque son
intercambiables: reciben la misma matriz y producen el mismo tipo de resultado.
Usar una clase base aquí no es un patrón "por lucir": evita duplicar el armado
del resultado y hace explícito el polimorfismo, algo propio del curso de
paradigmas.

Cuando no se fija un parámetro clave (k en K-Means, eps en DBSCAN) se estima
automáticamente, de modo que el sistema sea realmente "inteligente" sin pedirle
nada al usuario.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter

import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

from ..config import AnalysisConfig
from ..logger import get_logger
from ..models import ClusteringResult
from ..preprocessing import Preprocessor

logger = get_logger(__name__)


class ClusteringAlgorithm(ABC):
    """Interfaz común para los algoritmos de clustering."""

    def __init__(self, config: AnalysisConfig) -> None:
        self.config = config

    @abstractmethod
    def fit(self, matrix: np.ndarray, feature_names: list[str]) -> ClusteringResult:
        """Ajusta el algoritmo y devuelve un `ClusteringResult`."""

    def _build_result(
        self,
        algorithm: str,
        labels: np.ndarray,
        matrix: np.ndarray,
        feature_names: list[str],
        params: dict,
    ) -> ClusteringResult:
        """Ensambla el resultado común (tamaños, silhouette, proyección 2D)."""
        unique = [lbl for lbl in set(labels) if lbl != -1]
        n_clusters = len(unique)
        sizes = {int(k): int(v) for k, v in Counter(labels.tolist()).items()}
        silhouette = self._safe_silhouette(matrix, labels, n_clusters)
        projection = Preprocessor.project_2d(matrix, self.config.random_state)
        return ClusteringResult(
            algorithm=algorithm,
            labels=labels,
            n_clusters=n_clusters,
            features_used=feature_names,
            cluster_sizes=sizes,
            silhouette=silhouette,
            params=params,
            projection_2d=projection,
        )

    @staticmethod
    def _safe_silhouette(
        matrix: np.ndarray, labels: np.ndarray, n_clusters: int
    ) -> float | None:
        """Silhouette solo si es matemáticamente válido (2..n-1 clusters)."""
        mask = labels != -1
        valid_labels = labels[mask]
        valid_points = matrix[mask]
        unique = set(valid_labels.tolist())
        if len(unique) < 2 or len(valid_points) <= len(unique):
            return None
        return float(silhouette_score(valid_points, valid_labels))


class KMeansClustering(ClusteringAlgorithm):
    """K-Means con selección automática de k por silhouette si no se fija."""

    def fit(self, matrix: np.ndarray, feature_names: list[str]) -> ClusteringResult:
        n_samples = matrix.shape[0]
        k = self.config.kmeans_k or self._best_k(matrix, n_samples)
        k = max(2, min(k, n_samples - 1))
        model = KMeans(n_clusters=k, random_state=self.config.random_state, n_init=10)
        labels = model.fit_predict(matrix)
        logger.info("K-Means ajustado con k=%d", k)
        return self._build_result(
            "kmeans", labels, matrix, feature_names, {"k": k}
        )

    def _best_k(self, matrix: np.ndarray, n_samples: int) -> int:
        """Elige el k con mejor coeficiente de silhouette dentro del rango."""
        low, high = self.config.kmeans_k_range
        high = min(high, n_samples - 1)
        best_k, best_score = 2, -1.0
        for k in range(max(2, low), high + 1):
            labels = KMeans(
                n_clusters=k, random_state=self.config.random_state, n_init=10
            ).fit_predict(matrix)
            if len(set(labels)) < 2:
                continue
            score = silhouette_score(matrix, labels)
            if score > best_score:
                best_k, best_score = k, score
        logger.info("k óptimo estimado: %d (silhouette=%.3f)", best_k, best_score)
        return best_k


class DBSCANClustering(ClusteringAlgorithm):
    """DBSCAN con estimación automática de eps por la 'rodilla' de k-distancias."""

    def fit(self, matrix: np.ndarray, feature_names: list[str]) -> ClusteringResult:
        min_samples = self.config.dbscan_min_samples
        eps = self.config.dbscan_eps or self._estimate_eps(matrix, min_samples)
        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = model.fit_predict(matrix)
        logger.info(
            "DBSCAN ajustado con eps=%.3f, min_samples=%d", eps, min_samples
        )
        return self._build_result(
            "dbscan",
            labels,
            matrix,
            feature_names,
            {"eps": round(float(eps), 4), "min_samples": min_samples},
        )

    def _estimate_eps(self, matrix: np.ndarray, min_samples: int) -> float:
        """Estima eps con las distancias al k-ésimo vecino más cercano.

        Se ordenan esas distancias y se busca la 'rodilla' (punto de máxima
        curvatura) como la mayor distancia a la recta que une los extremos.
        """
        k = min(min_samples, matrix.shape[0] - 1)
        if k < 1:
            return 0.5
        neighbors = NearestNeighbors(n_neighbors=k).fit(matrix)
        distances, _ = neighbors.kneighbors(matrix)
        k_distances = np.sort(distances[:, -1])
        eps = self._knee_value(k_distances)
        return float(eps) if eps > 0 else 0.5

    @staticmethod
    def _knee_value(values: np.ndarray) -> float:
        """Devuelve el valor en la rodilla de una curva creciente."""
        n = len(values)
        if n < 3:
            return float(values[-1]) if n else 0.5
        x = np.arange(n, dtype=float)
        y = values.astype(float)
        x1, y1, x2, y2 = 0.0, y[0], float(n - 1), y[-1]
        numerator = np.abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1)
        denominator = np.hypot(y2 - y1, x2 - x1)
        if denominator == 0:
            return float(y[-1])
        knee_index = int(np.argmax(numerator / denominator))
        return float(values[knee_index])


_ALGORITHMS: dict[str, type[ClusteringAlgorithm]] = {
    "kmeans": KMeansClustering,
    "dbscan": DBSCANClustering,
}


def run_clustering(
    matrix: np.ndarray, feature_names: list[str], config: AnalysisConfig
) -> ClusteringResult:
    """Ejecuta el algoritmo de clustering indicado en la configuración."""
    name = config.clustering_algorithm.lower()
    algorithm_cls = _ALGORITHMS.get(name)
    if algorithm_cls is None:
        raise ValueError(
            f"Algoritmo de clustering desconocido: '{name}'. "
            f"Opciones: {', '.join(_ALGORITHMS)}."
        )
    return algorithm_cls(config).fit(matrix, feature_names)
