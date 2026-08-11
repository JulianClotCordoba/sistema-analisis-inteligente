"""Pruebas de integración de la pantalla de Segmentos."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_sample_dataset_kmeans_segments_screen():
    app = AppTest.from_file("app/main.py", default_timeout=25).run()
    assert not app.exception

    _button(app, "Usar datos de ejemplo").click().run(timeout=30)
    _button(app, "04  Segmentos").click().run(timeout=30)

    assert not app.exception
    assert [title.value for title in app.title] == [
        "Grupos identificados en los datos"
    ]
    assert any(
        metric.label == "Segmentos encontrados" and metric.value == "3"
        for metric in app.metric
    )
    assert any(
        metric.label == "Calidad de separación" and metric.value == "Buena"
        for metric in app.metric
    )
    assert any(
        metric.label == "Grupo más grande" and metric.value == "118"
        for metric in app.metric
    )
    assert len(app.get("plotly_chart")) == 2


def test_sample_dataset_dbscan_segments_screen():
    app = AppTest.from_file("app/main.py", default_timeout=25).run()
    advanced = next(
        expander for expander in app.expander if expander.label == "Opciones avanzadas"
    )
    method = next(
        radio for radio in advanced.radio if radio.label == "Método de segmentación"
    )
    method.set_value("dbscan")
    _button(app, "Usar datos de ejemplo").click().run(timeout=30)
    _button(app, "04  Segmentos").click().run(timeout=30)

    assert not app.exception
    assert any(
        metric.label == "Segmentos encontrados" and metric.value == "2"
        for metric in app.metric
    )
    assert any(
        metric.label == "Sin segmento" and int(metric.value) > 0
        for metric in app.metric
    )
