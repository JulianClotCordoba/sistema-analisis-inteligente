"""Subpaquete con los análisis: correlaciones, estadística descriptiva,
clustering y anomalías."""

from .anomaly import run_anomaly_detection
from .clustering import run_clustering
from .correlation import CorrelationAnalyzer
from .descriptive import BasicDescriptiveStats

__all__ = [
    "CorrelationAnalyzer",
    "BasicDescriptiveStats",
    "run_clustering",
    "run_anomaly_detection",
]
