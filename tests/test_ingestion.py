"""Pruebas de la carga y validación de archivos."""

from __future__ import annotations

import pandas as pd
import pytest

from smarteda.exceptions import (
    EmptyDatasetError,
    FileValidationError,
    UnsupportedFileFormatError,
)
from smarteda.ingestion import load_dataset


def test_load_csv(tmp_path, mixed_df):
    path = tmp_path / "datos.csv"
    mixed_df.to_csv(path, index=False)
    loaded = load_dataset(path)
    assert loaded.shape == mixed_df.shape
    assert list(loaded.columns) == list(mixed_df.columns)


def test_load_excel(tmp_path, mixed_df):
    path = tmp_path / "datos.xlsx"
    mixed_df.to_excel(path, index=False)
    loaded = load_dataset(path)
    assert loaded.shape == mixed_df.shape


def test_load_legacy_excel_uses_excel_reader(monkeypatch, mixed_df):
    """La extensión .xls sigue la misma ruta de lectura que .xlsx."""
    class UploadedFile:
        name = "datos.xls"

    captured = {}

    def fake_read_excel(source, **kwargs):
        captured["source"] = source
        return mixed_df

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    source = UploadedFile()
    loaded = load_dataset(source)

    assert loaded.equals(mixed_df)
    assert captured["source"] is source


def test_missing_file_raises():
    with pytest.raises(FileValidationError):
        load_dataset("no_existe.csv")


def test_unsupported_extension_raises(tmp_path):
    path = tmp_path / "datos.json"
    path.write_text("{}")
    with pytest.raises(UnsupportedFileFormatError):
        load_dataset(path)


def test_empty_file_raises(tmp_path):
    path = tmp_path / "vacio.csv"
    pd.DataFrame().to_csv(path, index=False)
    with pytest.raises((EmptyDatasetError, FileValidationError)):
        load_dataset(path)
