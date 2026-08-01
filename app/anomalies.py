"""Pantalla de datos inusuales basada en los resultados del backend SmartEDA."""

from __future__ import annotations

import html
from textwrap import dedent
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


METHOD_NAMES = {
    "zscore": "Z-Score",
    "iqr": "IQR",
    "isolation_forest": "Isolation Forest",
}

METHOD_SHORT = {
    "zscore": "Busca valores muy alejados del promedio.",
    "iqr": "Busca valores fuera del rango habitual de la mayoría.",
    "isolation_forest": "Busca combinaciones de valores difíciles de agrupar.",
}

METHOD_EXPLANATIONS = {
    "zscore": (
        "Compara cada valor con el promedio de su variable. Señala una fila cuando "
        "al menos uno de sus números está extremadamente lejos de lo habitual."
    ),
    "iqr": (
        "Se concentra en la zona donde se encuentra la mayoría de los datos y "
        "marca valores que quedan muy por fuera de ese rango central."
    ),
    "isolation_forest": (
        "Un modelo de aprendizaje automático observa todas las variables juntas. "
        "Detecta registros cuya combinación numérica es poco común."
    ),
}


def _humanize(value: Any) -> str:
    return str(value).replace("_", " ").strip().capitalize()


def _method_name(value: str) -> str:
    return METHOD_NAMES.get(value, _humanize(value))


def _result_map(report: Any) -> dict[str, Any]:
    return {result.method: result for result in report.anomalies}


def _consensus_mask(results: list[Any]) -> np.ndarray:
    if not results:
        return np.array([], dtype=bool)
    masks = [np.asarray(result.outlier_mask, dtype=bool) for result in results]
    return np.logical_and.reduce(masks)


def _any_mask(results: list[Any]) -> np.ndarray:
    if not results:
        return np.array([], dtype=bool)
    masks = [np.asarray(result.outlier_mask, dtype=bool) for result in results]
    return np.logical_or.reduce(masks)


def _review_queue(results: list[Any]) -> pd.DataFrame:
    """Resume el acuerdo entre métodos sin volver a detectar anomalías."""
    if not results:
        return pd.DataFrame(columns=["Fila procesada", "Métodos", "Coincidencias", "Prioridad"])

    masks = {
        result.method: np.asarray(result.outlier_mask, dtype=bool)
        for result in results
    }
    rows: list[dict[str, Any]] = []
    for index in np.flatnonzero(np.logical_or.reduce(list(masks.values()))):
        detected_by = [method for method, mask in masks.items() if mask[index]]
        count = len(detected_by)
        if count == len(results):
            priority = "Alta"
        elif count >= 2:
            priority = "Media"
        else:
            priority = "Explorar"
        rows.append(
            {
                "Fila procesada": int(index + 1),
                "Métodos": ", ".join(_method_name(method) for method in detected_by),
                "Coincidencias": count,
                "Prioridad": priority,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["Coincidencias", "Fila procesada"], ascending=[False, True]
    )


def build_anomaly_scatter(report: Any, selected: Any) -> go.Figure:
    """Ubica atípicos sobre la proyección que ya produjo el clustering."""
    projection = np.asarray(report.clustering.projection_2d)
    selected_mask = np.asarray(selected.outlier_mask, dtype=bool)
    consensus = _consensus_mask(report.anomalies)
    selected_only = selected_mask & ~consensus
    normal = ~selected_mask
    indexes = np.arange(len(selected_mask)) + 1

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=projection[normal, 0],
            y=projection[normal, 1],
            mode="markers",
            name="Sin señal en este método",
            customdata=indexes[normal],
            marker={"size": 7, "color": "#5D5F57", "opacity": 0.42},
            hovertemplate=(
                "<b>Fila procesada %{customdata}</b><br>"
                "Este método no la marcó para revisión.<extra></extra>"
            ),
        )
    )
    if selected_only.any():
        figure.add_trace(
            go.Scatter(
                x=projection[selected_only, 0],
                y=projection[selected_only, 1],
                mode="markers",
                name=f"Señal de {_method_name(selected.method)}",
                customdata=indexes[selected_only],
                marker={
                    "size": 12,
                    "color": "#DF8436",
                    "symbol": "diamond",
                    "line": {"color": "#F1CB70", "width": 1.2},
                },
                hovertemplate=(
                    "<b>Fila procesada %{customdata}</b><br>"
                    f"Marcada por {_method_name(selected.method)}.<extra></extra>"
                ),
            )
        )
    selected_consensus = selected_mask & consensus
    if selected_consensus.any():
        figure.add_trace(
            go.Scatter(
                x=projection[selected_consensus, 0],
                y=projection[selected_consensus, 1],
                mode="markers",
                name="Coincidencia de todos",
                customdata=indexes[selected_consensus],
                marker={
                    "size": 15,
                    "color": "#E4AD3A",
                    "symbol": "x",
                    "line": {"color": "#F1ECDD", "width": 2},
                },
                hovertemplate=(
                    "<b>Fila procesada %{customdata}</b><br>"
                    "Todos los métodos recomiendan revisarla.<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        height=500,
        margin={"l": 28, "r": 20, "t": 25, "b": 30},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#11130F",
        font={"family": "Arial, sans-serif", "color": "#F1ECDD"},
        hoverlabel={"bgcolor": "#171914", "bordercolor": "#E4AD3A"},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 11, "color": "#AAA89F"},
        },
        xaxis={
            "title": "Vista resumida 1",
            "gridcolor": "#24251F",
            "zerolinecolor": "#37362F",
        },
        yaxis={
            "title": "Vista resumida 2",
            "gridcolor": "#24251F",
            "zerolinecolor": "#37362F",
        },
    )
    return figure


def build_method_comparison_chart(results: list[Any]) -> go.Figure:
    names = [_method_name(result.method) for result in results]
    values = [result.outlier_ratio * 100 for result in results]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            text=[f"{result.outlier_count} · {value:.1f}%" for result, value in zip(results, values)],
            textposition="outside",
            cliponaxis=False,
            marker={
                "color": ["#E4AD3A", "#D7C57C", "#DF8436"][: len(results)],
                "line": {"color": "#F1CB70", "width": 0.7},
            },
            hovertemplate="<b>%{y}</b><br>%{x:.1f}% de registros<extra></extra>",
        )
    )
    upper = max(values, default=1)
    figure.update_layout(
        height=max(290, len(results) * 78),
        margin={"l": 20, "r": 90, "t": 20, "b": 35},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#F1ECDD"},
        showlegend=False,
        xaxis={
            "title": "Porcentaje marcado",
            "ticksuffix": "%",
            "range": [0, max(upper * 1.35, 5)],
            "gridcolor": "#24251F",
            "zeroline": False,
        },
        yaxis={"autorange": "reversed", "showgrid": False},
    )
    return figure


def _render_empty_state(title: str, message: str) -> None:
    st.html(
        dedent(
            f"""
            <div class="seda-empty-state">
              <div class="seda-empty-kicker">Sin resultados disponibles</div>
              <div class="seda-empty-title">{html.escape(title)}</div>
              <div class="seda-empty-copy">{html.escape(message)}</div>
            </div>
            """
        ).strip()
    )


def _render_method_note(result: Any) -> None:
    detail = ""
    if result.method == "zscore":
        detail = f"Umbral usado: {result.details.get('threshold', '—')} desviaciones."
    elif result.method == "iqr":
        detail = f"Amplitud aplicada al rango central: {result.details.get('multiplier', '—')}."
    else:
        contamination = result.details.get("contamination", "auto")
        detail = f"Proporción esperada configurada: {contamination}."
    st.html(
        dedent(
            f"""
            <div class="seda-method-note">
              <span>{html.escape(_method_name(result.method))}</span>
              <p>{html.escape(METHOD_EXPLANATIONS[result.method])}</p>
            </div>
            """
        ).strip()
    )
    st.caption(detail)


def _render_method_cards(results: list[Any], total: int) -> None:
    columns = st.columns(len(results), gap="small")
    for column, result in zip(columns, results):
        with column:
            st.html(
                dedent(
                    f"""
                    <article class="seda-anomaly-method-card">
                      <div class="seda-anomaly-method">{html.escape(_method_name(result.method))}</div>
                      <div class="seda-anomaly-count">{result.outlier_count:,}</div>
                      <div class="seda-anomaly-ratio">{result.outlier_ratio * 100:.1f}% de {total:,}</div>
                      <p>{html.escape(METHOD_SHORT[result.method])}</p>
                    </article>
                    """
                ).strip()
            )


def _render_method_details(result: Any) -> None:
    if result.method == "zscore":
        per_column = result.details.get("outliers_per_column", {})
        rows = [
            {"Variable": _humanize(column), "Señales encontradas": count}
            for column, count in per_column.items()
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    elif result.method == "iqr":
        bounds = result.details.get("bounds", {})
        rows = [
            {
                "Variable": _humanize(column),
                "Límite inferior": f"{values['lower']:,.2f}",
                "Límite superior": f"{values['upper']:,.2f}",
            }
            for column, values in bounds.items()
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.write(
            "Isolation Forest considera simultáneamente todas las variables. Por "
            "eso no atribuye cada señal a una sola columna."
        )


def _decision_guidance(results: list[Any], total: int) -> list[tuple[str, str, str]]:
    consensus_count = int(_consensus_mask(results).sum())
    any_count = int(_any_mask(results).sum())
    broadest = max(results, key=lambda result: result.outlier_count)

    first = (
        "Empieza por las coincidencias",
        (
            f"{consensus_count} registros fueron señalados por todos los métodos. "
            "Revísalos primero porque la evidencia es más consistente."
            if consensus_count
            else "Ningún registro fue señalado por todos. Revisa las señales como hipótesis separadas."
        ),
    )
    second = (
        "Usa cada método como una mirada distinta",
        (
            f"{_method_name(broadest.method)} marcó el conjunto más amplio. "
            "Úsalo para explorar combinaciones raras y contrástalo con los métodos más estrictos."
        ),
    )
    third = (
        "Confirma antes de corregir o eliminar",
        (
            f"En total, {any_count} de {total} registros recibieron al menos una señal. "
            "Comprueba su origen y contexto: pueden ser errores, casos legítimos o información valiosa."
        ),
    )
    return [
        ("01 / PRIORIZAR", first[0], first[1]),
        ("02 / CONTRASTAR", second[0], second[1]),
        ("03 / VALIDAR", third[0], third[1]),
    ]


def _render_decision_guidance(results: list[Any], total: int) -> None:
    columns = st.columns(3, gap="small")
    for column, (index, title, message) in zip(
        columns, _decision_guidance(results, total)
    ):
        with column:
            st.html(
                dedent(
                    f"""
                    <article class="seda-decision-card">
                      <div class="seda-decision-index">{html.escape(index)}</div>
                      <div class="seda-decision-title">{html.escape(title)}</div>
                      <p>{html.escape(message)}</p>
                      <div class="seda-decision-source">Orientación basada en el acuerdo</div>
                    </article>
                    """
                ).strip()
            )


def render_anomalies_view(report: Any, filename: str | None) -> None:
    """Renderiza la experiencia completa de datos inusuales."""
    if report is None:
        st.info("Primero debes analizar un archivo.")
        return

    st.markdown(
        '<div class="seda-eyebrow">Señales que merecen revisión</div>',
        unsafe_allow_html=True,
    )
    st.title("¿Qué registros se comportan de forma inusual?")
    st.markdown(
        """
        <div class="seda-page-lead">
          SmartEDA utiliza tres perspectivas para encontrar valores extremos y
          combinaciones poco frecuentes.
          <strong>“Inusual” no significa incorrecto, fraude ni problema. Significa
          que el registro merece contexto antes de tomar una decisión.</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    results = list(report.anomalies)
    if not results:
        _render_empty_state(
            "El motor no generó resultados de anomalías.",
            "Se necesitan variables numéricas y suficientes registros para ejecutar los detectores.",
        )
        return

    total = len(results[0].outlier_mask)
    variables = ", ".join(_humanize(value) for value in results[0].columns_analyzed)
    safe_filename = html.escape(str(filename or "Dataset"))
    st.markdown(
        f"""
        <div class="seda-context-line">
          <span>Archivo analizado</span>
          <strong>{safe_filename}</strong>
          <span>{total:,} registros procesados</span>
          <span>{html.escape(variables)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    method_map = _result_map(report)
    available = [method for method in METHOD_NAMES if method in method_map]
    selected_method = st.radio(
        "Método de revisión",
        options=available,
        format_func=_method_name,
        horizontal=True,
        key="anomaly_method",
        help="Cambia la perspectiva sin volver a analizar el archivo.",
    )
    selected = method_map[selected_method]
    consensus_count = int(_consensus_mask(results).sum())
    any_count = int(_any_mask(results).sum())

    metrics = st.columns(4)
    metrics[0].metric(
        "Registros marcados",
        selected.outlier_count,
        help="Cantidad de filas señaladas por el método seleccionado.",
    )
    metrics[1].metric("Porcentaje del total", f"{selected.outlier_ratio * 100:.1f}%")
    metrics[2].metric(
        "Coincidencia total",
        consensus_count,
        help="Registros marcados por todos los métodos disponibles.",
    )
    metrics[3].metric("Con alguna señal", any_count)

    _render_method_note(selected)

    st.markdown(
        '<div class="seda-section-heading">Mapa de revisión</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          Los puntos destacados son las filas marcadas por el método seleccionado.
          Una cruz dorada indica coincidencia entre todos los métodos. Las posiciones
          son una vista resumida de las variables, no sus valores originales.
        </div>
        """,
        unsafe_allow_html=True,
    )
    if (
        report.clustering is not None
        and report.clustering.projection_2d is not None
        and len(report.clustering.projection_2d) == total
    ):
        st.plotly_chart(
            build_anomaly_scatter(report, selected),
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )
    else:
        _render_empty_state(
            "No se puede construir el mapa visual.",
            "Las detecciones siguen disponibles, pero el reporte no contiene una proyección compatible.",
        )

    with st.expander(f"Ver detalle técnico de {_method_name(selected.method)}"):
        _render_method_details(selected)

    st.markdown(
        '<div class="seda-section-heading">Qué detectó cada método</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          No se espera que los tres resultados sean iguales: cada método define lo
          inusual de una manera diferente. La comparación ayuda a separar señales
          muy claras de casos que solo una perspectiva considera raros.
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_method_cards(results, total)
    st.plotly_chart(
        build_method_comparison_chart(results),
        width="stretch",
        config={"displayModeBar": False, "responsive": True},
    )

    st.markdown(
        '<div class="seda-section-heading">Prioridad de revisión</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          La tabla ordena primero las filas en las que coinciden más métodos. El
          número corresponde a la posición en los datos procesados por el motor;
          si se eliminaron filas vacías o duplicadas, puede diferir del archivo original.
        </div>
        """,
        unsafe_allow_html=True,
    )
    queue = _review_queue(results)
    st.dataframe(queue, width="stretch", hide_index=True)

    st.markdown(
        '<div class="seda-section-heading">Cómo actuar con estas señales</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          Utiliza los resultados para organizar una revisión, nunca para eliminar
          registros o tomar medidas sobre personas de forma automática.
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_decision_guidance(results, total)

    with st.expander("Z-Score, IQR e Isolation Forest sin fórmulas"):
        st.markdown(
            """
            - **Z-Score:** pregunta si un valor está extremadamente lejos del promedio.
            - **IQR:** pregunta si un valor queda fuera de la zona donde se concentra
              la mayoría de los registros.
            - **Isolation Forest:** pregunta si la combinación completa de valores
              es fácil o difícil de encontrar entre los demás registros.

            Z-Score e IQR suelen ser más estrictos con extremos individuales.
            Isolation Forest puede encontrar más casos porque observa patrones conjuntos.
            """
        )

    with st.expander("¿Cómo se construyó esta pantalla?"):
        st.markdown(
            """
            El frontend no volvió a ejecutar los detectores. Consumió directamente:

            - `report.anomalies[i].method`
            - `report.anomalies[i].outlier_mask`
            - `report.anomalies[i].outlier_count`
            - `report.anomalies[i].outlier_ratio`
            - `report.anomalies[i].columns_analyzed`
            - `report.anomalies[i].details`
            - `report.clustering.projection_2d` para el mapa

            La prioridad se obtiene comparando las máscaras ya calculadas por Julián;
            no se recalcula ninguna anomalía. El reporte actual no incluye el DataFrame
            limpio, por eso esta pantalla no inventa valores originales ni boxplots.
            """
        )
