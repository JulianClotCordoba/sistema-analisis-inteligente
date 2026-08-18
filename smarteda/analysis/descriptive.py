"""Estadística descriptiva básica (parte de Rachel).

Implementa el contrato `DescriptiveStatsProvider` definido en `smarteda.models`,
de modo que el motor lo invoque automáticamente::

    from smarteda import AnalysisEngine, BasicDescriptiveStats

    engine = AnalysisEngine(descriptive_provider=BasicDescriptiveStats())
    report = engine.analyze("data/samples/clientes.csv")
    report.descriptive.statistics["edad"]["media"]

Para cada columna numérica del perfil se calculan las medidas clásicas de
tendencia central, dispersión, posición y forma. Todos los valores se devuelven
como `float` nativos de Python (no tipos de numpy) para que el resultado sea
serializable por el frontend. Si un estadístico no se puede calcular (columna
vacía, un solo registro, etc.) se devuelve `nan` en lugar de lanzar un error:
el reporte nunca debe romperse por una columna problemática.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from ..logger import get_logger
from ..models import ClusteringResult, DatasetProfile, DescriptiveResult

logger = get_logger(__name__)

# Nombres (en español) de los estadísticos que se calculan por columna numérica.
# El orden fija la forma del diccionario que consume el frontend.
# Cuántas desviaciones típicas debe alejarse la media de un segmento respecto a
# la media general para considerarla un rasgo distintivo.
_RASGO_MARCADO = 1.0
_RASGO_LEVE = 0.35
# Porcentaje a partir del cual se considera que una categoría "predomina".
_CATEGORIA_DOMINANTE = 50.0

_STAT_NAMES: tuple[str, ...] = (
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
)


class BasicDescriptiveStats:
    """Proveedor de estadística descriptiva para el motor de análisis.

    Cumple el `Protocol` `DescriptiveStatsProvider`: basta con pasar una
    instancia al motor mediante `AnalysisEngine(descriptive_provider=...)`.
    """

    def compute(self, df: pd.DataFrame, profile: DatasetProfile) -> DescriptiveResult:
        """Calcula los estadísticos de todas las columnas numéricas.

        Args:
            df: DataFrame ya cargado y limpiado por el motor.
            profile: Perfil del dataset, del que se toman las columnas numéricas.

        Returns:
            Un `DescriptiveResult` cuyo campo `statistics` tiene la forma
            `{nombre_columna: {"media": ..., "mediana": ...}}`. Si el dataset no
            tiene columnas numéricas, el diccionario viene vacío.
        """
        statistics: dict[str, dict[str, float]] = {}
        for name in profile.numeric_columns:
            if name not in df.columns:
                logger.warning("Columna numérica '%s' ausente del DataFrame.", name)
                continue
            statistics[name] = self._column_statistics(df[name])

        logger.info(
            "Estadística descriptiva calculada para %d columna(s) numérica(s).",
            len(statistics),
        )
        return DescriptiveResult(statistics=statistics)

    def categorical_summary(
        self, df: pd.DataFrame, profile: DatasetProfile
    ) -> dict[str, dict[str, Any]]:
        """Resume las columnas categóricas y booleanas del dataset.

        Va aparte de `compute()` porque `DescriptiveResult.statistics` está
        tipado como `dict[str, dict[str, float]]` y estos valores incluyen texto:
        meterlos ahí rompería el contrato que ya consume el frontend.

        Args:
            df: DataFrame ya cargado y limpiado por el motor.
            profile: Perfil del dataset, del que se toman las columnas
                categóricas y booleanas.

        Returns:
            `{nombre_columna: {"categorias_unicas": int,
            "categoria_mas_frecuente": Any | None, "frecuencia": int,
            "porcentaje": float}}`. El porcentaje se calcula sobre los valores
            no nulos de la columna.
        """
        summary: dict[str, dict[str, Any]] = {}
        for name in profile.categorical_columns + profile.boolean_columns:
            if name not in df.columns:
                logger.warning("Columna categórica '%s' ausente del DataFrame.", name)
                continue
            summary[name] = self._column_summary(df[name])

        logger.info("Resumen categórico calculado para %d columna(s).", len(summary))
        return summary

    def segment_profiles(
        self,
        df: pd.DataFrame,
        profile: DatasetProfile,
        clustering: ClusteringResult | None,
    ) -> list[dict[str, Any]]:
        """Describe cada segmento del clustering: qué tienen en común sus registros.

        El agrupamiento dice *qué* registros van juntos, pero no *por qué*. Este
        método compara la media de cada grupo con la media general del dataset y
        traduce esa diferencia a una lectura en español, para que la
        segmentación se pueda interpretar sin saber estadística.

        Args:
            df: DataFrame ya cargado y limpiado por el motor.
            profile: Perfil del dataset (aporta las columnas categóricas).
            clustering: Resultado del agrupamiento, o None si no se pudo hacer.

        Returns:
            Una lista de diccionarios, uno por segmento y en orden de etiqueta
            (los registros sin grupo de DBSCAN van al final), con su tamaño, sus
            rasgos numéricos distintivos, sus categorías dominantes y una
            descripción ya redactada. Lista vacía si no hay agrupamiento.
        """
        if clustering is None or clustering.n_clusters == 0:
            return []

        labels = np.asarray(clustering.labels)
        if len(labels) != len(df):
            logger.warning(
                "Etiquetas (%d) y filas (%d) no coinciden: se omiten los perfiles.",
                len(labels),
                len(df),
            )
            return []

        numericas = [col for col in clustering.features_used if col in df.columns]
        categoricas = [
            col
            for col in profile.categorical_columns + profile.boolean_columns
            if col in df.columns
        ]
        # Media y desviación generales: son la vara con la que se compara cada grupo.
        referencia = {
            col: (self._to_float(df[col].mean()), self._to_float(df[col].std()))
            for col in numericas
        }
        total = int(len(df))

        perfiles: list[dict[str, Any]] = []
        # Los sin grupo (-1) van al final para no romper la numeración.
        for label in sorted(set(labels.tolist()), key=lambda x: (x == -1, x)):
            grupo = df[labels == label]
            tamano = int(len(grupo))
            porcentaje = float(tamano / total * 100) if total else 0.0
            rasgos = self._segment_traits(grupo, numericas, referencia)
            categorias = self._segment_categories(grupo, categoricas)
            perfiles.append(
                {
                    "segmento": int(label),
                    "nombre": "Sin grupo" if label == -1 else f"Segmento {label + 1}",
                    "tamano": tamano,
                    "porcentaje": porcentaje,
                    "rasgos": rasgos,
                    "categorias": categorias,
                    "descripcion": self._segment_description(
                        tamano, porcentaje, rasgos, categorias
                    ),
                }
            )

        logger.info("Perfiles de segmento calculados: %d", len(perfiles))
        return perfiles

    # ----------------------------- helpers -----------------------------

    def _column_statistics(self, series: pd.Series) -> dict[str, float]:
        """Estadísticos de una sola columna numérica."""
        # `to_numeric` es una red de seguridad: si llegara un valor no numérico
        # se convierte en NaN y se cuenta como faltante, en vez de romper.
        valores = pd.to_numeric(series, errors="coerce").dropna()
        total = int(len(series))
        conteo = int(len(valores))
        if conteo == 0:
            return self._empty_statistics(total)

        minimo = valores.min()
        maximo = valores.max()
        q1 = valores.quantile(0.25)
        q3 = valores.quantile(0.75)
        moda = valores.mode()

        return {
            "media": self._to_float(valores.mean()),
            "mediana": self._to_float(valores.median()),
            # `mode()` puede devolver varios valores; se toma el menor.
            "moda": self._to_float(moda.iloc[0]) if not moda.empty else float("nan"),
            "desviacion_estandar": self._to_float(valores.std()),
            "varianza": self._to_float(valores.var()),
            "minimo": self._to_float(minimo),
            "maximo": self._to_float(maximo),
            "rango": self._to_float(maximo - minimo),
            "q1": self._to_float(q1),
            "q3": self._to_float(q3),
            "iqr": self._to_float(q3 - q1),
            "conteo": float(conteo),
            "faltantes": float(total - conteo),
            "asimetria": self._to_float(valores.skew()),
            "curtosis": self._to_float(valores.kurtosis()),
        }

    def _column_summary(self, series: pd.Series) -> dict[str, Any]:
        """Resumen de una sola columna categórica o booleana."""
        valores = series.dropna()
        conteo = int(len(valores))
        if conteo == 0:
            return {
                "categorias_unicas": 0,
                "categoria_mas_frecuente": None,
                "frecuencia": 0,
                "porcentaje": 0.0,
            }

        frecuencias = valores.value_counts()
        dominante = frecuencias.index[0]
        frecuencia = int(frecuencias.iloc[0])
        return {
            "categorias_unicas": int(valores.nunique()),
            "categoria_mas_frecuente": self._to_native(dominante),
            "frecuencia": frecuencia,
            "porcentaje": float(frecuencia / conteo * 100),
        }

    def _segment_traits(
        self,
        grupo: pd.DataFrame,
        columnas: list[str],
        referencia: dict[str, tuple[float, float]],
    ) -> list[dict[str, Any]]:
        """Rasgos numéricos que separan al grupo del promedio general.

        La diferencia se expresa en desviaciones típicas para que variables con
        escalas distintas (edad e ingreso, por ejemplo) sean comparables entre sí.
        """
        rasgos: list[dict[str, Any]] = []
        for col in columnas:
            media_general, desviacion = referencia[col]
            media = self._to_float(grupo[col].mean())
            if math.isnan(media) or math.isnan(media_general):
                continue
            if math.isnan(desviacion) or desviacion == 0:
                diferencia = 0.0
            else:
                diferencia = (media - media_general) / desviacion
            rasgos.append(
                {
                    "variable": col,
                    "media": media,
                    "media_general": media_general,
                    "diferencia": float(diferencia),
                    "lectura": self._trait_reading(diferencia),
                }
            )
        # Primero los rasgos más marcados: son los que explican el grupo.
        rasgos.sort(key=lambda r: abs(r["diferencia"]), reverse=True)
        return rasgos

    def _segment_categories(
        self, grupo: pd.DataFrame, columnas: list[str]
    ) -> list[dict[str, Any]]:
        """Categoría más repetida dentro del grupo, por cada columna categórica."""
        categorias: list[dict[str, Any]] = []
        for col in columnas:
            valores = grupo[col].dropna()
            if valores.empty:
                continue
            frecuencias = valores.value_counts()
            categorias.append(
                {
                    "variable": col,
                    "categoria": self._to_native(frecuencias.index[0]),
                    "porcentaje": float(frecuencias.iloc[0] / len(valores) * 100),
                }
            )
        categorias.sort(key=lambda c: c["porcentaje"], reverse=True)
        return categorias

    def _segment_description(
        self,
        tamano: int,
        porcentaje: float,
        rasgos: list[dict[str, Any]],
        categorias: list[dict[str, Any]],
    ) -> str:
        """Redacta en español lo que caracteriza al segmento."""
        partes = [f"{tamano:,} registros ({porcentaje:.1f}% del total)."]

        distintivos = [r for r in rasgos if r["lectura"] != "en el promedio"][:2]
        if distintivos:
            frases = [
                f"{r['variable'].replace('_', ' ')} {r['lectura']} del promedio "
                f"({self._format_number(r['media'])} frente a "
                f"{self._format_number(r['media_general'])})"
                for r in distintivos
            ]
            partes.append("Se distingue por " + " y ".join(frases) + ".")
        else:
            partes.append("Sus valores se mantienen cerca del promedio general.")

        dominante = next(
            (c for c in categorias if c["porcentaje"] >= _CATEGORIA_DOMINANTE), None
        )
        if dominante is not None:
            partes.append(
                f"En {dominante['variable'].replace('_', ' ')} predomina "
                f"{self._category_label(dominante['categoria'])} "
                f"({dominante['porcentaje']:.0f}%)."
            )
        return " ".join(partes)

    @staticmethod
    def _category_label(categoria: Any) -> str:
        """Texto legible de una categoría (las booleanas se leen sí/no)."""
        if isinstance(categoria, bool):
            return "sí" if categoria else "no"
        return str(categoria)

    @staticmethod
    def _trait_reading(diferencia: float) -> str:
        """Traduce la diferencia en desviaciones típicas a lenguaje corriente."""
        if diferencia >= _RASGO_MARCADO:
            return "muy por encima"
        if diferencia >= _RASGO_LEVE:
            return "por encima"
        if diferencia <= -_RASGO_MARCADO:
            return "muy por debajo"
        if diferencia <= -_RASGO_LEVE:
            return "por debajo"
        return "en el promedio"

    @staticmethod
    def _format_number(valor: float) -> str:
        """Formato legible: sin decimales en cifras grandes, con dos en pequeñas."""
        return f"{valor:,.0f}" if abs(valor) >= 1000 else f"{valor:,.2f}"

    @staticmethod
    def _empty_statistics(total: int) -> dict[str, float]:
        """Estadísticos de una columna sin ningún valor utilizable."""
        vacio = {name: float("nan") for name in _STAT_NAMES}
        vacio["conteo"] = 0.0
        vacio["faltantes"] = float(total)
        return vacio

    @staticmethod
    def _to_float(value: Any) -> float:
        """Convierte a `float` nativo; devuelve `nan` si no es posible."""
        try:
            if pd.isna(value):
                return float("nan")
            return float(value)
        except (TypeError, ValueError):
            return float("nan")

    @staticmethod
    def _to_native(value: Any) -> Any:
        """Convierte tipos de numpy/pandas a tipos nativos serializables."""
        if hasattr(value, "item"):
            try:
                return value.item()
            except (ValueError, AttributeError):
                return str(value)
        return value
