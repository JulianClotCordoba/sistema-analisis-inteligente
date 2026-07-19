"""smarteda — Backend de análisis inteligente y exploratorio de datos.

Punto único de importación para el resto del equipo::

    from smarteda import AnalysisEngine, AnalysisConfig

    engine = AnalysisEngine()
    report = engine.analyze("data/samples/clientes.csv")
    for insight in report.insights:
        print(insight.message)
"""

from __future__ import annotations

from .config import AnalysisConfig
from .engine import AnalysisEngine
from .exceptions import (
    EmptyDatasetError,
    FileValidationError,
    InsufficientDataError,
    SmartEdaError,
    UnsupportedFileFormatError,
)
from .ingestion import load_dataset
from .cleaning import basic_clean
from .models import (
    AnalysisReport,
    AnomalyResult,
    CategoricalDependency,
    ClusteringResult,
    ColumnProfile,
    CorrelationResult,
    DatasetProfile,
    DescriptiveResult,
    DescriptiveStatsProvider,
    Insight,
    VariableRelationship,
    VariableType,
)
from .profiling import DataProfiler

__version__ = "1.0.0"

__all__ = [
    "AnalysisEngine",
    "AnalysisConfig",
    "AnalysisReport",
    "load_dataset",
    "basic_clean",
    "DataProfiler",
    # modelos / contratos
    "DatasetProfile",
    "ColumnProfile",
    "VariableType",
    "CorrelationResult",
    "VariableRelationship",
    "CategoricalDependency",
    "ClusteringResult",
    "AnomalyResult",
    "DescriptiveResult",
    "DescriptiveStatsProvider",
    "Insight",
    # excepciones
    "SmartEdaError",
    "FileValidationError",
    "UnsupportedFileFormatError",
    "EmptyDatasetError",
    "InsufficientDataError",
]
