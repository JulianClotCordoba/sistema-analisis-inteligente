"""Fixtures compartidas por las pruebas."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def mixed_df() -> pd.DataFrame:
    """DataFrame con tipos variados y valores faltantes."""
    return pd.DataFrame(
        {
            "edad": [20, 35, 40, 25, 60, 33],
            "ingreso": [1000.0, 2000.0, np.nan, 1500.0, 5000.0, 1800.0],
            "region": ["Norte", "Sur", "Norte", "Sur", "Centro", "Norte"],
            "activo": ["si", "no", "si", "no", "si", "no"],
            "fecha": ["2020-01-01", "2020-02-01", "2020-03-01",
                      "2020-04-01", "2020-05-01", "2020-06-01"],
        }
    )


@pytest.fixture
def clustered_df() -> pd.DataFrame:
    """DataFrame con tres grupos numéricos bien separados."""
    rng = np.random.default_rng(0)
    groups = []
    for cx, cy in [(0, 0), (20, 20), (40, 0)]:
        groups.append(
            pd.DataFrame(
                {
                    "x": rng.normal(cx, 1.0, 30),
                    "y": rng.normal(cy, 1.0, 30),
                }
            )
        )
    return pd.concat(groups, ignore_index=True)


@pytest.fixture
def outlier_df() -> pd.DataFrame:
    """DataFrame numérico con un valor atípico evidente."""
    values = list(range(1, 31)) + [10_000]  # el último es el atípico
    return pd.DataFrame({"valor": values, "otro": list(range(31))})
