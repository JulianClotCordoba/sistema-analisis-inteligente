"""Motor de análisis: orquesta todo el flujo y expone la API pública.

`AnalysisEngine` es el único objeto que el frontend (Jose) y la integración
(Rachel) necesitan usar. Recibe un archivo y devuelve un `AnalysisReport`
completo. Los análisis opcionales que fallen se registran como advertencia sin
tumbar el reporte entero, para que la aplicación sea robusta en una demo.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import pandas as pd

from .analysis.anomaly import run_anomaly_detection
from .analysis.clustering import run_clustering
from .analysis.correlation import CorrelationAnalyzer
from .cleaning import basic_clean
from .config import AnalysisConfig
from .exceptions import InsufficientDataError, SmartEdaError
from .ingestion import Source, load_dataset
from .insights import InsightGenerator
from .logger import get_logger
from .models import (
    AnalysisReport,
    DatasetProfile,
    DescriptiveStatsProvider,
)
from .preprocessing import Preprocessor
from .profiling import DataProfiler

logger = get_logger(__name__)


class AnalysisEngine:
    """Punto de entrada del backend de análisis inteligente de datos."""

    def __init__(
        self,
        config: AnalysisConfig | None = None,
        descriptive_provider: DescriptiveStatsProvider | None = None,
    ) -> None:
        """Crea el motor.

        Args:
            config: Configuración del análisis (usa valores por defecto si es None).
            descriptive_provider: Implementación opcional de Rachel para la
                estadística descriptiva. Si es None, el reporte omite ese bloque.
        """
        self.config = config or AnalysisConfig()
        self.descriptive_provider = descriptive_provider
        self.profiler = DataProfiler(self.config)
        self.preprocessor = Preprocessor()
        self.correlation_analyzer = CorrelationAnalyzer(self.config)
        self.insight_generator = InsightGenerator(self.config)

    def analyze(self, source: Source, **read_kwargs: Any) -> AnalysisReport:
        """Ejecuta el análisis completo sobre un archivo y devuelve el reporte.

        Args:
            source: Ruta o archivo (CSV/Excel) a analizar.
            **read_kwargs: Opciones extra para la lectura (sep, sheet_name, etc.).

        Returns:
            Un `AnalysisReport` con perfil, correlaciones, clustering, anomalías
            e insights.

        Raises:
            SmartEdaError: Ante errores de carga o validación del archivo.
        """
        start = time.perf_counter()

        df = load_dataset(source, **read_kwargs)
        if self.config.enable_basic_cleaning:
            df = basic_clean(df)
        profile = self.profiler.profile(df)

        correlations, dependencies = self._analyze_correlations(df, profile)
        clustering = self._analyze_clustering(df, profile)
        anomalies = self._analyze_anomalies(df, profile)
        descriptive = self._compute_descriptive(df, profile)

        insights = self.insight_generator.generate(
            profile, correlations, dependencies, clustering, anomalies
        )

        elapsed = time.perf_counter() - start
        report = AnalysisReport(
            profile=profile,
            correlations=correlations,
            dependencies=dependencies,
            clustering=clustering,
            anomalies=anomalies,
            descriptive=descriptive,
            insights=insights,
            metadata=self._build_metadata(source, df, elapsed),
        )
        logger.info("Análisis completado en %.2f s", elapsed)
        return report

    def analyze_many(
        self, sources: list[Source], **read_kwargs: Any
    ) -> dict[str, AnalysisReport]:
        """Analiza varios archivos y devuelve un reporte por cada uno.

        La propuesta pide aceptar "uno o varios conjuntos de datos". Cada archivo
        se analiza de forma independiente; si uno falla, se registra y se continúa
        con los demás para no perder el resto de resultados.

        Args:
            sources: Lista de rutas o archivos a analizar.
            **read_kwargs: Opciones de lectura aplicadas a todos los archivos.

        Returns:
            Diccionario {nombre_del_archivo: AnalysisReport}.
        """
        reports: dict[str, AnalysisReport] = {}
        for source in sources:
            key = source if isinstance(source, str) else getattr(source, "name", str(source))
            try:
                reports[str(key)] = self.analyze(source, **read_kwargs)
            except SmartEdaError as exc:
                logger.warning("Se omite '%s' por error: %s", key, exc)
        return reports

    # --------------------------- etapas internas ---------------------------

    def _analyze_correlations(self, df: pd.DataFrame, profile: DatasetProfile):
        try:
            correlations = self.correlation_analyzer.correlations(df, profile)
            dependencies = self.correlation_analyzer.dependencies(df, profile)
            return correlations, dependencies
        except SmartEdaError as exc:
            logger.warning("Correlaciones omitidas: %s", exc)
            return {}, []

    def _analyze_clustering(self, df: pd.DataFrame, profile: DatasetProfile):
        if len(profile.numeric_columns) < 2:
            logger.info("Clustering omitido: se requieren >= 2 columnas numéricas.")
            return None
        if profile.n_rows < self.config.min_rows_for_ml:
            logger.info("Clustering omitido: muy pocas filas.")
            return None
        try:
            matrix, features = self.preprocessor.feature_matrix(df, profile)
            return run_clustering(matrix, features, self.config)
        except (SmartEdaError, ValueError) as exc:
            logger.warning("Clustering omitido por error: %s", exc)
            return None

    def _analyze_anomalies(self, df: pd.DataFrame, profile: DatasetProfile):
        if not profile.numeric_columns:
            logger.info("Anomalías omitidas: no hay columnas numéricas.")
            return []
        try:
            numeric_df = self.preprocessor.numeric_frame(df, profile)
            return run_anomaly_detection(numeric_df, self.config)
        except InsufficientDataError as exc:
            logger.warning("Anomalías omitidas: %s", exc)
            return []

    def _compute_descriptive(self, df: pd.DataFrame, profile: DatasetProfile):
        if self.descriptive_provider is None:
            return None
        try:
            return self.descriptive_provider.compute(df, profile)
        except Exception as exc:  # proveedor externo: aislamos cualquier fallo
            logger.warning("Estadística descriptiva omitida: %s", exc)
            return None

    @staticmethod
    def _build_metadata(
        source: Source, df: pd.DataFrame, elapsed: float
    ) -> dict[str, Any]:
        name = source if isinstance(source, (str,)) else getattr(source, "name", "dataset")
        return {
            "source": str(name),
            "n_rows": int(df.shape[0]),
            "n_cols": int(df.shape[1]),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "elapsed_seconds": round(elapsed, 3),
        }
