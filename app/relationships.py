"""Pantalla de relaciones entre variables.

Esta vista consume los resultados que ya vienen en ``AnalysisReport``:

- matrices completas de Pearson y Spearman;
- pares fuertes encontrados por el backend;
- dependencias categórica -> numérica mediante eta cuadrado.

El frontend únicamente los organiza, explica y visualiza.
"""

from __future__ import annotations

import html
from textwrap import dedent
from typing import Any

import numpy as np
import plotly.graph_objects as go
import streamlit as st


METHOD_NAMES = {
    "pearson": "Pearson",
    "spearman": "Spearman",
}

METHOD_EXPLANATIONS = {
    "pearson": (
        "Busca relaciones que siguen una dirección bastante uniforme. Es útil "
        "para reconocer si dos variables numéricas suben o bajan de manera parecida."
    ),
    "spearman": (
        "Observa el orden general de los valores. Puede encontrar una tendencia "
        "aunque el cambio no ocurra siempre al mismo ritmo."
    ),
}


def _humanize(name: Any) -> str:
    """Convierte nombres técnicos de columnas en etiquetas legibles."""
    label = str(name).replace("_", " ").strip()
    return label[:1].upper() + label[1:] if label else "Variable"


def _relationship_sentence(var_a: str, var_b: str, coefficient: float) -> str:
    """Traduce el signo de una correlación a una frase cotidiana."""
    first = _humanize(var_a)
    second = _humanize(var_b).lower()
    if coefficient >= 0:
        return (
            f"Cuando {first.lower()} aumenta, {second} también tiende a aumentar."
        )
    return f"Cuando {first.lower()} aumenta, {second} tiende a disminuir."


def _association_label(value: float) -> str:
    """Etiqueta orientativa para comunicar eta cuadrado sin jerga."""
    if value >= 0.50:
        return "Muy marcada"
    if value >= 0.26:
        return "Marcada"
    return "Relevante"


def _pair_key(relationship: Any) -> frozenset[str]:
    return frozenset(
        {
            str(relationship.var_a),
            str(relationship.var_b),
        }
    )


def _decision_guidance(
    report: Any,
    selected_method: str,
) -> list[tuple[str, str, str, str]]:
    """Convierte resultados existentes en orientaciones prudentes de uso."""
    result = report.correlations[selected_method]
    guidance: list[tuple[str, str, str, str]] = []

    if result.strong_pairs:
        strongest = max(
            result.strong_pairs,
            key=lambda relationship: abs(float(relationship.coefficient)),
        )
        first = _humanize(strongest.var_a)
        second = _humanize(strongest.var_b)
        guidance.append(
            (
                "01 / PRIORIZAR",
                f"Analiza {first.lower()} junto a {second.lower()}",
                (
                    f"Es el patrón más consistente desde {METHOD_NAMES[selected_method]} "
                    f"({strongest.coefficient:+.2f}). Úsalas juntas en comparaciones "
                    "y revisa los registros que se alejan de la tendencia."
                ),
                f"Basado en {METHOD_NAMES[selected_method]}",
            )
        )
    else:
        guidance.append(
            (
                "01 / NO FORZAR",
                "Evalúa cada variable por separado",
                (
                    "Este método no encontró una relación suficientemente fuerte. "
                    "Evita crear una regla entre variables solo porque algunos "
                    "registros parezcan coincidir."
                ),
                "Basado en el umbral del backend",
            )
        )

    pearson_pairs = {
        _pair_key(relationship): relationship
        for relationship in report.correlations.get("pearson", result).strong_pairs
    }
    spearman_pairs = {
        _pair_key(relationship): relationship
        for relationship in report.correlations.get("spearman", result).strong_pairs
    }
    spearman_only = [
        relationship
        for key, relationship in spearman_pairs.items()
        if key not in pearson_pairs
    ]

    if spearman_only:
        relationship = max(
            spearman_only,
            key=lambda item: abs(float(item.coefficient)),
        )
        first = _humanize(relationship.var_a)
        second = _humanize(relationship.var_b)
        guidance.append(
            (
                "02 / INTERPRETAR",
                "Busca una tendencia, no una regla exacta",
                (
                    f"{first} y {second.lower()} muestran una tendencia fuerte en "
                    "Spearman, pero no una relación igualmente uniforme en Pearson. "
                    "Úsala para orientar preguntas, no para predecir un valor exacto."
                ),
                "Comparación Pearson vs. Spearman",
            )
        )
    else:
        guidance.append(
            (
                "02 / CONFIRMAR",
                "Contrasta el patrón con el contexto",
                (
                    "Una relación estadística es una señal para investigar. Antes "
                    "de tomar una decisión, revisa si el patrón tiene sentido para "
                    "el proceso, negocio o fenómeno representado."
                ),
                "Relación no significa causalidad",
            )
        )

    if report.dependencies:
        dependency = report.dependencies[0]
        categorical = _humanize(dependency.categorical)
        numeric = _humanize(dependency.numeric)
        guidance.append(
            (
                "03 / COMPARAR",
                f"Separa el análisis por {categorical.lower()}",
                (
                    f"{numeric} cambia de forma {_association_label(dependency.eta_squared).lower()} "
                    f"entre las categorías de {categorical.lower()}. Antes de usar "
                    "un promedio general, compara los grupos por separado."
                ),
                f"Asociación observada: {dependency.eta_squared * 100:.0f}%",
            )
        )
    else:
        guidance.append(
            (
                "03 / EXPLORAR",
                "No segmentes sin una diferencia clara",
                (
                    "El análisis no encontró asociaciones relevantes entre "
                    "categorías y números. Mantén una lectura general hasta tener "
                    "evidencia suficiente para separar grupos."
                ),
                "Basado en eta cuadrado",
            )
        )

    return guidance


def _strongest_value(matrix: Any) -> float | None:
    """Obtiene la mayor relación fuera de la diagonal de una matriz."""
    if matrix is None or matrix.shape[0] < 2:
        return None
    values = np.abs(matrix.to_numpy(dtype=float))
    np.fill_diagonal(values, np.nan)
    if np.isnan(values).all():
        return None
    return float(np.nanmax(values))


def build_correlation_heatmap(result: Any) -> go.Figure:
    """Construye el mapa interactivo usando la matriz calculada por el backend."""
    matrix = result.matrix
    labels = [_humanize(column) for column in matrix.columns]
    figure = go.Figure(
        go.Heatmap(
            z=matrix.to_numpy(dtype=float),
            x=labels,
            y=labels,
            zmin=-1,
            zmax=1,
            zmid=0,
            xgap=2,
            ygap=2,
            colorscale=[
                [0.0, "#B75637"],
                [0.35, "#593525"],
                [0.5, "#24251F"],
                [0.65, "#76602B"],
                [1.0, "#E4AD3A"],
            ],
            texttemplate="%{z:.2f}",
            textfont={"color": "#F1ECDD", "size": 13},
            hovertemplate=(
                "<b>%{x}</b> y <b>%{y}</b><br>"
                "Índice de relación: %{z:.2f}<extra></extra>"
            ),
            colorbar={
                "title": {
                    "text": "Relación",
                    "side": "right",
                    "font": {"color": "#AAA89F", "size": 11},
                },
                "tickvals": [-1, 0, 1],
                "ticktext": ["Inversa", "Sin patrón", "Directa"],
                "thickness": 12,
                "len": 0.78,
                "outlinewidth": 0,
                "tickfont": {"color": "#AAA89F", "size": 11},
            },
        )
    )
    chart_height = max(390, min(650, 92 * len(labels)))
    figure.update_layout(
        height=chart_height,
        margin={"l": 25, "r": 25, "t": 42, "b": 25},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#F1ECDD"},
        xaxis={
            "side": "top",
            "tickangle": 0,
            "showgrid": False,
            "zeroline": False,
        },
        yaxis={
            "autorange": "reversed",
            "showgrid": False,
            "zeroline": False,
        },
    )
    return figure


def build_dependency_chart(dependencies: list[Any]) -> go.Figure:
    """Representa las asociaciones categóricas relevantes que entrega Julián."""
    labels = [
        f"{_humanize(dep.categorical)} → {_humanize(dep.numeric)}"
        for dep in dependencies
    ]
    values = [dep.eta_squared * 100 for dep in dependencies]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            text=[f"{value:.0f}%" for value in values],
            textposition="outside",
            cliponaxis=False,
            marker={
                "color": "#E4AD3A",
                "line": {"color": "#F1CB70", "width": 1},
            },
            hovertemplate="<b>%{y}</b><br>Asociación: %{x:.1f}%<extra></extra>",
        )
    )
    figure.update_layout(
        height=max(280, 75 * len(labels)),
        margin={"l": 20, "r": 55, "t": 18, "b": 35},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#F1ECDD"},
        xaxis={
            "range": [0, 100],
            "ticksuffix": "%",
            "gridcolor": "#2A2B25",
            "zeroline": False,
            "title": "Intensidad de la asociación",
        },
        yaxis={
            "autorange": "reversed",
            "showgrid": False,
            "zeroline": False,
        },
    )
    return figure


def _render_empty_state(title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="seda-empty-state">
          <div class="seda-empty-kicker">Sin resultados disponibles</div>
          <div class="seda-empty-title">{html.escape(title)}</div>
          <div class="seda-empty-copy">{html.escape(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_relationship_cards(result: Any) -> None:
    pairs = result.strong_pairs
    if not pairs:
        _render_empty_state(
            "No encontramos relaciones fuertes con este método.",
            (
                "Las variables pueden seguir siendo útiles por separado. El mapa "
                "inferior permite revisar relaciones más suaves."
            ),
        )
        return

    card_columns = st.columns(2, gap="small") if len(pairs) > 1 else None
    for index, relationship in enumerate(pairs):
        coefficient = float(relationship.coefficient)
        direction = "Mismo sentido" if coefficient >= 0 else "Sentido contrario"
        safe_a = html.escape(_humanize(relationship.var_a))
        safe_b = html.escape(_humanize(relationship.var_b))
        safe_sentence = html.escape(
            _relationship_sentence(
                relationship.var_a,
                relationship.var_b,
                coefficient,
            )
        )
        card_html = dedent(
            f"""
            <article class="seda-relation-card">
              <div class="seda-relation-topline">
                <span>Relación {html.escape(relationship.strength)}</span>
                <span>{html.escape(METHOD_NAMES.get(relationship.method, relationship.method))}</span>
              </div>
              <div class="seda-relation-pair">{safe_a}<span>↔</span>{safe_b}</div>
              <p>{safe_sentence}</p>
              <div class="seda-relation-score">
                <div>
                  <span class="seda-score-label">Índice</span>
                  <strong>{coefficient:+.2f}</strong>
                </div>
                <span class="seda-direction-pill">{direction}</span>
              </div>
            </article>
            """
        ).strip()
        if card_columns:
            with card_columns[index % 2]:
                st.html(card_html)
        else:
            st.html(card_html)


def _render_dependency_cards(dependencies: list[Any]) -> None:
    for dependency in dependencies:
        percentage = dependency.eta_squared * 100
        categorical = html.escape(_humanize(dependency.categorical))
        numeric = html.escape(_humanize(dependency.numeric))
        label = _association_label(dependency.eta_squared)
        card_html = dedent(
            f"""
            <article class="seda-dependency-card">
              <div class="seda-dependency-value">{percentage:.0f}%</div>
              <div>
                <div class="seda-dependency-label">{html.escape(label)}</div>
                <div class="seda-dependency-title">{categorical} → {numeric}</div>
                <p>
                  Los valores de <strong>{numeric.lower()}</strong> cambian de forma
                  importante entre las categorías de
                  <strong>{categorical.lower()}</strong>.
                </p>
              </div>
            </article>
            """
        ).strip()
        st.html(card_html)


def _render_decision_guidance(report: Any, selected_method: str) -> None:
    guidance = _decision_guidance(report, selected_method)
    columns = st.columns(3, gap="small")
    for column, (index, title, message, source) in zip(columns, guidance):
        with column:
            st.html(
                dedent(
                    f"""
                    <article class="seda-decision-card">
                      <div class="seda-decision-index">{html.escape(index)}</div>
                      <div class="seda-decision-title">{html.escape(title)}</div>
                      <p>{html.escape(message)}</p>
                      <div class="seda-decision-source">{html.escape(source)}</div>
                    </article>
                    """
                ).strip()
            )


def render_relationships_view(report: Any, filename: str | None) -> None:
    """Renderiza la experiencia completa de relaciones."""
    if report is None:
        st.info("Primero debes analizar un archivo.")
        return

    st.markdown(
        '<div class="seda-eyebrow">Relaciones entre variables</div>',
        unsafe_allow_html=True,
    )
    st.title("Relaciones entre variables")

    available_methods = [
        method
        for method in ("pearson", "spearman")
        if method in report.correlations
    ]
    if not available_methods:
        _render_empty_state(
            "No fue posible comparar variables numéricas.",
            (
                "El análisis de relaciones requiere al menos dos columnas numéricas."
            ),
        )
        with st.expander("Requisito para el análisis de relaciones"):
            st.write(
                "Una relación compara cómo cambia un número frente a otro. Con una "
                "sola columna no existe un segundo valor con el cual compararla."
            )
        return

    selected_method = st.radio(
        "Método de lectura",
        options=available_methods,
        format_func=lambda method: METHOD_NAMES.get(method, method.title()),
        horizontal=True,
        key="relationship_method",
        help=(
            "Pearson busca cambios uniformes; Spearman observa la tendencia "
            "general. Ambos métodos usan los mismos datos analizados."
        ),
    )
    result = report.correlations[selected_method]
    strongest = _strongest_value(result.matrix)

    metrics = st.columns(4)
    metrics[0].metric("Variables comparadas", len(result.matrix.columns))
    metrics[1].metric("Relaciones fuertes", len(result.strong_pairs))
    metrics[2].metric(
        "Relación más alta",
        f"{strongest:.2f}" if strongest is not None else "—",
    )
    metrics[3].metric("Diferencias por categoría", len(report.dependencies))

    st.markdown(
        f"""
        <div class="seda-method-note">
          <span>{html.escape(METHOD_NAMES.get(selected_method, selected_method.title()))}</span>
          <p>{html.escape(METHOD_EXPLANATIONS[selected_method])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="seda-section-heading">Relaciones identificadas</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          Se muestran los pares cuyo índice absoluto es 0.70 o superior. Cuanto
          más cerca esté de 1 o −1, más consistente es el patrón.
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_relationship_cards(result)

    st.markdown(
        '<div class="seda-section-heading">Mapa completo de relaciones</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          Cada cuadro compara dos variables. Los tonos dorados indican que suelen
          moverse en el mismo sentido; los naranjas, en sentidos contrarios; y los
          oscuros, que no existe un patrón claro.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        build_correlation_heatmap(result),
        width="stretch",
        config={"displayModeBar": False, "responsive": True},
    )
    st.caption(
        "La diagonal siempre vale 1.00 porque compara cada variable consigo misma."
    )

    with st.expander("Métodos de correlación"):
        first_col, second_col = st.columns(2, gap="large")
        with first_col:
            st.markdown(
                """
                **Pearson**

                Mide la relación lineal entre dos variables numéricas. Los valores
                extremos pueden influir en el resultado.
                """
            )
        with second_col:
            st.markdown(
                """
                **Spearman**

                Mide la relación entre el orden de los valores de dos variables.
                Es adecuado cuando la tendencia no es necesariamente lineal.
                """
            )
    st.markdown(
        '<div class="seda-section-heading">Diferencias entre categorías</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          Esta sección compara variables como región, tipo o grupo con variables
          numéricas. El porcentaje indica cuánto cambian los valores entre las
          distintas categorías; no implica causalidad.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if report.dependencies:
        dependency_copy, dependency_chart = st.columns([1, 1.25], gap="large")
        with dependency_copy:
            _render_dependency_cards(report.dependencies)
        with dependency_chart:
            st.plotly_chart(
                build_dependency_chart(report.dependencies),
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )
    else:
        _render_empty_state(
            "No encontramos diferencias relevantes entre categorías.",
            (
                "Puede que el archivo no tenga variables categóricas o que sus "
                "grupos presenten valores numéricos bastante parecidos."
            ),
        )
