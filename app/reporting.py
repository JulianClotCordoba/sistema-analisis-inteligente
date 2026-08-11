"""Vista ejecutiva y generación del reporte PDF descargable de SmartEDA."""

from __future__ import annotations

import html
from datetime import datetime
from io import BytesIO
from pathlib import Path
from textwrap import dedent
from typing import Any
from xml.sax.saxutils import escape as xml_escape

import numpy as np
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PDF_DARK = colors.HexColor("#11130F")
PDF_INK = colors.HexColor("#25261F")
PDF_MUTED = colors.HexColor("#696A62")
PDF_GOLD = colors.HexColor("#D79E28")
PDF_GOLD_LIGHT = colors.HexColor("#F0D28A")
PDF_SURFACE = colors.HexColor("#F4F0E6")
PDF_LINE = colors.HexColor("#D8D2C4")
PDF_WARNING = colors.HexColor("#C86F32")


def _humanize(value: Any) -> str:
    return str(value).replace("_", " ").strip().capitalize()


def _algorithm_name(value: str) -> str:
    return "K-Means" if value.lower() == "kmeans" else "DBSCAN"


def _method_name(value: str) -> str:
    return {
        "zscore": "Z-Score",
        "iqr": "IQR",
        "isolation_forest": "Isolation Forest",
    }.get(value, _humanize(value))


def _generated_at(report: Any) -> str:
    raw = report.metadata.get("generated_at")
    if not raw:
        return "Fecha no disponible"
    try:
        value = datetime.fromisoformat(str(raw))
        return value.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(raw)


def _missing_total(report: Any) -> int:
    return sum(column.missing_count for column in report.profile.columns)


def _strong_relationships(report: Any) -> list[Any]:
    relationships: list[Any] = []
    seen: set[frozenset[str]] = set()
    for method in ("pearson", "spearman"):
        result = report.correlations.get(method)
        if result is None:
            continue
        for relationship in result.strong_pairs:
            key = frozenset((relationship.var_a, relationship.var_b))
            if key not in seen:
                relationships.append(relationship)
                seen.add(key)
    return sorted(relationships, key=lambda item: abs(item.coefficient), reverse=True)


def _consensus_count(report: Any) -> int:
    if not report.anomalies:
        return 0
    masks = [np.asarray(result.outlier_mask, dtype=bool) for result in report.anomalies]
    return int(np.logical_and.reduce(masks).sum())


def _any_anomaly_count(report: Any) -> int:
    if not report.anomalies:
        return 0
    masks = [np.asarray(result.outlier_mask, dtype=bool) for result in report.anomalies]
    return int(np.logical_or.reduce(masks).sum())


def _cluster_quality(score: float | None) -> str:
    if score is None:
        return "No evaluable"
    if score >= 0.5:
        return "Buena"
    if score >= 0.25:
        return "Moderada"
    return "Baja"


def build_executive_summary(report: Any) -> str:
    """Crea una lectura corta usando únicamente resultados del contrato."""
    profile = report.profile
    parts = [
        f"El análisis incluye {profile.n_rows:,} registros y {profile.n_cols} variables."
    ]
    relationships = _strong_relationships(report)
    if relationships:
        top = relationships[0]
        direction = "en el mismo sentido" if top.coefficient >= 0 else "en sentido contrario"
        parts.append(
            f"La relación numérica más marcada aparece entre {_humanize(top.var_a).lower()} "
            f"y {_humanize(top.var_b).lower()} ({top.coefficient:+.2f}), que tienden a "
            f"moverse {direction}."
        )
    if report.clustering is not None and report.clustering.n_clusters:
        clustering = report.clustering
        parts.append(
            f"Se encontraron {clustering.n_clusters} segmentos mediante "
            f"{_algorithm_name(clustering.algorithm)}, con separación "
            f"{_cluster_quality(clustering.silhouette).lower()}."
        )
    consensus = _consensus_count(report)
    any_count = _any_anomaly_count(report)
    if report.anomalies:
        parts.append(
            f"{any_count} registros recibieron al menos una señal de comportamiento "
            f"inusual y {consensus} coincidieron en todos los métodos."
        )
    return " ".join(parts)


def build_recommendations(report: Any) -> list[str]:
    """Transforma los resultados en próximos pasos prudentes y verificables."""
    recommendations: list[str] = []
    relationships = _strong_relationships(report)
    if relationships:
        top = relationships[0]
        recommendations.append(
            f"Revisar {_humanize(top.var_a).lower()} junto con "
            f"{_humanize(top.var_b).lower()} en futuras comparaciones, sin asumir causalidad."
        )
    if report.dependencies:
        dependency = max(report.dependencies, key=lambda item: item.eta_squared)
        recommendations.append(
            f"Comparar {_humanize(dependency.numeric).lower()} por las categorías de "
            f"{_humanize(dependency.categorical).lower()} antes de usar un promedio general."
        )
    if report.clustering is not None and report.clustering.n_clusters:
        recommendations.append(
            "Comparar los indicadores de cada segmento para identificar sus "
            "diferencias principales."
        )
    consensus = _consensus_count(report)
    if consensus:
        recommendations.append(
            f"Revisar primero los {consensus} registros señalados por todos los "
            "detectores y confirmar su contexto antes de corregirlos o eliminarlos."
        )
    recommendations.append(
        "Interpretar los resultados según el contexto del conjunto de datos y "
        "documentar las conclusiones obtenidas."
    )
    return recommendations[:5]


def _pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SmartTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=31,
            textColor=PDF_INK,
            alignment=TA_LEFT,
            spaceAfter=9,
        ),
        "subtitle": ParagraphStyle(
            "SmartSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=16,
            textColor=PDF_MUTED,
            spaceAfter=16,
        ),
        "h1": ParagraphStyle(
            "SmartH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=PDF_INK,
            spaceBefore=4,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "SmartH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=PDF_INK,
            spaceBefore=5,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "SmartBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=14,
            textColor=PDF_INK,
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "SmartSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=11,
            textColor=PDF_MUTED,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10,
            textColor=colors.white,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            textColor=PDF_INK,
            alignment=TA_CENTER,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.3,
            leading=9,
            textColor=PDF_MUTED,
            alignment=TA_CENTER,
        ),
        "callout": ParagraphStyle(
            "SmartCallout",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=PDF_INK,
        ),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(xml_escape(str(text)).replace("\n", "<br/>"), style)


def _section_title(text: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [Spacer(1, 4), _p(f"/ {text}", styles["h1"])]


def _metric_table(report: Any, styles: dict[str, ParagraphStyle]) -> Table:
    clustering = report.clustering
    metrics = [
        (f"{report.profile.n_rows:,}", "REGISTROS"),
        (str(report.profile.n_cols), "VARIABLES"),
        (str(len(report.insights)), "HALLAZGOS"),
        (
            str(clustering.n_clusters) if clustering is not None else "-",
            "SEGMENTOS",
        ),
    ]
    cells = [
        [
            _p(value, styles["metric_value"]),
            Spacer(1, 2),
            _p(label, styles["metric_label"]),
        ]
        for value, label in metrics
    ]
    table = Table([cells], colWidths=[42 * mm] * 4, rowHeights=[23 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PDF_SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.7, PDF_LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, PDF_LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _data_table(
    rows: list[list[Any]],
    widths: list[float],
    styles: dict[str, ParagraphStyle],
    header: bool = True,
) -> Table:
    rendered = []
    for index, row in enumerate(rows):
        cell_style = styles["table_header"] if header and index == 0 else styles["small"]
        rendered.append([_p(cell, cell_style) for cell in row])
    table = Table(rendered, colWidths=widths, repeatRows=1 if header else 0)
    rules = [
        ("GRID", (0, 0), (-1, -1), 0.45, PDF_LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        rules.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PDF_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    for row_index in range(1 if header else 0, len(rows)):
        if row_index % 2 == 0:
            rules.append(("BACKGROUND", (0, row_index), (-1, row_index), PDF_SURFACE))
    table.setStyle(TableStyle(rules))
    return table


def _draw_page_frame(canvas: Any, doc: Any, filename: str) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(PDF_DARK)
    canvas.rect(0, height - 30, width, 30, fill=1, stroke=0)
    canvas.setFillColor(PDF_GOLD_LIGHT)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(doc.leftMargin, height - 19, "PROYECTO UNIVERSITARIO")
    canvas.setFillColor(colors.HexColor("#D5D2C8"))
    canvas.setFont("Helvetica", 7.5)
    safe_name = Path(filename).name[:58]
    canvas.drawRightString(width - doc.rightMargin, height - 19, safe_name)
    canvas.setStrokeColor(PDF_LINE)
    canvas.line(doc.leftMargin, 25, width - doc.rightMargin, 25)
    canvas.setFillColor(PDF_MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(doc.leftMargin, 14, "Análisis exploratorio de datos")
    canvas.drawRightString(width - doc.rightMargin, 14, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def generate_pdf_report(report: Any, filename: str | None = None) -> bytes:
    """Genera un PDF ejecutivo completamente en memoria para Streamlit."""
    safe_filename = Path(str(filename or report.metadata.get("source", "dataset"))).name
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=15 * mm,
        title=f"Reporte de análisis - {safe_filename}",
        author="Proyecto universitario",
        subject="Reporte de análisis exploratorio",
    )
    styles = _pdf_styles()
    story: list[Any] = []

    story.extend(
        [
            Spacer(1, 8),
            _p("REPORTE DE DATOS", styles["small"]),
            _p("Análisis exploratorio", styles["title"]),
            _p(
                f"Archivo: {safe_filename}\nGenerado: {_generated_at(report)}\n"
                f"Procesamiento: {report.metadata.get('elapsed_seconds', 0):.3f} segundos",
                styles["subtitle"],
            ),
            _metric_table(report, styles),
            Spacer(1, 15),
        ]
    )
    story.extend(_section_title("Resumen de resultados", styles))
    summary_box = Table(
        [[_p(build_executive_summary(report), styles["callout"])]],
        colWidths=[170 * mm],
    )
    summary_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PDF_SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.8, PDF_GOLD),
                ("LINEBEFORE", (0, 0), (0, -1), 3, PDF_GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
            ]
        )
    )
    story.extend([summary_box, Spacer(1, 12)])
    story.extend(_section_title("Resultados principales", styles))
    for insight in report.insights[:7]:
        story.append(_p(f"- {insight.message}", styles["body"]))

    story.append(PageBreak())
    story.extend(_section_title("Relaciones entre variables", styles))
    relationships = _strong_relationships(report)
    if relationships:
        relationship_rows = [["Variables", "Método", "Índice", "Lectura"]]
        for relationship in relationships[:5]:
            relationship_rows.append(
                [
                    f"{_humanize(relationship.var_a)} / {_humanize(relationship.var_b)}",
                    _humanize(relationship.method),
                    f"{relationship.coefficient:+.2f}",
                    "Mismo sentido" if relationship.coefficient >= 0 else "Sentido contrario",
                ]
            )
        story.append(
            _data_table(
                relationship_rows,
                [65 * mm, 30 * mm, 25 * mm, 50 * mm],
                styles,
            )
        )
    else:
        story.append(_p("No se encontraron relaciones numéricas fuertes.", styles["body"]))

    if report.dependencies:
        story.extend([Spacer(1, 10), _p("Diferencias por categoría", styles["h2"])])
        dependency_rows = [["Categoría", "Variable numérica", "Asociación"]]
        for dependency in sorted(
            report.dependencies, key=lambda item: item.eta_squared, reverse=True
        )[:5]:
            dependency_rows.append(
                [
                    _humanize(dependency.categorical),
                    _humanize(dependency.numeric),
                    f"{dependency.eta_squared * 100:.0f}%",
                ]
            )
        story.append(
            _data_table(dependency_rows, [60 * mm, 70 * mm, 40 * mm], styles)
        )

    story.extend(_section_title("Segmentos", styles))
    clustering = report.clustering
    if clustering is not None and clustering.n_clusters:
        story.append(
            _p(
                f"{_algorithm_name(clustering.algorithm)} encontró "
                f"{clustering.n_clusters} segmentos usando "
                f"{', '.join(_humanize(item) for item in clustering.features_used)}. "
                f"La calidad de separación es {_cluster_quality(clustering.silhouette).lower()}"
                + (
                    f" (silhouette {clustering.silhouette:.2f})."
                    if clustering.silhouette is not None
                    else "."
                ),
                styles["body"],
            )
        )
        cluster_rows = [["Grupo", "Registros", "Porcentaje"]]
        total = len(clustering.labels)
        for label, count in sorted(clustering.cluster_sizes.items()):
            name = "Sin segmento" if int(label) == -1 else f"Segmento {int(label) + 1}"
            cluster_rows.append([name, f"{count:,}", f"{count / total * 100:.1f}%"])
        story.append(_data_table(cluster_rows, [75 * mm, 45 * mm, 50 * mm], styles))
        story.append(
            _p(
                "Los grupos representan similitud matemática. Deben contrastarse "
                "con el contexto antes de recibir nombres comerciales.",
                styles["small"],
            )
        )
    else:
        story.append(_p("No fue posible formar segmentos estables.", styles["body"]))

    story.append(PageBreak())
    story.extend(_section_title("Datos inusuales", styles))
    if report.anomalies:
        anomaly_rows = [["Método", "Registros", "Porcentaje", "Qué busca"]]
        descriptions = {
            "zscore": "Extremos frente al promedio",
            "iqr": "Valores fuera del rango central",
            "isolation_forest": "Combinaciones poco frecuentes",
        }
        for result in report.anomalies:
            anomaly_rows.append(
                [
                    _method_name(result.method),
                    str(result.outlier_count),
                    f"{result.outlier_ratio * 100:.1f}%",
                    descriptions.get(result.method, "Señales inusuales"),
                ]
            )
        story.append(
            _data_table(
                anomaly_rows,
                [38 * mm, 28 * mm, 29 * mm, 75 * mm],
                styles,
            )
        )
        story.append(
            _p(
                f"Coincidencia de todos los métodos: {_consensus_count(report)} registros. "
                f"Con al menos una señal: {_any_anomaly_count(report)} registros.",
                styles["body"],
            )
        )
    else:
        story.append(_p("No se generaron resultados de anomalías.", styles["body"]))

    story.extend(_section_title("Puntos para revisar", styles))
    for index, recommendation in enumerate(build_recommendations(report), start=1):
        story.append(_p(f"{index}. {recommendation}", styles["body"]))

    story.extend(_section_title("Alcance y limitaciones", styles))
    limitations = [
        "Una relación estadística no demuestra que una variable cause la otra.",
        "Un segmento representa similitud numérica, no una categoría comercial definitiva.",
        "Un registro inusual puede ser válido y no debe eliminarse automáticamente.",
        "Los resultados dependen de la calidad y representatividad del archivo analizado.",
        "La interpretación de los resultados requiere considerar el contexto de los datos.",
    ]
    for limitation in limitations:
        story.append(_p(f"- {limitation}", styles["body"]))

    story.extend(_section_title("Metodología", styles))
    story.append(
        _p(
            "El análisis incluye perfilado de variables, correlaciones Pearson y "
            "Spearman, dependencias categóricas, segmentación con "
            f"{_algorithm_name(clustering.algorithm) if clustering else 'el método disponible'} "
            "y detección de anomalías mediante Z-Score, IQR e Isolation Forest. "
            "Este documento presenta los resultados obtenidos.",
            styles["small"],
        )
    )

    if report.descriptive is not None and report.descriptive.statistics:
        story.extend(_section_title("Estadística descriptiva disponible", styles))
        descriptive_rows = [["Variable", "Indicadores"]]
        for variable, values in report.descriptive.statistics.items():
            indicators = ", ".join(
                f"{_humanize(name)}: {value:,.2f}" for name, value in values.items()
            )
            descriptive_rows.append([_humanize(variable), indicators])
        story.append(_data_table(descriptive_rows, [45 * mm, 125 * mm], styles))

    doc.build(
        story,
        onFirstPage=lambda canvas, current_doc: _draw_page_frame(
            canvas, current_doc, safe_filename
        ),
        onLaterPages=lambda canvas, current_doc: _draw_page_frame(
            canvas, current_doc, safe_filename
        ),
    )
    return buffer.getvalue()


def _render_summary_cards(report: Any) -> None:
    relationships = _strong_relationships(report)
    clustering = report.clustering
    consensus = _consensus_count(report)
    cards = [
        (
            "01 / RELACIONES",
            f"{len(relationships)} patrones destacados",
            (
                f"La relación principal conecta {_humanize(relationships[0].var_a).lower()} "
                f"con {_humanize(relationships[0].var_b).lower()}."
                if relationships
                else "No se encontraron relaciones numéricas fuertes."
            ),
        ),
        (
            "02 / SEGMENTOS",
            f"{clustering.n_clusters if clustering else 0} grupos encontrados",
            (
                f"La separación es {_cluster_quality(clustering.silhouette).lower()} "
                f"usando {_algorithm_name(clustering.algorithm)}."
                if clustering is not None and clustering.n_clusters
                else "No fue posible construir segmentos estables."
            ),
        ),
        (
            "03 / REVISIÓN",
            f"{consensus} coincidencias prioritarias",
            (
                f"{_any_anomaly_count(report)} registros recibieron al menos una señal."
                if report.anomalies
                else "No se generaron resultados de anomalías."
            ),
        ),
    ]
    columns = st.columns(3, gap="small")
    for column, (index, title, copy) in zip(columns, cards):
        with column:
            st.html(
                dedent(
                    f"""
                    <article class="seda-report-card">
                      <div class="seda-report-card-index">{html.escape(index)}</div>
                      <div class="seda-report-card-title">{html.escape(title)}</div>
                      <p>{html.escape(copy)}</p>
                    </article>
                    """
                ).strip()
            )


def render_report_view(report: Any, filename: str | None) -> None:
    """Presenta el cierre ejecutivo y permite descargar el PDF."""
    if report is None:
        st.info("Primero debes analizar un archivo.")
        return

    st.markdown(
        '<div class="seda-eyebrow">Documento final del análisis</div>',
        unsafe_allow_html=True,
    )
    st.title("Reporte del análisis")

    metrics = st.columns(4)
    metrics[0].metric("Registros", f"{report.profile.n_rows:,}")
    metrics[1].metric("Variables", report.profile.n_cols)
    metrics[2].metric("Resultados", len(report.insights))
    metrics[3].metric("Faltantes", f"{_missing_total(report):,}")

    st.markdown(
        '<div class="seda-section-heading">Resumen de resultados</div>',
        unsafe_allow_html=True,
    )
    st.html(
        dedent(
            f"""
            <article class="seda-report-summary">
              <div class="seda-report-summary-label">LECTURA GENERAL</div>
              <p>{html.escape(build_executive_summary(report))}</p>
            </article>
            """
        ).strip()
    )

    st.markdown(
        '<div class="seda-section-heading">Contenido del reporte</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          La vista resume los resultados de cada sección. El PDF incluye tablas,
          metodología, recomendaciones y limitaciones del análisis.
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_summary_cards(report)

    preview_column, action_column = st.columns([1.45, 0.75], gap="large")
    with preview_column:
        st.markdown(
            '<div class="seda-section-heading">Resultados incluidos</div>',
            unsafe_allow_html=True,
        )
        for insight in report.insights[:6]:
            css_class = (
                "seda-insight seda-insight-warning"
                if insight.severity == "warning"
                else "seda-insight"
            )
            st.html(
                f'<div class="{css_class}">{html.escape(insight.message)}</div>'
            )
        if len(report.insights) > 6:
            st.caption(
                f"El PDF incluye una selección de los {len(report.insights)} resultados."
            )

    with action_column:
        st.markdown(
            '<div class="seda-section-heading">Exportar</div>',
            unsafe_allow_html=True,
        )
        pdf_bytes = generate_pdf_report(report, filename)
        output_name = f"smarteda_reporte_{Path(str(filename or 'datos')).stem}.pdf"
        st.html(
            dedent(
                """
                <div class="seda-export-card">
                  <div class="seda-export-label">DOCUMENTO PDF</div>
                  <div class="seda-export-title">Disponible para descargar</div>
                  <p>
                    Incluye resumen, tablas, recomendaciones, metodología,
                    limitaciones y numeración de páginas.
                  </p>
                </div>
                """
            ).strip()
        )
        st.download_button(
            "Descargar reporte PDF",
            data=pdf_bytes,
            file_name=output_name,
            mime="application/pdf",
            type="primary",
            width="stretch",
        )
        st.caption(f"Documento generado en esta sesión · {len(pdf_bytes) / 1024:.1f} KB")

    with st.expander("Alcance y limitaciones del reporte"):
        st.markdown(
            """
            - Una relación no demuestra causalidad.
            - Los segmentos requieren interpretación según el contexto de los datos.
            - Un registro inusual no debe eliminarse automáticamente.
            - El resultado depende de la calidad del archivo analizado.
            - El número de fila procesada puede diferir del archivo original si la
              limpieza eliminó filas vacías o duplicadas.
            """
        )
