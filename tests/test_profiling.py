"""Pruebas de la detección automática de tipos y el perfilado."""

from __future__ import annotations

from smarteda.profiling import DataProfiler
from smarteda.models import VariableType


def _type_of(profile, name):
    return next(c.dtype for c in profile.columns if c.name == name)


def test_detects_variable_types(mixed_df):
    profile = DataProfiler().profile(mixed_df)
    assert _type_of(profile, "edad") == VariableType.NUMERIC
    assert _type_of(profile, "ingreso") == VariableType.NUMERIC
    assert _type_of(profile, "region") == VariableType.CATEGORICAL
    assert _type_of(profile, "activo") == VariableType.BOOLEAN
    assert _type_of(profile, "fecha") == VariableType.DATETIME


def test_groups_and_counts(mixed_df):
    profile = DataProfiler().profile(mixed_df)
    assert profile.n_rows == 6
    assert profile.n_cols == 5
    assert "edad" in profile.numeric_columns
    assert "region" in profile.categorical_columns


def test_missing_values_counted(mixed_df):
    profile = DataProfiler().profile(mixed_df)
    ingreso = next(c for c in profile.columns if c.name == "ingreso")
    assert ingreso.missing_count == 1
    assert 0 < ingreso.missing_ratio < 1
