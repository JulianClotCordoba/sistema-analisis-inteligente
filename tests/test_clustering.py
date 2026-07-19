"""Pruebas de los algoritmos de clustering."""

from __future__ import annotations

from smarteda.config import AnalysisConfig
from smarteda.analysis.clustering import run_clustering
from smarteda.preprocessing import Preprocessor
from smarteda.profiling import DataProfiler


def _matrix(df):
    profile = DataProfiler().profile(df)
    return Preprocessor().feature_matrix(df, profile)


def test_kmeans_finds_three_groups(clustered_df):
    matrix, features = _matrix(clustered_df)
    config = AnalysisConfig(clustering_algorithm="kmeans")
    result = run_clustering(matrix, features, config)
    assert result.algorithm == "kmeans"
    assert result.n_clusters == 3
    assert result.silhouette is not None and result.silhouette > 0.5


def test_kmeans_is_deterministic(clustered_df):
    matrix, features = _matrix(clustered_df)
    config = AnalysisConfig()
    first = run_clustering(matrix, features, config).labels
    second = run_clustering(matrix, features, config).labels
    assert (first == second).all()


def test_dbscan_runs_and_projects(clustered_df):
    matrix, features = _matrix(clustered_df)
    config = AnalysisConfig(clustering_algorithm="dbscan", dbscan_min_samples=5)
    result = run_clustering(matrix, features, config)
    assert result.algorithm == "dbscan"
    assert result.projection_2d is not None
    assert result.projection_2d.shape[1] == 2
