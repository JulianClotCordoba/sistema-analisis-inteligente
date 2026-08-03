"""Dashboard principal de SmartEDA.

Esta primera versión implementa la ruta vertical del frontend:

    cargar archivo -> ejecutar AnalysisEngine -> conservar AnalysisReport
    -> mostrar un resumen comprensible.

El frontend consume exclusivamente la API pública del paquete ``smarteda``.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Permite ejecutar `streamlit run app/main.py` desde la raíz sin instalar el
# paquete en modo editable. No modifica el backend.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from smarteda import AnalysisConfig, AnalysisEngine  # noqa: E402
from smarteda.exceptions import SmartEdaError  # noqa: E402
from app.anomalies import render_anomalies_view  # noqa: E402
from app.relationships import render_relationships_view  # noqa: E402
from app.reporting import render_report_view  # noqa: E402
from app.segments import render_segments_view  # noqa: E402


APP_TITLE = "SmartEDA"
SAMPLE_DATASET = PROJECT_ROOT / "data" / "samples" / "clientes.csv"
STYLESHEET = Path(__file__).resolve().parent / "assets" / "styles.css"

TYPE_LABELS = {
    "numeric": "Numérica",
    "categorical": "Categoría",
    "datetime": "Fecha",
    "boolean": "Sí / No",
    "text": "Texto",
    "unknown": "No identificado",
}

TYPE_COLORS = {
    "Numéricas": "#E4AD3A",
    "Categorías": "#D9C37C",
    "Fechas": "#C7792B",
    "Sí / No": "#8F9C75",
    "Texto": "#8A8B84",
}


def configure_page() -> None:
    """Configura la ventana y carga los estilos propios."""
    st.set_page_config(
        page_title=f"{APP_TITLE} · Análisis inteligente",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    if STYLESHEET.exists():
        st.markdown(
            f"<style>{STYLESHEET.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def initialize_state() -> None:
    """Crea el estado que debe sobrevivir a las recargas de Streamlit."""
    defaults = {
        "view": "Carga de datos",
        "report": None,
        "active_file": None,
        "selected_algorithm": "kmeans",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="seda-brand">
          <span class="seda-brand-rule"></span>
          <div class="seda-brand-name">SMART<span>EDA</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def navigate_to(view: str) -> None:
    st.session_state.view = view


def render_sidebar() -> None:
    """Navegación inicial, lista para crecer pantalla por pantalla."""
    render_brand()
    st.sidebar.caption("NAVEGACIÓN")

    if st.sidebar.button(
        "01  Carga de datos",
        width="stretch",
        type="primary" if st.session_state.view == "Carga de datos" else "secondary",
    ):
        navigate_to("Carga de datos")
        st.rerun()

    has_report = st.session_state.report is not None
    if st.sidebar.button(
        "02  Resumen",
        width="stretch",
        disabled=not has_report,
        type="primary" if st.session_state.view == "Resumen" else "secondary",
    ):
        navigate_to("Resumen")
        st.rerun()

    if st.sidebar.button(
        "03  Relaciones",
        width="stretch",
        disabled=not has_report,
        type="primary" if st.session_state.view == "Relaciones" else "secondary",
    ):
        navigate_to("Relaciones")
        st.rerun()

    if st.sidebar.button(
        "04  Segmentos",
        width="stretch",
        disabled=not has_report,
        type="primary" if st.session_state.view == "Segmentos" else "secondary",
    ):
        navigate_to("Segmentos")
        st.rerun()
    if st.sidebar.button(
        "05  Datos inusuales",
        width="stretch",
        disabled=not has_report,
        type="primary" if st.session_state.view == "Datos inusuales" else "secondary",
    ):
        navigate_to("Datos inusuales")
        st.rerun()
    if st.sidebar.button(
        "06  Reporte",
        width="stretch",
        disabled=not has_report,
        type="primary" if st.session_state.view == "Reporte" else "secondary",
    ):
        navigate_to("Reporte")
        st.rerun()

    st.sidebar.divider()
    if has_report:
        safe_name = html.escape(str(st.session_state.active_file))
        st.sidebar.markdown(
            f"""
            <div class="seda-status">
              Análisis disponible<br>
              <span style="font-weight:500">{safe_name}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.caption("Sube un archivo para habilitar los resultados.")


def analyze_source(source: Any, filename: str, algorithm: str) -> None:
    """Conecta el archivo de Streamlit con el motor público de Julián."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        config = AnalysisConfig(clustering_algorithm=algorithm)
        engine = AnalysisEngine(config)
        with st.spinner("Analizando estructura, relaciones y patrones..."):
            report = engine.analyze(source)
    except SmartEdaError as exc:
        st.error(
            "No pudimos analizar el archivo. Comprueba que tenga datos y que "
            "su formato sea CSV, TSV o Excel."
        )
        with st.expander("Ver detalle del error"):
            st.code(str(exc))
        return
    except Exception as exc:  # evita que la interfaz desaparezca ante un imprevisto
        st.error("Ocurrió un problema inesperado durante el análisis.")
        with st.expander("Ver detalle técnico"):
            st.exception(exc)
        return

    st.session_state.report = report
    st.session_state.active_file = filename
    st.session_state.selected_algorithm = algorithm
    st.session_state.view = "Resumen"
    st.rerun()


def render_hero() -> None:
    st.markdown(
        """
        <section class="seda-hero">
          <div class="seda-hero-copy">
            <div class="seda-eyebrow">Exploración automática de datos</div>
            <h1>Análisis exploratorio<br><em>sin fricción técnica.</em></h1>
            <p>
              Sube un CSV o Excel. SmartEDA detecta estructura, relaciones,
              segmentos y registros inusuales en segundos.
            </p>
            <div class="seda-hero-formats">
              <span>CSV / XLSX</span>
              <span>Sin configuración</span>
              <span>Resultados explicables</span>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-process-strip">
          <div class="seda-feature">
            <div class="seda-feature-index">01 / PERFIL</div>
            <div class="seda-feature-title">Entiende la estructura</div>
            <div class="seda-feature-copy">
              Tipos, faltantes y calidad de cada variable.
            </div>
          </div>
          <div class="seda-feature">
            <div class="seda-feature-index">02 / PATRONES</div>
            <div class="seda-feature-title">Detecta relaciones</div>
            <div class="seda-feature-copy">
              Correlaciones y grupos que vale la pena revisar.
            </div>
          </div>
          <div class="seda-feature">
            <div class="seda-feature-index">03 / LECTURA</div>
            <div class="seda-feature-title">Llega a lo importante</div>
            <div class="seda-feature-copy">
              Hallazgos técnicos traducidos a lenguaje claro.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_view() -> None:
    """Pantalla inicial de carga y configuración."""
    render_hero()
    st.markdown('<div class="seda-section-heading">Comienza tu análisis</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="seda-section-copy">Selecciona un archivo o utiliza el dataset de demostración.</div>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Archivo de datos",
        type=["csv", "tsv", "txt", "xlsx", "xls"],
        help="Formatos admitidos: CSV, TSV, TXT, XLSX y XLS.",
        label_visibility="collapsed",
    )

    with st.expander("Opciones avanzadas"):
        algorithm = st.radio(
            "Método de segmentación",
            options=["kmeans", "dbscan"],
            format_func=lambda value: "K-Means" if value == "kmeans" else "DBSCAN",
            horizontal=True,
            index=0 if st.session_state.selected_algorithm == "kmeans" else 1,
            help=(
                "K-Means crea grupos para todos los registros. DBSCAN puede dejar "
                "como inusuales aquellos que no encajan en ningún grupo."
            ),
        )
        st.caption(
            "Esta elección solo cambia la forma de crear segmentos; el resto del "
            "análisis se ejecuta de la misma manera."
        )

    primary_col, sample_col = st.columns([1, 1])
    with primary_col:
        if st.button(
            "Analizar archivo",
            type="primary",
            width="stretch",
            disabled=uploaded_file is None,
        ):
            analyze_source(uploaded_file, uploaded_file.name, algorithm)
    with sample_col:
        if st.button("Usar datos de ejemplo", width="stretch"):
            analyze_source(SAMPLE_DATASET, SAMPLE_DATASET.name, algorithm)

    st.caption(
        "El archivo se procesa durante la sesión actual. Esta versión no almacena "
        "los datos en una base de datos."
    )


def build_profile_table(report: Any) -> pd.DataFrame:
    """Convierte el perfil entregado por Julián en una tabla para la interfaz."""
    rows = []
    for column in report.profile.columns:
        dtype = getattr(column.dtype, "value", str(column.dtype))
        samples = ", ".join(str(value) for value in column.sample_values)
        rows.append(
            {
                "Variable": column.name,
                "Tipo detectado": TYPE_LABELS.get(dtype, dtype),
                "Faltantes": column.missing_count,
                "% faltante": f"{column.missing_ratio * 100:.1f}%",
                "Valores únicos": column.unique_count,
                "Ejemplos": samples or "—",
            }
        )
    return pd.DataFrame(rows)


def build_variable_type_chart(report: Any) -> go.Figure:
    """Representa los tipos que DataProfiler ya clasificó en el backend."""
    profile = report.profile
    counts = {
        "Numéricas": len(profile.numeric_columns),
        "Categorías": len(profile.categorical_columns),
        "Fechas": len(profile.datetime_columns),
        "Sí / No": len(profile.boolean_columns),
        "Texto": len(profile.text_columns),
    }
    visible = {label: value for label, value in counts.items() if value > 0}
    figure = go.Figure(
        go.Pie(
            labels=list(visible),
            values=list(visible.values()),
            hole=0.64,
            sort=False,
            textinfo="label+value",
            hovertemplate="%{label}: %{value} variable(s)<extra></extra>",
            marker={
                "colors": [TYPE_COLORS[label] for label in visible],
                "line": {"color": "#0C0D0B", "width": 3},
            },
        )
    )
    figure.update_layout(
        height=320,
        margin={"l": 12, "r": 12, "t": 20, "b": 20},
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#F1ECDD", "size": 13},
        annotations=[
            {
                "text": f"<b>{profile.n_cols}</b><br><span>variables</span>",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 17, "color": "#F1ECDD"},
            }
        ],
    )
    return figure


def render_insight(insight: Any) -> None:
    css_class = (
        "seda-insight seda-insight-warning"
        if insight.severity == "warning"
        else "seda-insight"
    )
    safe_message = html.escape(insight.message)
    st.markdown(
        f'<div class="{css_class}">{safe_message}</div>',
        unsafe_allow_html=True,
    )


def render_summary_view() -> None:
    """Primera pantalla de resultados construida desde AnalysisReport."""
    report = st.session_state.report
    if report is None:
        st.info("Primero debes analizar un archivo.")
        return

    safe_name = html.escape(str(st.session_state.active_file))
    elapsed = report.metadata.get("elapsed_seconds", 0)
    st.markdown('<div class="seda-eyebrow">Análisis completado</div>', unsafe_allow_html=True)
    st.title("Resumen de tus datos")
    st.markdown(
        f"""
        <div class="seda-file-line">
          <div>
            <div class="seda-file-name">{safe_name}</div>
            <div class="seda-file-meta">Archivo analizado correctamente</div>
          </div>
          <div class="seda-file-meta">{elapsed:.3f} segundos</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_missing = sum(column.missing_count for column in report.profile.columns)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Registros", f"{report.profile.n_rows:,}")
    metric_cols[1].metric("Variables", report.profile.n_cols)
    metric_cols[2].metric("Valores faltantes", f"{total_missing:,}")
    metric_cols[3].metric("Hallazgos", len(report.insights))

    insight_col, chart_col = st.columns([1.35, 1], gap="large")
    with insight_col:
        st.markdown('<div class="seda-section-heading">Qué encontró SmartEDA</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="seda-section-copy">Una primera lectura automática de la estructura y los patrones del archivo.</div>',
            unsafe_allow_html=True,
        )
        visible_insights = report.insights[:4]
        for insight in visible_insights:
            render_insight(insight)
    with chart_col:
        st.markdown('<div class="seda-section-heading">Composición</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="seda-section-copy">Tipos de variables identificados por el motor.</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            build_variable_type_chart(report),
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )

    if len(report.insights) > len(visible_insights):
        with st.expander(f"Ver los {len(report.insights)} hallazgos"):
            for insight in report.insights:
                render_insight(insight)

    st.markdown('<div class="seda-section-heading">Variables detectadas</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="seda-section-copy">El motor identificó automáticamente el tipo y la calidad básica de cada columna.</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        build_profile_table(report),
        width="stretch",
        hide_index=True,
    )

    with st.expander("¿Cómo se obtuvo este resumen?"):
        st.markdown(
            """
            El frontend envió el archivo a `AnalysisEngine.analyze()`. El motor de
            Julián realizó la carga, limpieza, detección de tipos, correlaciones,
            clustering, anomalías e insights. Esta pantalla toma los datos de
            `report.profile`, `report.metadata` y `report.insights`; no vuelve a
            calcular el análisis.
            """
        )

    action_col, spacer_col = st.columns([1, 2])
    with action_col:
        if st.button("Analizar otro archivo", width="stretch"):
            st.session_state.report = None
            st.session_state.active_file = None
            st.session_state.view = "Carga de datos"
            st.rerun()


def main() -> None:
    configure_page()
    initialize_state()
    render_sidebar()

    if st.session_state.view == "Resumen":
        render_summary_view()
    elif st.session_state.view == "Relaciones":
        render_relationships_view(
            st.session_state.report,
            st.session_state.active_file,
        )
    elif st.session_state.view == "Segmentos":
        render_segments_view(
            st.session_state.report,
            st.session_state.active_file,
        )
    elif st.session_state.view == "Datos inusuales":
        render_anomalies_view(
            st.session_state.report,
            st.session_state.active_file,
        )
    elif st.session_state.view == "Reporte":
        render_report_view(
            st.session_state.report,
            st.session_state.active_file,
        )
    else:
        render_upload_view()


if __name__ == "__main__":
    main()
