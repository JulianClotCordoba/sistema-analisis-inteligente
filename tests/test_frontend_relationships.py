"""Pruebas de integración de la pantalla de Relaciones."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_sample_dataset_relationships_screen():
    app = AppTest.from_file("app/main.py", default_timeout=25).run()
    assert not app.exception

    _button(app, "Usar datos de ejemplo").click().run(timeout=30)
    assert not app.exception

    _button(app, "03  Relaciones").click().run(timeout=30)
    assert not app.exception
    assert [title.value for title in app.title] == ["Relaciones entre variables"]
    assert any(
        metric.label == "Variables comparadas" and metric.value == "3"
        for metric in app.metric
    )
    assert any(
        metric.label == "Relaciones fuertes" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        metric.label == "Diferencias por categoría" and metric.value == "3"
        for metric in app.metric
    )
    assert not app.exception

    method_selector = next(
        radio for radio in app.radio if radio.label == "Método de lectura"
    )
    method_selector.set_value("spearman").run(timeout=20)

    assert not app.exception
    assert any(
        metric.label == "Relaciones fuertes" and metric.value == "3"
        for metric in app.metric
    )
