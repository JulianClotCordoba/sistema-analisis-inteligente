"""Pruebas de la limpieza básica del dataset."""

from __future__ import annotations

import numpy as np
import pandas as pd

from smarteda.cleaning import basic_clean


def test_strips_whitespace_and_empties_to_nan():
    df = pd.DataFrame(
        {
            "texto": ["  hola ", "", "chao"],
            "id": [1, 2, 3],  # evita que la fila vacía sea totalmente nula
        }
    )
    cleaned = basic_clean(df)
    assert cleaned.loc[0, "texto"] == "hola"
    assert pd.isna(cleaned.loc[1, "texto"])
    assert cleaned.shape[0] == 3


def test_drops_empty_rows_and_columns():
    df = pd.DataFrame(
        {
            "a": [1, np.nan, 3],
            "vacia": [np.nan, np.nan, np.nan],
        }
    )
    df.loc[1] = [np.nan, np.nan]  # fila totalmente vacía
    cleaned = basic_clean(df)
    assert "vacia" not in cleaned.columns  # columna vacía eliminada
    assert cleaned.shape[0] == 2  # fila vacía eliminada


def test_drops_duplicate_rows():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    cleaned = basic_clean(df)
    assert cleaned.shape[0] == 2


def test_can_be_disabled_via_config(tmp_path):
    from smarteda import AnalysisConfig, AnalysisEngine

    df = pd.DataFrame({"a": [1, 1, 2, 3], "b": [1.0, 1.0, 2.0, 3.0]})
    path = tmp_path / "dup.csv"
    df.to_csv(path, index=False)

    # Con limpieza: se elimina la fila duplicada (4 -> 3).
    report_on = AnalysisEngine().analyze(path)
    assert report_on.profile.n_rows == 3

    # Sin limpieza: se conservan las 4 filas.
    config = AnalysisConfig(enable_basic_cleaning=False)
    report_off = AnalysisEngine(config).analyze(path)
    assert report_off.profile.n_rows == 4