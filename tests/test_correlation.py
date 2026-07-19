"""Pruebas de correlaciones y dependencias entre variables."""

from __future__ import annotations

import pandas as pd

from smarteda.analysis.correlation import CorrelationAnalyzer
from smarteda.profiling import DataProfiler


def test_detects_strong_positive_correlation():
    df = pd.DataFrame({"a": range(20), "b": [x * 2 for x in range(20)]})
    profile = DataProfiler().profile(df)
    results = CorrelationAnalyzer().correlations(df, profile)

    assert "pearson" in results
    pearson = results["pearson"]
    assert pearson.matrix.shape == (2, 2)
    assert len(pearson.strong_pairs) == 1
    rel = pearson.strong_pairs[0]
    assert rel.direction == "positiva"
    assert rel.coefficient > 0.99


def test_no_correlation_without_two_numeric_columns():
    df = pd.DataFrame({"a": range(10), "cat": ["x"] * 10})
    profile = DataProfiler().profile(df)
    results = CorrelationAnalyzer().correlations(df, profile)
    assert results == {}


def test_categorical_dependency_detected():
    # 'grupo' determina completamente el valor -> eta cuadrado alto.
    df = pd.DataFrame(
        {
            "grupo": ["a"] * 10 + ["b"] * 10,
            "valor": [1.0] * 10 + [100.0] * 10,
        }
    )
    profile = DataProfiler().profile(df)
    deps = CorrelationAnalyzer().dependencies(df, profile)
    assert len(deps) == 1
    assert deps[0].eta_squared > 0.9
