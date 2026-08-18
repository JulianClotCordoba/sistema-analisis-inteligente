"""Pruebas de la estadística descriptiva básica (parte de Rachel)."""

from __future__ import annotations

import math
from io import BytesIO

import numpy as np
import pandas as pd
import pytest
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

from app.reporting import generate_pdf_report
from app.segments import build_segment_profile_table
from smarteda import AnalysisConfig, AnalysisEngine, BasicDescriptiveStats
from smarteda.analysis.clustering import run_clustering
from smarteda.__main__ import main as cli_main
from smarteda.models import DatasetProfile, DescriptiveStatsProvider
from smarteda.profiling import DataProfiler


def _statistics(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Atajo: perfila el DataFrame y devuelve el diccionario de estadísticos."""
    profile = DataProfiler().profile(df)
    return BasicDescriptiveStats().compute(df, profile).statistics


def test_cumple_el_contrato_del_motor():
    assert isinstance(BasicDescriptiveStats(), DescriptiveStatsProvider)


def test_media_mediana_y_desviacion_correctas():
    # Valores verificables a mano: media = 3, mediana = 3,
    # varianza muestral = 10/4 = 2.5, desviación = sqrt(2.5).
    df = pd.DataFrame({"valor": [1.0, 2.0, 3.0, 4.0, 5.0]})
    stats = _statistics(df)["valor"]

    assert stats["media"] == pytest.approx(3.0)
    assert stats["mediana"] == pytest.approx(3.0)
    assert stats["varianza"] == pytest.approx(2.5)
    assert stats["desviacion_estandar"] == pytest.approx(math.sqrt(2.5))


def test_posicion_rango_y_moda_correctos():
    # Nueve valores ordenados: los cuartiles caen justo sobre un dato, sin
    # interpolar. Q1 = 3.er valor = 4, Q3 = 7.º valor = 7, IQR = 3, moda = 4.
    df = pd.DataFrame({"valor": [2.0, 4.0, 4.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]})
    stats = _statistics(df)["valor"]

    assert stats["minimo"] == pytest.approx(2.0)
    assert stats["maximo"] == pytest.approx(9.0)
    assert stats["rango"] == pytest.approx(7.0)
    assert stats["moda"] == pytest.approx(4.0)
    assert stats["q1"] == pytest.approx(4.0)
    assert stats["q3"] == pytest.approx(7.0)
    assert stats["iqr"] == pytest.approx(3.0)


def test_todos_los_valores_son_float_nativos(mixed_df):
    stats = _statistics(mixed_df)
    for medidas in stats.values():
        # `type(...) is float` descarta np.float64, que sí pasaría isinstance.
        assert all(type(valor) is float for valor in medidas.values())


def test_columnas_categoricas_no_aparecen_en_statistics(mixed_df):
    stats = _statistics(mixed_df)

    assert set(stats) == {"edad", "ingreso"}
    assert "region" not in stats
    assert "activo" not in stats
    assert "fecha" not in stats


def test_conteo_y_faltantes_de_columna_con_nulos(mixed_df):
    # 'ingreso' tiene 6 filas, una de ellas NaN.
    stats = _statistics(mixed_df)["ingreso"]

    assert stats["conteo"] == 5.0
    assert stats["faltantes"] == 1.0
    # La media ignora el faltante: (1000 + 2000 + 1500 + 5000 + 1800) / 5.
    assert stats["media"] == pytest.approx(2260.0)


def test_columna_constante_no_rompe():
    df = pd.DataFrame({"constante": [7.0, 7.0, 7.0, 7.0]})
    stats = _statistics(df)["constante"]

    assert stats["desviacion_estandar"] == 0.0
    assert stats["varianza"] == 0.0
    assert stats["rango"] == 0.0
    assert stats["iqr"] == 0.0
    assert stats["media"] == pytest.approx(7.0)


def test_columna_con_un_solo_registro_no_rompe():
    df = pd.DataFrame({"valor": [42.0]})
    stats = _statistics(df)["valor"]

    assert stats["conteo"] == 1.0
    assert stats["media"] == pytest.approx(42.0)
    # Sin dispersión posible con un solo dato: nan en vez de excepción.
    assert math.isnan(stats["desviacion_estandar"])


def test_columna_totalmente_nula_devuelve_nan():
    # El perfilador marca las columnas vacías como UNKNOWN, así que se fuerza
    # el caso para comprobar que el módulo lo soporta igualmente.
    df = pd.DataFrame({"vacia": [np.nan, np.nan, np.nan]})
    profile = DatasetProfile(n_rows=3, n_cols=1, columns=[], numeric_columns=["vacia"])
    stats = BasicDescriptiveStats().compute(df, profile).statistics["vacia"]

    assert stats["conteo"] == 0.0
    assert stats["faltantes"] == 3.0
    assert math.isnan(stats["media"])
    assert math.isnan(stats["moda"])


def test_todas_las_columnas_tienen_las_mismas_medidas():
    df = pd.DataFrame({"valor": [1.0, 2.0, 3.0]})
    profile = DatasetProfile(
        n_rows=3, n_cols=1, columns=[], numeric_columns=["valor", "inexistente"]
    )
    completa = BasicDescriptiveStats().compute(df, profile).statistics["valor"]
    vacia = _statistics(pd.DataFrame({"valor": [np.nan]}))

    # La columna inexistente se ignora sin lanzar error.
    assert set(completa) == {
        "media",
        "mediana",
        "moda",
        "desviacion_estandar",
        "varianza",
        "minimo",
        "maximo",
        "rango",
        "q1",
        "q3",
        "iqr",
        "conteo",
        "faltantes",
        "asimetria",
        "curtosis",
    }
    assert vacia == {}


def test_dataset_sin_columnas_numericas_devuelve_vacio():
    df = pd.DataFrame({"region": ["Norte", "Sur", "Norte", "Sur"]})
    result = BasicDescriptiveStats().compute(df, DataProfiler().profile(df))

    assert result.statistics == {}


def test_categorical_summary_identifica_la_categoria_dominante(mixed_df):
    profile = DataProfiler().profile(mixed_df)
    resumen = BasicDescriptiveStats().categorical_summary(mixed_df, profile)

    # 'region': Norte x3, Sur x2, Centro x1 sobre 6 filas.
    region = resumen["region"]
    assert region["categorias_unicas"] == 3
    assert region["categoria_mas_frecuente"] == "Norte"
    assert region["frecuencia"] == 3
    assert region["porcentaje"] == pytest.approx(50.0)

    # También cubre las booleanas y deja fuera las numéricas.
    assert "activo" in resumen
    assert "edad" not in resumen


def test_categorical_summary_con_columna_vacia():
    df = pd.DataFrame({"categoria": [None, None, None]})
    profile = DatasetProfile(
        n_rows=3, n_cols=1, columns=[], categorical_columns=["categoria"]
    )
    resumen = BasicDescriptiveStats().categorical_summary(df, profile)["categoria"]

    assert resumen["categorias_unicas"] == 0
    assert resumen["categoria_mas_frecuente"] is None
    assert resumen["frecuencia"] == 0
    assert resumen["porcentaje"] == 0.0


def test_integracion_con_el_motor(tmp_path, mixed_df):
    """El motor llena `report.descriptive` al recibir el proveedor."""
    path = tmp_path / "datos.csv"
    mixed_df.to_csv(path, index=False)

    engine = AnalysisEngine(descriptive_provider=BasicDescriptiveStats())
    report = engine.analyze(path)

    assert report.descriptive is not None
    assert set(report.descriptive.statistics) == {"edad", "ingreso"}
    assert report.descriptive.statistics["edad"]["media"] == pytest.approx(
        mixed_df["edad"].mean()
    )


# ------------------- perfil de cada segmento (clustering) -------------------


def _clustering_de(df):
    """Analiza un DataFrame en memoria y devuelve (perfil, clustering)."""
    engine = AnalysisEngine()
    profile = DataProfiler().profile(df)
    matriz, features = engine.preprocessor.feature_matrix(df, profile)
    return profile, run_clustering(matriz, features, engine.config)


def test_segment_profiles_describe_cada_grupo(clustered_df):
    profile, clustering = _clustering_de(clustered_df)
    perfiles = BasicDescriptiveStats().segment_profiles(
        clustered_df, profile, clustering
    )

    assert len(perfiles) == clustering.n_clusters
    # Los tamaños cuadran con los que reportó el motor.
    assert sum(p["tamano"] for p in perfiles) == len(clustered_df)
    assert {p["segmento"]: p["tamano"] for p in perfiles} == clustering.cluster_sizes
    assert sum(p["porcentaje"] for p in perfiles) == pytest.approx(100.0)
    for p in perfiles:
        assert p["descripcion"]
        assert p["rasgos"]


def test_segment_profiles_detecta_el_rasgo_dominante():
    # Dos grupos separados solo por 'valor': uno queda encima y otro debajo.
    rng = np.random.default_rng(7)
    df = pd.DataFrame(
        {
            "valor": np.concatenate([rng.normal(1, 0.1, 20), rng.normal(100, 0.1, 20)]),
            "otro": [5.0] * 40,
            "grupo": ["bajo"] * 20 + ["alto"] * 20,
        }
    )
    profile, clustering = _clustering_de(df)
    perfiles = BasicDescriptiveStats().segment_profiles(df, profile, clustering)

    principales = [p["rasgos"][0] for p in perfiles]
    # 'otro' es constante: no puede ser el rasgo que explica ningún grupo.
    assert all(r["variable"] == "valor" for r in principales)
    encima = [r for r in principales if r["diferencia"] > 0]
    debajo = [r for r in principales if r["diferencia"] < 0]
    assert len(encima) == 1 and len(debajo) == 1
    assert "por encima" in encima[0]["lectura"]
    assert "por debajo" in debajo[0]["lectura"]
    # Cada grupo es puro respecto a la categórica, y así se refleja.
    for p in perfiles:
        assert p["categorias"][0]["porcentaje"] == pytest.approx(100.0)
        assert "predomina" in p["descripcion"]


def test_segment_profiles_sin_clustering_devuelve_vacio(mixed_df):
    profile = DataProfiler().profile(mixed_df)
    assert BasicDescriptiveStats().segment_profiles(mixed_df, profile, None) == []


def test_segment_profiles_ignora_etiquetas_desalineadas(clustered_df):
    profile, clustering = _clustering_de(clustered_df)
    # Menos filas que etiquetas: no debe romper, solo omitir el perfilado.
    recortado = clustered_df.head(10)
    assert BasicDescriptiveStats().segment_profiles(recortado, profile, clustering) == []


def test_segment_profiles_marca_los_registros_sin_grupo(clustered_df):
    config = AnalysisConfig(clustering_algorithm="dbscan")
    engine = AnalysisEngine(config)
    profile = DataProfiler().profile(clustered_df)
    matriz, features = engine.preprocessor.feature_matrix(clustered_df, profile)
    clustering = run_clustering(matriz, features, config)
    perfiles = BasicDescriptiveStats().segment_profiles(
        clustered_df, profile, clustering
    )

    nombres = [p["nombre"] for p in perfiles]
    assert nombres[0] == "Segmento 1"
    if -1 in clustering.cluster_sizes:
        # Los sin grupo se describen igual, pero al final de la lista.
        assert nombres[-1] == "Sin grupo"
        assert perfiles[-1]["segmento"] == -1


def test_la_tabla_de_perfiles_incluye_la_fila_general(clustered_df):
    profile, clustering = _clustering_de(clustered_df)
    perfiles = BasicDescriptiveStats().segment_profiles(
        clustered_df, profile, clustering
    )
    tabla = build_segment_profile_table(perfiles, clustering.features_used)

    assert list(tabla["Segmento"])[-1] == "General"
    assert list(tabla.columns)[:3] == ["Segmento", "Registros", "% del total"]
    assert list(tabla["Registros"])[-1] == len(clustered_df)


def test_la_tabla_de_perfiles_admite_una_lista_vacia():
    # Sin segmentos no hay tabla, pero tampoco excepción.
    assert build_segment_profile_table([], []).empty


def test_la_pantalla_de_segmentos_explica_los_grupos():
    """La vista de Segmentos muestra la tabla de perfiles y una frase por grupo."""
    app = AppTest.from_file("app/main.py", default_timeout=25).run()
    next(b for b in app.button if b.label == "Usar datos de ejemplo").click().run(
        timeout=40
    )
    next(b for b in app.button if b.label == "04  Segmentos").click().run(timeout=40)

    assert not app.exception
    tablas = [element.value for element in app.dataframe]
    perfiles = [t for t in tablas if "Categoría dominante" in t.columns]
    assert len(perfiles) == 1
    assert "General" in list(perfiles[0]["Segmento"])

    textos = " ".join(str(element.value) for element in app.markdown)
    assert "Qué distingue a cada segmento" in textos
    assert "Se distingue por" in textos or "promedio general" in textos


# --------- integración con la aplicación, el PDF y la consola ---------


def test_la_pantalla_de_resumen_muestra_la_estadistica():
    """La app pasa el proveedor al motor y pinta la tabla descriptiva."""
    app = AppTest.from_file("app/main.py", default_timeout=25).run()
    boton = next(
        button for button in app.button if button.label == "Usar datos de ejemplo"
    )
    boton.click().run(timeout=40)

    assert not app.exception
    tablas = [element.value for element in app.dataframe]
    descriptiva = [t for t in tablas if "Media" in t.columns]
    assert len(descriptiva) == 1
    assert "edad" in list(descriptiva[0]["Variable"])

    categorica = [t for t in tablas if "Más frecuente" in t.columns]
    assert len(categorica) == 1
    assert "region" in list(categorica[0]["Variable"])
    # Las booleanas se leen Sí / No, no True / False.
    activo = categorica[0].set_index("Variable").loc["cliente_activo"]
    assert activo["Más frecuente"] == "Sí"


def test_el_pdf_incluye_la_estadistica_descriptiva():
    engine = AnalysisEngine(descriptive_provider=BasicDescriptiveStats())
    report = engine.analyze("data/samples/clientes.csv")
    pdf = generate_pdf_report(report, "clientes.csv")

    reader = PdfReader(BytesIO(pdf))
    texto = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Estadística descriptiva disponible" in texto
    assert "Media" in texto


def test_la_consola_imprime_la_estadistica_descriptiva(capsys):
    assert cli_main(["data/samples/clientes.csv"]) == 0

    salida = capsys.readouterr().out
    assert "ESTADÍSTICA DESCRIPTIVA" in salida
    assert "edad: media=" in salida
