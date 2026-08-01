"""Pantalla de segmentos construida a partir del contrato público de SmartEDA."""

from __future__ import annotations

import html
from textwrap import dedent
from typing import Any

import numpy as np
import plotly.graph_objects as go
import streamlit as st


SEGMENT_COLORS = [
    "#E4AD3A",
    "#D8783E",
    "#8FA278",
    "#D7C57C",
    "#A779B5",
    "#68A7A1",
    "#C66E71",
    "#7F91C7",
    "#B79265",
    "#9B9D92",
]


def _humanize(value: Any) -> str:
    return str(value).replace("_", " ").strip().capitalize()


def _algorithm_name(value: str) -> str:
    return "K-Means" if value.lower() == "kmeans" else "DBSCAN"


def _quality_details(score: float | None) -> tuple[str, str, str]:
    """Traduce silhouette a una lectura que no requiere conocimientos técnicos."""
    if score is None:
        return (
            "No evaluable",
            "Exploratorio",
            (
                "No fue posible calcular una puntuación comparable. Esto suele "
                "ocurrir cuando solo se forma un grupo útil o quedan muy pocos datos."
            ),
        )
    if score >= 0.5:
        return (
            "Buena",
            "Grupos claros",
            (
                "Los registros de un mismo segmento se parecen entre sí y se "
                "distinguen razonablemente de los demás."
            ),
        )
    if score >= 0.25:
        return (
            "Moderada",
            "Hay mezcla",
            (
                "Los grupos muestran una estructura útil, aunque algunos registros "
                "podrían encajar en más de un segmento."
            ),
        )
    return (
        "Baja",
        "Grupos poco definidos",
        (
            "La separación es débil. Conviene usar estos segmentos como una primera "
            "hipótesis y no como una clasificación definitiva."
        ),
    )


def _segment_items(result: Any) -> list[tuple[int, int]]:
    return sorted(
        (
            (int(label), int(size))
            for label, size in result.cluster_sizes.items()
            if int(label) != -1
        ),
        key=lambda item: (-item[1], item[0]),
    )


def _noise_count(result: Any) -> int:
    return int(result.cluster_sizes.get(-1, 0))


def build_segment_scatter(result: Any) -> go.Figure:
    """Dibuja la proyección 2D que ya calculó el backend."""
    projection = np.asarray(result.projection_2d)
    labels = np.asarray(result.labels)
    figure = go.Figure()

    for color_index, (label, _) in enumerate(_segment_items(result)):
        mask = labels == label
        point_indexes = np.flatnonzero(mask) + 1
        figure.add_trace(
            go.Scatter(
                x=projection[mask, 0],
                y=projection[mask, 1],
                mode="markers",
                name=f"Segmento {label + 1}",
                customdata=point_indexes,
                marker={
                    "size": 9,
                    "color": SEGMENT_COLORS[color_index % len(SEGMENT_COLORS)],
                    "opacity": 0.82,
                    "line": {"color": "#10120E", "width": 0.8},
                },
                hovertemplate=(
                    f"<b>Segmento {label + 1}</b><br>"
                    "Registro procesado: %{customdata}<br>"
                    "Vista 1: %{x:.2f}<br>Vista 2: %{y:.2f}<extra></extra>"
                ),
            )
        )

    noise_mask = labels == -1
    if noise_mask.any():
        point_indexes = np.flatnonzero(noise_mask) + 1
        figure.add_trace(
            go.Scatter(
                x=projection[noise_mask, 0],
                y=projection[noise_mask, 1],
                mode="markers",
                name="Sin segmento",
                customdata=point_indexes,
                marker={
                    "size": 10,
                    "color": "#77786F",
                    "symbol": "x",
                    "opacity": 0.9,
                    "line": {"width": 1.4},
                },
                hovertemplate=(
                    "<b>Sin segmento</b><br>"
                    "Registro procesado: %{customdata}<br>"
                    "DBSCAN no encontró vecinos suficientemente parecidos."
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        height=520,
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


def build_segment_size_chart(result: Any) -> go.Figure:
    """Compara cuántos registros contiene cada grupo."""
    items = _segment_items(result)
    names = [f"Segmento {label + 1}" for label, _ in items]
    values = [size for _, size in items]
    colors = [SEGMENT_COLORS[index % len(SEGMENT_COLORS)] for index in range(len(items))]

    noise = _noise_count(result)
    if noise:
        names.append("Sin segmento")
        values.append(noise)
        colors.append("#77786F")

    figure = go.Figure(
        go.Bar(
            x=names,
            y=values,
            marker={"color": colors, "line": {"color": "#F1CB70", "width": 0.5}},
            text=values,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>%{y} registros<extra></extra>",
        )
    )
    figure.update_layout(
        height=330,
        margin={"l": 20, "r": 15, "t": 25, "b": 45},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#F1ECDD"},
        showlegend=False,
        xaxis={"showgrid": False, "zeroline": False},
        yaxis={
            "title": "Registros",
            "gridcolor": "#24251F",
            "zeroline": False,
            "rangemode": "tozero",
        },
    )
    return figure


def _render_empty_state(title: str, message: str) -> None:
    st.html(
        dedent(
            f"""
            <div class="seda-empty-state">
              <div class="seda-empty-kicker">Sin segmentos disponibles</div>
              <div class="seda-empty-title">{html.escape(title)}</div>
              <div class="seda-empty-copy">{html.escape(message)}</div>
            </div>
            """
        ).strip()
    )


def _render_segment_cards(result: Any, total: int) -> None:
    items = _segment_items(result)
    if not items:
        return

    columns = st.columns(min(3, len(items)), gap="small")
    largest = max(size for _, size in items)
    smallest = min(size for _, size in items)
    for index, (label, size) in enumerate(items):
        percentage = size / total * 100 if total else 0
        if size == largest and largest != smallest:
            note = "Es el grupo con mayor representación."
        elif size == smallest and largest != smallest:
            note = "Es el grupo más pequeño; evita ignorarlo por su tamaño."
        else:
            note = "Tiene una representación intermedia dentro del conjunto."
        with columns[index % len(columns)]:
            st.html(
                dedent(
                    f"""
                    <article class="seda-segment-card">
                      <div class="seda-segment-number">SEGMENTO {label + 1:02d}</div>
                      <div class="seda-segment-count">{size:,}</div>
                      <div class="seda-segment-percentage">{percentage:.1f}% del total</div>
                      <div class="seda-segment-bar">
                        <span style="width:{min(percentage, 100):.1f}%"></span>
                      </div>
                      <p>{html.escape(note)}</p>
                    </article>
                    """
                ).strip()
            )

    noise = _noise_count(result)
    if noise:
        percentage = noise / total * 100 if total else 0
        st.html(
            dedent(
                f"""
                <article class="seda-noise-card">
                  <div>
                    <div class="seda-segment-number">REGISTROS SIN SEGMENTO</div>
                    <div class="seda-noise-title">{noise:,} registros · {percentage:.1f}%</div>
                  </div>
                  <p>
                    DBSCAN los dejó fuera porque no encontró suficientes registros
                    cercanos y parecidos. No significa que sean errores: conviene
                    revisarlos como casos especiales.
                  </p>
                </article>
                """
            ).strip()
        )


def _decision_guidance(result: Any, total: int) -> list[tuple[str, str, str]]:
    quality, _, _ = _quality_details(result.silhouette)
    items = _segment_items(result)
    noise = _noise_count(result)

    if result.silhouette is not None and result.silhouette >= 0.5:
        first = (
            "Compara resultados por segmento",
            (
                "La separación es buena. Compara indicadores, respuestas o "
                "resultados por grupo antes de aplicar una misma estrategia a todos."
            ),
        )
    else:
        first = (
            "Trátalos como una hipótesis",
            (
                "La separación no es suficientemente clara para automatizar "
                "decisiones. Úsalos para explorar diferencias y valida lo encontrado."
            ),
        )

    largest_size = max((size for _, size in items), default=0)
    largest_share = largest_size / total * 100 if total else 0
    if largest_share >= 60:
        second = (
            "No dejes que el grupo mayor oculte al resto",
            (
                f"El segmento más grande reúne {largest_share:.1f}% de los registros. "
                "Revisa por separado los grupos pequeños antes de usar un promedio general."
            ),
        )
    else:
        second = (
            "Prueba estrategias diferenciadas",
            (
                "Los tamaños permiten comparar grupos sin que uno domine por completo. "
                "Puedes probar mensajes, servicios o procesos distintos y medir resultados."
            ),
        )

    if noise:
        noise_share = noise / total * 100 if total else 0
        third = (
            "Revisa los casos sin segmento",
            (
                f"DBSCAN dejó {noise_share:.1f}% fuera de los grupos. Comprueba si "
                "son casos válidos, perfiles poco frecuentes o datos que requieren revisión."
            ),
        )
    else:
        third = (
            "Ponles significado con información del negocio",
            (
                "El algoritmo encontró similitud, pero no asigna nombres comerciales. "
                "Contrasta cada grupo con sus variables antes de llamarlo, por ejemplo, "
                "“alto valor” o “bajo consumo”."
            ),
        )

    return [
        ("01 / COMPARAR", first[0], first[1]),
        ("02 / EQUILIBRIO", second[0], second[1]),
        ("03 / VALIDAR", third[0], third[1]),
    ]


def _render_decision_guidance(result: Any, total: int) -> None:
    columns = st.columns(3, gap="small")
    for column, (index, title, message) in zip(
        columns, _decision_guidance(result, total)
    ):
        with column:
            st.html(
                dedent(
                    f"""
                    <article class="seda-decision-card">
                      <div class="seda-decision-index">{html.escape(index)}</div>
                      <div class="seda-decision-title">{html.escape(title)}</div>
                      <p>{html.escape(message)}</p>
                      <div class="seda-decision-source">Orientación basada en el análisis</div>
                    </article>
                    """
                ).strip()
            )


def _render_method_details(result: Any) -> None:
    algorithm = result.algorithm.lower()
    if algorithm == "kmeans":
        explanation = (
            "K-Means asigna todos los registros al grupo más parecido. El motor "
            "probó distintas cantidades y eligió automáticamente la que produjo "
            "la separación más clara."
        )
        parameter = f"k = {result.params.get('k', result.n_clusters)}"
        parameter_copy = "cantidad de segmentos seleccionada"
    else:
        explanation = (
            "DBSCAN forma grupos donde encuentra suficientes registros cercanos. "
            "Puede dejar algunos fuera cuando no se parecen lo suficiente a sus vecinos."
        )
        eps = result.params.get("eps", "—")
        min_samples = result.params.get("min_samples", "—")
        parameter = f"eps = {eps} · mínimo = {min_samples}"
        parameter_copy = "distancia y vecinos mínimos elegidos por el motor"

    st.html(
        dedent(
            f"""
            <div class="seda-method-note">
              <span>{html.escape(_algorithm_name(result.algorithm))}</span>
              <p>{html.escape(explanation)}</p>
            </div>
            """
        ).strip()
    )
    st.caption(f"Configuración técnica: {parameter} — {parameter_copy}.")


def render_segments_view(report: Any, filename: str | None) -> None:
    """Renderiza la experiencia completa de segmentación."""
    if report is None:
        st.info("Primero debes analizar un archivo.")
        return

    result = report.clustering
    safe_filename = html.escape(str(filename or "Dataset"))
    st.markdown(
        '<div class="seda-eyebrow">Grupos encontrados automáticamente</div>',
        unsafe_allow_html=True,
    )
    st.title("¿Qué tipos de registros aparecen en tus datos?")
    st.markdown(
        """
        <div class="seda-page-lead">
          SmartEDA reúne registros que presentan combinaciones numéricas parecidas.
          Esto permite comparar grupos y adaptar decisiones sin revisar cada fila
          manualmente.
          <strong>Un segmento representa similitud matemática; no es todavía una
          etiqueta comercial ni una explicación de por qué existe.</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result is None:
        _render_empty_state(
            "El motor no pudo crear grupos con este archivo.",
            (
                "Se necesitan suficientes filas y al menos una variable numérica. "
                "Prueba con otro archivo o revisa la estructura en Resumen."
            ),
        )
        return

    total = len(result.labels)
    variables = ", ".join(_humanize(name) for name in result.features_used)
    st.markdown(
        f"""
        <div class="seda-context-line">
          <span>Archivo analizado</span>
          <strong>{safe_filename}</strong>
          <span>{html.escape(_algorithm_name(result.algorithm))}</span>
          <span>{html.escape(variables)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result.n_clusters == 0:
        _render_empty_state(
            "No se formó ningún segmento estable.",
            (
                "DBSCAN consideró que los registros no tenían suficiente cercanía "
                "para formar grupos. Esto también es un resultado útil: evita forzar "
                "segmentos que los datos no respaldan."
            ),
        )
        return

    quality, quality_tag, quality_copy = _quality_details(result.silhouette)
    noise = _noise_count(result)
    largest = max((size for _, size in _segment_items(result)), default=0)

    metrics = st.columns(4)
    metrics[0].metric("Segmentos encontrados", result.n_clusters)
    metrics[1].metric(
        "Calidad de separación",
        quality,
        help="Resume qué tan juntos están los registros de cada grupo y qué tan separados están de los demás.",
    )
    metrics[2].metric(
        "Grupo más grande",
        f"{largest:,}",
        help="Cantidad de registros asignados al segmento con mayor representación.",
    )
    metrics[3].metric("Sin segmento", f"{noise:,}")

    _render_method_details(result)

    st.markdown(
        '<div class="seda-section-heading">Mapa de similitud</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          Cada punto representa un registro procesado. Los puntos cercanos tienen
          combinaciones numéricas parecidas; el color indica el grupo asignado.
          Las posiciones son una vista resumida, no valores originales como edad
          o ingreso.
        </div>
        """,
        unsafe_allow_html=True,
    )
    if result.projection_2d is not None:
        st.plotly_chart(
            build_segment_scatter(result),
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )
    else:
        _render_empty_state(
            "No se puede dibujar el mapa en dos dimensiones.",
            (
                "El análisis sí creó grupos, pero necesita al menos dos variables "
                "numéricas para construir esta vista."
            ),
        )

    quality_class = (
        "seda-quality-good"
        if result.silhouette is not None and result.silhouette >= 0.5
        else "seda-quality-caution"
    )
    score_text = (
        f"{result.silhouette:.2f}" if result.silhouette is not None else "No disponible"
    )
    st.html(
        dedent(
            f"""
            <article class="seda-quality-card {quality_class}">
              <div>
                <div class="seda-quality-kicker">CALIDAD SILHOUETTE · {html.escape(score_text)}</div>
                <div class="seda-quality-title">{html.escape(quality_tag)}</div>
              </div>
              <p>{html.escape(quality_copy)}</p>
            </article>
            """
        ).strip()
    )
    with st.expander("¿Qué significa silhouette sin fórmulas?"):
        st.markdown(
            """
            Imagina que cada segmento es una mesa:

            - Una puntuación **alta** significa que cada persona está sentada cerca
              de quienes se le parecen y lejos de las otras mesas.
            - Una puntuación **media** indica que algunas personas podrían sentarse
              razonablemente en más de una mesa.
            - Una puntuación **baja** avisa que las mesas se mezclan y que no conviene
              tomar decisiones automáticas a partir de esos grupos.

            La puntuación evalúa la separación matemática, no si los segmentos son
            útiles para el negocio. Esa utilidad debe validarse con el contexto.
            """
        )

    st.markdown(
        '<div class="seda-section-heading">Tamaño de los segmentos</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          Revisa cuánto representa cada grupo. Un segmento pequeño no es menos
          importante: puede contener un perfil especializado que un promedio general
          escondería.
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_segment_cards(result, total)
    st.plotly_chart(
        build_segment_size_chart(result),
        width="stretch",
        config={"displayModeBar": False, "responsive": True},
    )

    st.markdown(
        '<div class="seda-section-heading">Cómo usar estos segmentos</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="seda-section-copy">
          Estas recomendaciones convierten la estructura encontrada en próximos
          pasos. Son orientación para investigar y probar, no decisiones automáticas
          sobre personas o registros.
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_decision_guidance(result, total)

    with st.expander("K-Means y DBSCAN explicados de forma sencilla"):
        first, second = st.columns(2, gap="large")
        with first:
            st.markdown(
                """
                **K-Means — todos entran en un grupo**

                Es útil cuando necesitas dividir toda la información en una cantidad
                clara de grupos. Incluso un registro poco común recibirá un segmento.
                """
            )
        with second:
            st.markdown(
                """
                **DBSCAN — solo agrupa donde encuentra cercanía**

                Es útil para descubrir grupos de formas diferentes y separar casos
                aislados. Puede producir pocos grupos o dejar registros sin segmento.
                """
            )
        st.info(
            "Para cambiar el método debes volver a Carga de datos, abrir Opciones "
            "avanzadas y analizar nuevamente el archivo."
        )

    with st.expander("¿Cómo se construyó esta pantalla?"):
        st.markdown(
            """
            El frontend no volvió a ejecutar clustering. Consumió directamente:

            - `report.clustering.algorithm`
            - `report.clustering.labels`
            - `report.clustering.n_clusters`
            - `report.clustering.features_used`
            - `report.clustering.cluster_sizes`
            - `report.clustering.silhouette`
            - `report.clustering.params`
            - `report.clustering.projection_2d`

            El backend de Julián creó los grupos y la proyección. Esta pantalla
            solamente los transforma en indicadores, gráficas y explicaciones.
            Para describir qué caracteriza cada segmento se necesitará que una
            versión futura del backend entregue perfiles o estadísticas por grupo.
            """
        )
