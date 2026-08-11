"""Pruebas de integración de la pantalla de Datos inusuales."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_sample_dataset_anomalies_screen():
    app = AppTest.from_file("app/main.py", default_timeout=25).run()
    assert not app.exception

    _button(app, "Usar datos de ejemplo").click().run(timeout=30)
    _button(app, "05  Datos inusuales").click().run(timeout=30)

    assert not app.exception
    assert [title.value for title in app.title] == [
        "Registros con comportamientos inusuales"
    ]
    assert any(
        metric.label == "Registros marcados" and metric.value == "3"
        for metric in app.metric
    )
    assert any(
        metric.label == "Coincidencia total" and metric.value == "3"
        for metric in app.metric
    )
    assert any(
        metric.label == "Con alguna señal" and metric.value == "18"
        for metric in app.metric
    )
    assert len(app.get("plotly_chart")) == 2

    selector = next(
        radio for radio in app.radio if radio.label == "Método de revisión"
    )
    selector.set_value("isolation_forest").run(timeout=20)

    assert not app.exception
    assert any(
        metric.label == "Registros marcados" and metric.value == "18"
        for metric in app.metric
    )
