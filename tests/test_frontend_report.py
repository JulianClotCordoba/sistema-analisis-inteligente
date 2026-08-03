"""Pruebas de integración de la pantalla y del PDF de Reporte."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

from app.reporting import generate_pdf_report
from smarteda import AnalysisEngine


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_sample_dataset_report_screen():
    app = AppTest.from_file("app/main.py", default_timeout=25).run()
    assert not app.exception

    _button(app, "Usar datos de ejemplo").click().run(timeout=30)
    _button(app, "06  Reporte").click().run(timeout=30)

    assert not app.exception
    assert [title.value for title in app.title] == [
        "Tu reporte está listo para compartir"
    ]
    assert any(
        metric.label == "Registros" and metric.value == "183"
        for metric in app.metric
    )
    assert any(
        button.label == "Descargar reporte PDF" for button in app.download_button
    )


def test_generated_pdf_contains_complete_sections():
    report = AnalysisEngine().analyze("data/samples/clientes.csv")
    pdf_bytes = generate_pdf_report(report, "clientes.csv")

    assert pdf_bytes.startswith(b"%PDF")
    reader = PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) >= 3
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    for expected in (
        "SMARTEDA",
        "clientes.csv",
        "Resumen ejecutivo",
        "Relaciones entre variables",
        "Segmentos",
        "Datos inusuales",
        "Próximos pasos recomendados",
        "Alcance y limitaciones",
    ):
        assert expected in text
