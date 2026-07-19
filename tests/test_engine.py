"""Pruebas de integración del motor completo."""

from __future__ import annotations

import pandas as pd

from smarteda import AnalysisEngine, AnalysisConfig
from smarteda.models import DescriptiveResult


def test_full_report_on_sample(tmp_path, clustered_df):
    # Añadimos una categórica para ejercitar dependencias e insights.
    df = clustered_df.copy()
    df["grupo"] = (["a"] * 30) + (["b"] * 30) + (["c"] * 30)
    path = tmp_path / "datos.csv"
    df.to_csv(path, index=False)

    report = AnalysisEngine().analyze(path)

    assert report.profile.n_rows == 90
    assert report.clustering is not None
    assert len(report.anomalies) == 3
    assert len(report.insights) > 0
    assert report.metadata["n_cols"] == 3
    assert report.descriptive is None  # sin proveedor de Rachel


def test_engine_uses_descriptive_provider(tmp_path, clustered_df):
    class DummyProvider:
        def compute(self, df, profile):
            return DescriptiveResult(statistics={"x": {"mean": float(df["x"].mean())}})

    path = tmp_path / "datos.csv"
    clustered_df.to_csv(path, index=False)

    report = AnalysisEngine(descriptive_provider=DummyProvider()).analyze(path)
    assert report.descriptive is not None
    assert "x" in report.descriptive.statistics


def test_analyze_many_returns_report_per_file(tmp_path, clustered_df):
    path_a = tmp_path / "a.csv"
    path_b = tmp_path / "b.csv"
    clustered_df.to_csv(path_a, index=False)
    clustered_df.to_csv(path_b, index=False)

    reports = AnalysisEngine().analyze_many([path_a, path_b])
    assert len(reports) == 2
    for report in reports.values():
        assert report.clustering is not None


def test_analyze_many_skips_invalid_file(tmp_path, clustered_df):
    good = tmp_path / "ok.csv"
    clustered_df.to_csv(good, index=False)
    reports = AnalysisEngine().analyze_many([good, "no_existe.csv"])
    # El archivo inválido se omite sin tumbar el resto.
    assert len(reports) == 1


def test_dbscan_config(tmp_path, clustered_df):
    path = tmp_path / "datos.csv"
    clustered_df.to_csv(path, index=False)
    config = AnalysisConfig(clustering_algorithm="dbscan")
    report = AnalysisEngine(config).analyze(path)
    assert report.clustering is not None
    assert report.clustering.algorithm == "dbscan"
