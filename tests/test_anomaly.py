"""Pruebas de los detectores de anomalías."""

from __future__ import annotations

from smarteda.config import AnalysisConfig
from smarteda.analysis.anomaly import run_anomaly_detection


def test_all_methods_detect_injected_outlier(outlier_df):
    config = AnalysisConfig()
    results = run_anomaly_detection(outlier_df, config)
    assert {r.method for r in results} == {"zscore", "iqr", "isolation_forest"}
    # El último registro es el atípico inyectado (valor = 10_000).
    for result in results:
        assert result.outlier_mask[-1], f"{result.method} no detectó el atípico"
        assert result.outlier_count >= 1


def test_zscore_ratio_is_reasonable(outlier_df):
    config = AnalysisConfig(anomaly_methods=["zscore"])
    result = run_anomaly_detection(outlier_df, config)[0]
    assert 0 < result.outlier_ratio < 0.5


def test_unknown_method_is_skipped(outlier_df):
    config = AnalysisConfig(anomaly_methods=["zscore", "inexistente"])
    results = run_anomaly_detection(outlier_df, config)
    assert len(results) == 1
    assert results[0].method == "zscore"
